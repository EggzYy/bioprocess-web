"""
Optimization module.
Provides single and multi-objective optimization for facility design.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import itertools

from .models import (
    OptimizationResult,
    ScenarioInput,
)
from .capacity import calculate_capacity_deterministic, capacity_meets_target
from .sizing import calculate_capex_estimate
from .econ import calculate_economics


@dataclass
class DesignVariable:
    """Design variable for optimization."""

    name: str
    min_value: float
    max_value: float
    is_integer: bool = False


@dataclass
class OptimizationProblem:
    """Optimization problem definition."""

    variables: List[DesignVariable]
    objectives: List[str]
    constraints: Dict[str, Any]
    scenario: ScenarioInput


def evaluate_configuration(
    reactors: int,
    ds_lines: int,
    fermenter_volume_l: float,
    scenario: ScenarioInput,
    use_monte_carlo: bool = False,
    n_samples: int = 100,
) -> Dict[str, Any]:
    """
    Evaluate a specific equipment configuration.

    Args:
        reactors: Number of reactors
        ds_lines: Number of downstream lines
        fermenter_volume_l: Fermenter volume
        scenario: Scenario input
        use_monte_carlo: Whether to use Monte Carlo
        n_samples: Number of Monte Carlo samples

    Returns:
        Dictionary with evaluation metrics
    """
    # Update equipment configuration
    equipment = scenario.equipment
    equipment.reactors_total = reactors
    equipment.ds_lines_total = ds_lines

    # Calculate capacity
    _, totals, capacity_result = calculate_capacity_deterministic(
        scenario.strains, equipment, fermenter_volume_l
    )

    # Check capacity constraint
    meets_capacity = capacity_meets_target(
        capacity_result.total_annual_kg, scenario.target_tpa
    )

    if not meets_capacity:
        # Penalize infeasible solutions
        return {
            "reactors": reactors,
            "ds_lines": ds_lines,
            "fermenter_volume_l": fermenter_volume_l,
            "feasible": False,
            "npv": -1e9,
            "irr": -1.0,
            "capex": 1e9,
            "capacity_kg": capacity_result.total_annual_kg,
            "utilization": 0.0,
        }

    # Get strain data for equipment sizing
    from .presets import get_strain_info

    strain_data = []
    for strain in scenario.strains:
        if isinstance(strain, str):
            strain_info = get_strain_info(strain)
            strain_info["name"] = strain
            strain_data.append(strain_info)
        elif hasattr(strain, "name"):
            try:
                strain_info = get_strain_info(strain.name)
                strain_info["name"] = strain.name
                # Merge any custom properties
                if hasattr(strain, "respiration_type"):
                    strain_info["respiration_type"] = strain.respiration_type
                if hasattr(strain, "requires_tff"):
                    strain_info["requires_tff"] = strain.requires_tff
                if hasattr(strain, "downstream_complexity"):
                    strain_info["downstream_complexity"] = strain.downstream_complexity
                strain_data.append(strain_info)
            except ValueError:
                strain_data.append(
                    {
                        "name": strain.name,
                        "respiration_type": getattr(
                            strain, "respiration_type", "aerobic"
                        ),
                        "requires_tff": getattr(strain, "requires_tff", False),
                        "downstream_complexity": getattr(
                            strain, "downstream_complexity", 1.0
                        ),
                    }
                )
        else:
            strain_data.append(strain)

    # Calculate CAPEX
    total_capex, capex_breakdown = calculate_capex_estimate(
        scenario.target_tpa,
        reactors,
        ds_lines,
        fermenter_volume_l,
        strains=strain_data,  # Pass strain data instead of anaerobic flag
        volume_plan=scenario.volumes,
        capex_config=scenario.capex,
        licensing_fixed_total=sum(
            s.licensing_fixed_cost_usd
            if hasattr(s, "licensing_fixed_cost_usd")
            else s.get("licensing_fixed_cost_usd", 0)
            if isinstance(s, dict)
            else 0
            for s in scenario.strains
        ),
    )

    # Calculate economics
    batches_per_strain = {
        strain["name"]: strain["good_batches"] for strain in capacity_result.per_strain
    }

    economics = calculate_economics(
        scenario.target_tpa,
        capacity_result.total_annual_kg,
        capacity_result.total_good_batches,
        batches_per_strain,
        scenario.strains,
        fermenter_volume_l,
        capex_breakdown["equipment"],
        scenario.assumptions,
        scenario.labor,
        scenario.capex,
        scenario.opex,
        scenario.prices.product_prices,
    )

    # Calculate additional metrics
    opex_per_kg = (
        economics.total_opex / capacity_result.total_annual_kg
        if capacity_result.total_annual_kg > 0
        else 1e6
    )
    avg_utilization = (
        capacity_result.weighted_up_utilization
        + capacity_result.weighted_ds_utilization
    ) / 2

    return {
        "reactors": reactors,
        "ds_lines": ds_lines,
        "fermenter_volume_l": fermenter_volume_l,
        "feasible": True,
        "npv": economics.npv,
        "irr": economics.irr,
        "capex": economics.total_capex,
        "opex_per_kg": opex_per_kg,
        "capacity_kg": capacity_result.total_annual_kg,
        "utilization": avg_utilization,
        "payback_years": economics.payback_years,
        "ebitda_margin": economics.ebitda_margin,
        "up_utilization": capacity_result.weighted_up_utilization,
        "ds_utilization": capacity_result.weighted_ds_utilization,
        "bottleneck": capacity_result.bottleneck,
        "economics": economics,
        "capacity": capacity_result,
        "capex_breakdown": capex_breakdown,
    }


def grid_search_optimization(
    scenario: ScenarioInput,
    reactor_range: Tuple[int, int],
    ds_line_range: Tuple[int, int],
    volume_options: List[float],
    objective: str = "npv",
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Perform grid search optimization.

    Args:
        scenario: Scenario input
        reactor_range: (min, max) reactors
        ds_line_range: (min, max) DS lines
        volume_options: List of fermenter volumes
        objective: Optimization objective

    Returns:
        Tuple of (best_solution, all_results_df)
    """
    results = []

    # Generate grid
    reactor_values = range(reactor_range[0], reactor_range[1] + 1)
    ds_line_values = range(ds_line_range[0], ds_line_range[1] + 1)

    # Evaluate all combinations
    for reactors, ds_lines, volume in itertools.product(
        reactor_values, ds_line_values, volume_options
    ):
        result = evaluate_configuration(reactors, ds_lines, volume, scenario)
        results.append(result)

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Filter feasible solutions
    feasible_df = df[df["feasible"]].copy()

    if feasible_df.empty:
        # No feasible solution found
        return None, df

    # Find best solution
    if objective in ["npv", "irr", "utilization", "ebitda_margin"]:
        # Maximize
        best_idx = feasible_df[objective].idxmax()
    elif objective in ["capex", "opex_per_kg", "payback_years"]:
        # Minimize
        best_idx = feasible_df[objective].idxmin()
    else:
        # Default to NPV
        best_idx = feasible_df["npv"].idxmax()

    best_solution = feasible_df.loc[best_idx].to_dict()

    return best_solution, df


def pareto_dominates(sol1: Dict, sol2: Dict, objectives: List[Tuple[str, str]]) -> bool:
    """
    Check if sol1 dominates sol2 in Pareto sense.

    Args:
        sol1: Solution 1
        sol2: Solution 2
        objectives: List of (objective_name, direction) where direction is 'min' or 'max'

    Returns:
        True if sol1 dominates sol2
    """
    at_least_one_better = False

    for obj_name, direction in objectives:
        val1 = sol1.get(obj_name, 0)
        val2 = sol2.get(obj_name, 0)

        if direction == "max":
            if val1 < val2:
                return False
            if val1 > val2:
                at_least_one_better = True
        else:  # min
            if val1 > val2:
                return False
            if val1 < val2:
                at_least_one_better = True

    return at_least_one_better


def find_pareto_front(
    solutions: List[Dict], objectives: List[Tuple[str, str]]
) -> List[Dict]:
    """
    Find Pareto front from a list of solutions.

    Args:
        solutions: List of solution dictionaries
        objectives: List of (objective_name, direction) tuples

    Returns:
        List of non-dominated solutions
    """
    pareto_front = []

    for sol in solutions:
        is_dominated = False

        for other in solutions:
            if sol is other:
                continue

            if pareto_dominates(other, sol, objectives):
                is_dominated = True
                break

        if not is_dominated:
            pareto_front.append(sol)

    return pareto_front


def multi_objective_optimization(
    scenario: ScenarioInput,
    reactor_range: Tuple[int, int],
    ds_line_range: Tuple[int, int],
    volume_options: List[float],
    objectives: List[Tuple[str, str]] = [("npv", "max"), ("capex", "min")],
) -> OptimizationResult:
    """
    Perform multi-objective optimization.

    Args:
        scenario: Scenario input
        reactor_range: (min, max) reactors
        ds_line_range: (min, max) DS lines
        volume_options: List of fermenter volumes
        objectives: List of (objective_name, direction) tuples

    Returns:
        OptimizationResult with Pareto front
    """
    # First do grid search
    _, all_results_df = grid_search_optimization(
        scenario, reactor_range, ds_line_range, volume_options, "npv"
    )

    # Filter feasible solutions
    feasible_df = all_results_df[all_results_df["feasible"]].copy()

    if feasible_df.empty:
        # No feasible solutions
        return OptimizationResult(
            best_solution={},
            pareto_front=[],
            n_evaluations=len(all_results_df),
            selected_fermenter_volume=volume_options[0],
            selected_reactors=reactor_range[0],
            selected_ds_lines=ds_line_range[0],
        )

    # Find Pareto front
    feasible_solutions = feasible_df.to_dict("records")
    pareto_front = find_pareto_front(feasible_solutions, objectives)

    # Select knee point from Pareto front
    if pareto_front:
        # Normalize objectives for knee point selection
        obj_names = [obj[0] for obj in objectives]
        obj_dirs = [obj[1] for obj in objectives]

        # Create normalized matrix
        pareto_df = pd.DataFrame(pareto_front)

        # Normalize each objective
        normalized_values = []
        for obj_name, direction in objectives:
            values = pareto_df[obj_name].values
            if direction == "max":
                # For maximization, higher is better
                norm = (values - values.min()) / (values.max() - values.min() + 1e-10)
            else:
                # For minimization, lower is better
                norm = (values.max() - values) / (values.max() - values.min() + 1e-10)
            normalized_values.append(norm)

        # Calculate distance to ideal point (1, 1, ...)
        distances = np.sqrt(sum((1 - nv) ** 2 for nv in normalized_values))
        knee_idx = np.argmin(distances)
        best_solution = pareto_front[knee_idx]
    else:
        # Fallback to best NPV
        best_idx = feasible_df["npv"].idxmax()
        best_solution = feasible_df.loc[best_idx].to_dict()

    return OptimizationResult(
        best_solution=best_solution,
        pareto_front=pareto_front,
        n_evaluations=len(all_results_df),
        convergence_history=None,
        selected_fermenter_volume=best_solution.get(
            "fermenter_volume_l", volume_options[0]
        ),
        selected_reactors=best_solution.get("reactors", reactor_range[0]),
        selected_ds_lines=best_solution.get("ds_lines", ds_line_range[0]),
    )


def optimize_equipment_configuration(
    scenario: ScenarioInput,
    max_reactors: int = 20,
    max_ds_lines: int = 10,
    volume_options: Optional[List[float]] = None,
) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """
    Main optimization function for equipment configuration.

    Args:
        scenario: Scenario input
        max_reactors: Maximum number of reactors to consider
        max_ds_lines: Maximum number of DS lines to consider
        volume_options: List of fermenter volumes (if None, uses scenario volumes)

    Returns:
        Tuple of (best_solution, pareto_df, all_results_df)
    """
    # Get volume options
    if volume_options is None:
        if scenario.volumes.volume_options_l:
            volume_options = scenario.volumes.volume_options_l
        else:
            volume_options = [scenario.volumes.base_fermenter_vol_l]

    # Define ranges
    min_reactors = 2  # Minimum for redundancy
    min_ds_lines = 1

    reactor_range = (min_reactors, min(max_reactors, 60))
    ds_line_range = (min_ds_lines, min(max_ds_lines, 20))

    # Perform optimization based on configuration
    if scenario.use_multiobjective:
        # Multi-objective optimization
        result = multi_objective_optimization(
            scenario,
            reactor_range,
            ds_line_range,
            volume_options,
            objectives=[("irr", "max"), ("capex", "min")],
        )

        best_solution = result.best_solution
        pareto_df = (
            pd.DataFrame(result.pareto_front) if result.pareto_front else pd.DataFrame()
        )

        # Get all results for analysis
        _, all_results_df = grid_search_optimization(
            scenario, reactor_range, ds_line_range, volume_options, "npv"
        )
    else:
        # Single objective optimization
        objective = "irr" if scenario.optimization.objectives else "npv"
        if scenario.optimization.objectives:
            objective = scenario.optimization.objectives[0].value

        best_solution, all_results_df = grid_search_optimization(
            scenario, reactor_range, ds_line_range, volume_options, objective
        )

        # No Pareto front for single objective
        pareto_df = pd.DataFrame([best_solution]) if best_solution else pd.DataFrame()

    return best_solution, pareto_df, all_results_df


def sensitivity_analysis(
    scenario: ScenarioInput,
    base_configuration: Dict[str, Any],
    parameters: List[str],
    delta_pct: float = 0.1,
) -> pd.DataFrame:
    """
    Perform sensitivity analysis on key parameters.

    Args:
        scenario: Scenario input
        base_configuration: Base equipment configuration
        parameters: List of parameters to vary
        delta_pct: Percentage change for each parameter

    Returns:
        DataFrame with sensitivity results
    """
    results = []

    # Get base metrics
    base_result = evaluate_configuration(
        base_configuration["reactors"],
        base_configuration["ds_lines"],
        base_configuration["fermenter_volume_l"],
        scenario,
    )

    base_npv = base_result["npv"]
    base_irr = base_result["irr"]

    # Vary each parameter
    for param in parameters:
        # Create modified scenarios
        for direction, factor in [("down", 1 - delta_pct), ("up", 1 + delta_pct)]:
            # Clone scenario
            modified_scenario = scenario.model_copy(deep=True)

            # Modify parameter
            if param == "discount_rate":
                modified_scenario.assumptions.discount_rate *= factor
            elif param == "tax_rate":
                modified_scenario.assumptions.tax_rate *= factor
            elif param == "electricity_cost":
                modified_scenario.opex.electricity_usd_per_kwh *= factor
            elif param == "product_price":
                for key in modified_scenario.prices.product_prices:
                    modified_scenario.prices.product_prices[key] *= factor
            elif param == "raw_material_cost":
                for key in modified_scenario.prices.raw_prices:
                    modified_scenario.prices.raw_prices[key] *= factor
            # Add more parameters as needed

            # Evaluate modified scenario
            result = evaluate_configuration(
                base_configuration["reactors"],
                base_configuration["ds_lines"],
                base_configuration["fermenter_volume_l"],
                modified_scenario,
            )

            # Calculate changes
            npv_change = (
                (result["npv"] - base_npv) / abs(base_npv) if base_npv != 0 else 0
            )
            irr_change = result["irr"] - base_irr

            results.append(
                {
                    "parameter": param,
                    "direction": direction,
                    "factor": factor,
                    "npv": result["npv"],
                    "irr": result["irr"],
                    "npv_change_pct": npv_change * 100,
                    "irr_change_pts": irr_change * 100,
                }
            )

    return pd.DataFrame(results)
