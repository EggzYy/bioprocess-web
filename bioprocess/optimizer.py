"""
Constrained optimizer module that properly minimizes excess capacity.
Matches original behavior: find minimum equipment that just meets target.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .models import ScenarioInput
from .capacity import calculate_capacity_deterministic, capacity_meets_target
from .sizing import calculate_capex_estimate_original
from .econ import calculate_economics


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
        scenario.strains,
        equipment,
        fermenter_volume_l,
        working_volume_fraction=scenario.volumes.working_volume_fraction,
    )

    # Check capacity constraint
    meets_capacity = capacity_meets_target(
        capacity_result.total_annual_kg, scenario.target_tpa
    )

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
    # Use original CAPEX parity function for optimization/economics alignment
    licensing_fixed_total = sum(
        s.licensing_fixed_cost_usd
        if hasattr(s, "licensing_fixed_cost_usd")
        else s.get("licensing_fixed_cost_usd", 0)
        if isinstance(s, dict)
        else 0
        for s in scenario.strains
    )
    total_capex, capex_breakdown = calculate_capex_estimate_original(
        scenario.target_tpa,
        reactors,
        ds_lines,
        fermenter_volume_l,
        licensing_fixed_total=licensing_fixed_total,
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
        capex_breakdown.get("equip", capex_breakdown.get("equipment", 0)),
        scenario.assumptions,
        scenario.labor,
        scenario.capex,
        scenario.opex,
        scenario.prices.product_prices,
        working_volume_fraction=scenario.volumes.working_volume_fraction,
        capex_override={
            "land": capex_breakdown.get("land", 0.0),
            "building": capex_breakdown.get("building", 0.0),
            "equipment": capex_breakdown.get(
                "equip", capex_breakdown.get("equipment", 0.0)
            ),
            "install": capex_breakdown.get("install", 0.0),
            "direct": capex_breakdown.get("direct", 0.0),
            "cont": capex_breakdown.get("cont", 0.0),
            "wc": capex_breakdown.get(
                "wc", capex_breakdown.get("working_capital", 0.0)
            ),
            "licensing_fixed_total": capex_breakdown.get("licensing_fixed_total", 0.0),
            "total": capex_breakdown.get("total", 0.0),
        },
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

    # Calculate excess capacity ratio (penalize overproduction)
    target_kg = scenario.target_tpa * 1000
    excess_ratio = (
        (capacity_result.total_annual_kg - target_kg) / target_kg
        if target_kg > 0
        else 0
    )

    return {
        "reactors": reactors,
        "ds_lines": ds_lines,
        "fermenter_volume_l": fermenter_volume_l,
        "meets_capacity": meets_capacity,
        "npv": economics.npv,
        "irr": economics.irr,
        "capex": economics.total_capex,
        "opex_per_kg": opex_per_kg,
        "capacity_kg": capacity_result.total_annual_kg,
        "excess_ratio": excess_ratio,  # Track how much we exceed target
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


def optimize_for_minimal_excess(
    scenario: ScenarioInput,
    max_reactors: int = 20,
    max_ds_lines: int = 10,
    volume_options: Optional[List[float]] = None,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Optimize equipment to meet target TPA with MINIMAL excess capacity.
    This properly matches the original pricing_integrated.py logic.

    Key algorithm:
    1. For each volume (smallest to largest)
    2. For each reactor count (smallest to largest)
    3. For each DS line count (smallest to largest)
    4. If configuration meets target:
       - Record it as a candidate
       - BREAK out of DS loop (higher DS only adds cost)
    5. Select best from candidates (lowest CAPEX among minimal excess)

    Args:
        scenario: Scenario input
        max_reactors: Maximum number of reactors to consider
        max_ds_lines: Maximum number of DS lines to consider
        volume_options: List of fermenter volumes to test

    Returns:
        Tuple of (best_solution, all_results_df)
    """
    target_kg = scenario.target_tpa * 1000

    # Get volume options
    if volume_options is None:
        if scenario.volumes.volume_options_l:
            volume_options = scenario.volumes.volume_options_l
        else:
            volume_options = [scenario.volumes.base_fermenter_vol_l]

    best_solution = None
    best_score = float("inf")  # Combined score of CAPEX and excess
    all_results = []
    feasible_candidates = []

    # Test each volume option (smallest first to minimize excess)
    for volume in sorted(volume_options):
        # For each volume, find minimum equipment that meets target
        for reactors in range(2, max_reactors + 1):
            found_feasible_for_r = False

            for ds_lines in range(1, max_ds_lines + 1):
                # Evaluate this configuration
                result = evaluate_configuration(reactors, ds_lines, volume, scenario)
                all_results.append(result)

                # Check if meets target
                if result["meets_capacity"]:
                    feasible_candidates.append(result)
                    found_feasible_for_r = True
                    # CRITICAL: Break out of DS loop like original
                    # Higher DS lines only increase cost for same reactors
                    break

            # Optional: early termination if we found a very good solution
            # (low excess, reasonable CAPEX)
            if found_feasible_for_r and result["excess_ratio"] < 0.2:
                # Found solution with <20% excess, might be good enough
                pass  # Continue searching for now

    # Convert results to DataFrame
    all_results_df = pd.DataFrame(all_results)

    if feasible_candidates:
        # Among feasible solutions, select based on:
        # 1. Minimize excess capacity (avoid massive overproduction)
        # 2. Among similar excess, minimize CAPEX

        candidates_df = pd.DataFrame(feasible_candidates)

        # Group by excess bins (0-20%, 20-50%, 50-100%, >100%)
        candidates_df["excess_bin"] = pd.cut(
            candidates_df["excess_ratio"],
            bins=[-0.01, 0.2, 0.5, 1.0, float("inf")],
            labels=["minimal", "low", "moderate", "high"],
        )

        # Within the lowest excess bin, find minimum CAPEX
        min_excess_bin = candidates_df["excess_bin"].min()
        best_bin_df = candidates_df[candidates_df["excess_bin"] == min_excess_bin]
        best_idx = best_bin_df["capex"].idxmin()
        best_solution = best_bin_df.loc[best_idx].to_dict()

    else:
        # No feasible solution found, return configuration with highest capacity
        if not all_results_df.empty:
            best_idx = all_results_df["capacity_kg"].idxmax()
            best_solution = all_results_df.loc[best_idx].to_dict()
            best_solution["warning"] = "Target not reachable within search bounds"

    return best_solution, all_results_df


def optimize_with_constrained_pareto(
    scenario: ScenarioInput,
    max_reactors: int = 20,
    max_ds_lines: int = 10,
    volume_options: Optional[List[float]] = None,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Multi-objective optimization with Pareto front, but constrained
    to solutions with minimal excess capacity.

    Args:
        scenario: Scenario input
        max_reactors: Maximum number of reactors
        max_ds_lines: Maximum number of DS lines
        volume_options: List of fermenter volumes

    Returns:
        Tuple of (best_solution, all_results_df)
    """
    # First get minimal excess solutions
    minimal_solution, all_results_df = optimize_for_minimal_excess(
        scenario, max_reactors, max_ds_lines, volume_options
    )

    if minimal_solution is None:
        return minimal_solution, all_results_df

    # Filter to only solutions with reasonable excess (<50% over target)
    feasible_df = all_results_df[
        (all_results_df["meets_capacity"]) & (all_results_df["excess_ratio"] < 0.5)
    ].copy()

    if feasible_df.empty:
        # Fall back to minimal solution
        return minimal_solution, all_results_df

    # Find Pareto front for (min CAPEX, max IRR) within constrained set
    pareto_solutions = []
    for idx, row in feasible_df.iterrows():
        is_dominated = False
        for _, other in feasible_df.iterrows():
            if idx == _:
                continue
            # Check if 'other' dominates 'row'
            if (
                other["capex"] <= row["capex"]
                and other["irr"] >= row["irr"]
                and (other["capex"] < row["capex"] or other["irr"] > row["irr"])
            ):
                is_dominated = True
                break
        if not is_dominated:
            pareto_solutions.append(row.to_dict())

    if not pareto_solutions:
        return minimal_solution, all_results_df

    # Select knee point from Pareto front
    pareto_df = pd.DataFrame(pareto_solutions)

    # Normalize CAPEX (minimize - lower is better)
    capex_norm = (pareto_df["capex"].max() - pareto_df["capex"]) / (
        pareto_df["capex"].max() - pareto_df["capex"].min() + 1e-10
    )

    # Normalize IRR (maximize - higher is better)
    irr_norm = (pareto_df["irr"] - pareto_df["irr"].min()) / (
        pareto_df["irr"].max() - pareto_df["irr"].min() + 1e-10
    )

    # Calculate distance to ideal point (1, 1)
    distances = np.sqrt((1 - capex_norm) ** 2 + (1 - irr_norm) ** 2)
    knee_idx = distances.idxmin()
    best_solution = pareto_df.loc[knee_idx].to_dict()

    return best_solution, all_results_df


def optimize_equipment_configuration(
    scenario: ScenarioInput,
    max_reactors: int = 20,
    max_ds_lines: int = 10,
    volume_options: Optional[List[float]] = None,
) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """
    Main optimization function for equipment configuration.
    Uses constrained optimization to minimize excess capacity.

    Args:
        scenario: Scenario input
        max_reactors: Maximum number of reactors to consider
        max_ds_lines: Maximum number of DS lines to consider
        volume_options: List of fermenter volumes (if None, uses scenario volumes)

    Returns:
        Tuple of (best_solution, pareto_df, all_results_df)
    """
    # For multi-objective optimization, use constrained Pareto
    if scenario.use_multiobjective:
        best_solution, all_results_df = optimize_with_constrained_pareto(
            scenario, max_reactors, max_ds_lines, volume_options
        )
    else:
        # Single objective: minimize excess while meeting target
        best_solution, all_results_df = optimize_for_minimal_excess(
            scenario, max_reactors, max_ds_lines, volume_options
        )

    # Create Pareto DataFrame (single row for best solution)
    if best_solution:
        # Add key info for display
        best_solution["plant_kg_good"] = best_solution.get("capacity_kg", 0)
        pareto_df = pd.DataFrame([best_solution])
    else:
        pareto_df = pd.DataFrame()

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
