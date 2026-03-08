"""
Consolidated optimizer module that combines the best features from all optimizer implementations.

This module provides:
- Basic optimization with minimal excess capacity (from optimizer.py)
- Enhanced multi-objective optimization with capacity enforcement (from optimizer_enhanced.py)
- Progressive constraint solving for complex optimization scenarios

The consolidated optimizer serves as the main entry point, with backward compatibility
via imports from the original modules.
"""

import math
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .models import ScenarioInput
from .capacity import calculate_capacity_deterministic, capacity_meets_target
from .sizing import calculate_capex_estimate_original
from .econ import calculate_economics
from .constants import (
    DEFAULT_MAX_REACTORS,
    DEFAULT_MAX_DS_LINES,
    DEFAULT_MIN_REACTORS,
    DEFAULT_MIN_DS_LINES,
    EXCESS_TOLERANCE_TIERS,
    MAX_ALLOWED_EXCESS,
)

logger = logging.getLogger(__name__)


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
        "excess_ratio": excess_ratio,
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
    max_reactors: int = DEFAULT_MAX_REACTORS,
    max_ds_lines: int = DEFAULT_MAX_DS_LINES,
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
    best_score = float("inf")
    all_results = []
    feasible_candidates = []

    # Test each volume option (smallest first to minimize excess)
    for volume in sorted(volume_options):
        # For each volume, find minimum equipment that meets target
        for reactors in range(DEFAULT_MIN_REACTORS, max_reactors + 1):
            found_feasible_for_r = False

            for ds_lines in range(DEFAULT_MIN_DS_LINES, max_ds_lines + 1):
                # Evaluate this configuration
                result = evaluate_configuration(reactors, ds_lines, volume, scenario)
                all_results.append(result)

                # Check if meets target
                if result["meets_capacity"]:
                    feasible_candidates.append(result)
                    found_feasible_for_r = True
                    # Break out of DS loop like original
                    break

    # Convert results to DataFrame
    all_results_df = pd.DataFrame(all_results)

    if feasible_candidates:
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
    max_reactors: int = DEFAULT_MAX_REACTORS,
    max_ds_lines: int = DEFAULT_MAX_DS_LINES,
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
        return minimal_solution, all_results_df

    # Find Pareto front for (min CAPEX, max IRR) within constrained set
    pareto_solutions = find_pareto_front(feasible_df)

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


def find_pareto_front(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Find Pareto-optimal solutions for (min CAPEX, max IRR).

    Args:
        df: DataFrame with solutions

    Returns:
        List of Pareto-optimal solutions
    """
    pareto_solutions = []

    for idx, row in df.iterrows():
        is_dominated = False
        for _, other in df.iterrows():
            if idx == _:
                continue
            # Check if 'other' dominates 'row'
            # Dominance: lower CAPEX AND higher IRR (with at least one strict inequality)
            if (
                other["capex"] <= row["capex"]
                and other["irr"] >= row["irr"]
                and (other["capex"] < row["capex"] or other["irr"] > row["irr"])
            ):
                is_dominated = True
                break
        if not is_dominated:
            pareto_solutions.append(row.to_dict())

    return pareto_solutions


def select_knee_with_excess_penalty(
    pareto_solutions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Select knee point from Pareto front with penalty for excess capacity.

    This function selects the best solution considering:
    1. Distance to ideal point in (CAPEX, IRR) space
    2. Penalty for excess capacity

    Args:
        pareto_solutions: List of Pareto-optimal solutions

    Returns:
        Best solution dictionary
    """
    if not pareto_solutions:
        return None

    pareto_df = pd.DataFrame(pareto_solutions)

    # Normalize CAPEX (minimize - lower is better)
    capex_range = pareto_df["capex"].max() - pareto_df["capex"].min()
    if capex_range > 0:
        capex_norm = (pareto_df["capex"].max() - pareto_df["capex"]) / capex_range
    else:
        capex_norm = pd.Series([1.0] * len(pareto_df))

    # Normalize IRR (maximize - higher is better)
    irr_range = pareto_df["irr"].max() - pareto_df["irr"].min()
    if irr_range > 0:
        irr_norm = (pareto_df["irr"] - pareto_df["irr"].min()) / irr_range
    else:
        irr_norm = pd.Series([1.0] * len(pareto_df))

    # Normalize excess ratio (minimize - lower is better)
    excess_range = pareto_df["excess_ratio"].max() - pareto_df["excess_ratio"].min()
    if excess_range > 0:
        excess_norm = (
            pareto_df["excess_ratio"].max() - pareto_df["excess_ratio"]
        ) / excess_range
    else:
        excess_norm = pd.Series([1.0] * len(pareto_df))

    # Calculate weighted distance to ideal point
    w_capex = 0.3
    w_irr = 0.3
    w_excess = 0.4

    distances = np.sqrt(
        w_capex * (1 - capex_norm) ** 2
        + w_irr * (1 - irr_norm) ** 2
        + w_excess * (1 - excess_norm) ** 2
    )

    knee_idx = distances.idxmin()
    return pareto_df.loc[knee_idx].to_dict()


def optimize_with_progressive_constraints(
    scenario: ScenarioInput,
    max_reactors: int = DEFAULT_MAX_REACTORS,
    max_ds_lines: int = DEFAULT_MAX_DS_LINES,
    volume_options: Optional[List[float]] = None,
    max_excess_targets: Optional[List[float]] = None,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Multi-objective optimization with progressive excess capacity constraints.

    This function iteratively narrows the allowed excess capacity window
    to find the best tradeoff between CAPEX, IRR, and capacity matching.

    Args:
        scenario: Scenario input
        max_reactors: Maximum number of reactors
        max_ds_lines: Maximum number of DS lines
        volume_options: List of fermenter volumes
        max_excess_targets: List of maximum excess ratios to try

    Returns:
        Tuple of (best_solution, all_results_df)
    """
    if max_excess_targets is None:
        max_excess_targets = EXCESS_TOLERANCE_TIERS + [MAX_ALLOWED_EXCESS]

    # Get all solutions with minimal excess
    minimal_solution, all_results_df = optimize_for_minimal_excess(
        scenario, max_reactors, max_ds_lines, volume_options
    )

    if minimal_solution is None:
        return minimal_solution, all_results_df

    # Only consider solutions that meet capacity
    feasible_df = all_results_df[all_results_df["meets_capacity"]].copy()

    if feasible_df.empty:
        return minimal_solution, all_results_df

    best_solution = None
    best_pareto_set = []

    # Try progressively tighter excess constraints
    for max_excess in max_excess_targets:
        # Filter to solutions within this excess limit
        constrained_df = feasible_df[feasible_df["excess_ratio"] <= max_excess].copy()

        if constrained_df.empty:
            break

        # Find Pareto front within this constrained set
        pareto_solutions = find_pareto_front(constrained_df)

        if pareto_solutions:
            # Select knee point considering excess ratio
            best_in_set = select_knee_with_excess_penalty(pareto_solutions)

            # Update best if this is better
            if best_solution is None:
                best_solution = best_in_set
                best_pareto_set = pareto_solutions
            else:
                # Check if new solution is significantly better
                if (
                    best_in_set["excess_ratio"] < best_solution["excess_ratio"] * 0.8
                    and best_in_set["irr"] >= best_solution["irr"] * 0.9
                ):
                    best_solution = best_in_set
                    best_pareto_set = pareto_solutions

    # If no solution found through progressive constraints, use minimal excess
    if best_solution is None:
        best_solution = minimal_solution

    return best_solution, all_results_df


def optimize_with_capacity_enforcement(
    scenario: ScenarioInput,
    max_reactors: int = DEFAULT_MAX_REACTORS,
    max_ds_lines: int = DEFAULT_MAX_DS_LINES,
    volume_options: Optional[List[float]] = None,
    enforce_capacity: bool = True,
    max_allowed_excess: float = MAX_ALLOWED_EXCESS,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Optimization with strict capacity enforcement similar to original pricing_integrated.py.

    This function mimics the behavior of the original optimize_counts_multiobjective:
    1. FULL grid search over ALL configurations (no early breaking)
    2. Filter to only those meeting capacity if enforce_capacity=True
    3. Create Pareto front from feasible set only
    4. Select knee point

    Args:
        scenario: Scenario input
        max_reactors: Maximum number of reactors (default 60 to match original)
        max_ds_lines: Maximum number of DS lines (default 12 to match original)
        volume_options: List of fermenter volumes
        enforce_capacity: Whether to enforce capacity constraint
        max_allowed_excess: Maximum allowed excess ratio when enforce_capacity=True

    Returns:
        Tuple of (best_solution, all_results_df)
    """
    start_time = time.time()

    target_kg = scenario.target_tpa * 1000.0

    # If no volume options provided, use scenario volumes
    if volume_options is None:
        if hasattr(scenario, 'volumes') and scenario.volumes.volume_options_l:
            volume_options = scenario.volumes.volume_options_l
        else:
            volume_options = [scenario.volumes.base_fermenter_vol_l]

    all_results = []
    total_evaluations = len(volume_options) * (max_reactors - DEFAULT_MIN_REACTORS + 1) * max_ds_lines
    evaluation_count = 0

    logger.info(
        f"Starting FULL grid search optimization: {len(volume_options)} volumes × "
        f"{max_reactors - DEFAULT_MIN_REACTORS + 1} reactors × {max_ds_lines} DS lines = "
        f"{total_evaluations} evaluations"
    )

    # FULL grid search over ALL configurations - NO EARLY BREAKING
    for volume in volume_options:
        for reactors in range(DEFAULT_MIN_REACTORS, max_reactors + 1):
            for ds_lines in range(DEFAULT_MIN_DS_LINES, max_ds_lines + 1):
                evaluation_count += 1
                if evaluation_count % 100 == 0:
                    logger.info(
                        f"Progress: {evaluation_count}/{total_evaluations} "
                        f"evaluations ({evaluation_count/total_evaluations*100:.1f}%)"
                    )
                # Evaluate this configuration
                result = evaluate_configuration(reactors, ds_lines, volume, scenario)
                all_results.append(result)

    # Convert to DataFrame
    all_results_df = pd.DataFrame(all_results)

    end_time = time.time()
    runtime = end_time - start_time
    logger.info(
        f"Completed {total_evaluations} evaluations in {runtime:.2f}s "
        f"({total_evaluations/runtime:.1f} evals/sec)"
    )

    if all_results_df.empty:
        return None, all_results_df

    # Filter feasibility if requested
    if enforce_capacity:
        # Filter to solutions that meet capacity
        meets_capacity_df = all_results_df[all_results_df["meets_capacity"]].copy()

        if meets_capacity_df.empty:
            # No solutions meet capacity at all
            fallback_idx = all_results_df["capacity_kg"].idxmax()
            best_solution = all_results_df.loc[fallback_idx].to_dict()
            best_solution["warning"] = "Target not reachable within search bounds"
            return best_solution, all_results_df

        # Progressive excess tolerance: EXACT tiers 5%, then 15%, then 25%
        # Note: Use tiers from constants
        tiers = EXCESS_TOLERANCE_TIERS
        feasible_df = None
        for tol in tiers:
            constrained = meets_capacity_df[meets_capacity_df["excess_ratio"] <= tol]
            if not constrained.empty:
                feasible_df = constrained
                break

        if feasible_df is None:
            # Fall back to solution with minimum excess that still meets capacity
            best_idx = meets_capacity_df["excess_ratio"].idxmin()
            best_solution = meets_capacity_df.loc[best_idx].to_dict()
            best_solution["warning"] = (
                f"Could not meet progressive excess limits up to 25%. "
                f"Minimum achievable: {best_solution['excess_ratio']:.1%}"
            )
            return best_solution, all_results_df

    if feasible_df.empty:
        # This shouldn't happen given the logic above, but keep as safety
        fallback_idx = all_results_df["capacity_kg"].idxmax()
        best_solution = all_results_df.loc[fallback_idx].to_dict()
        best_solution["warning"] = "No feasible solution found"
        return best_solution, all_results_df

    # Build Pareto front (min CAPEX, max IRR) from feasible set using boolean mask
    def _pareto_mask(df: pd.DataFrame) -> pd.Series:
        n = len(df)
        dominated = np.zeros(n, dtype=bool)
        vals = df[["capex", "irr"]].to_numpy()
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                # j dominates i if capex<= and irr>= with at least one strict
                if (
                    vals[j, 0] <= vals[i, 0]
                    and vals[j, 1] >= vals[i, 1]
                    and (vals[j, 0] < vals[i, 0] or vals[j, 1] > vals[i, 1])
                ):
                    dominated[i] = True
                    break
        # Return boolean Series aligned to df index
        return pd.Series(~dominated, index=df.index)

    mask = _pareto_mask(feasible_df)
    pareto_df = (
        feasible_df[mask]
        .sort_values(["capex", "irr"], ascending=[True, False])
        .reset_index(drop=True)
    )

    # Choose knee point (closest to utopia: min CAPEX, max IRR), matching original
    def _choose_knee_point(df: pd.DataFrame) -> Optional[int]:
        if df.empty:
            return None
        cap_min, cap_max = df["capex"].min(), df["capex"].max()
        irr_min, irr_max = df["irr"].min(), df["irr"].max()

        def norm_cap(x: float) -> float:
            return 0.0 if cap_max == cap_min else (x - cap_min) / (cap_max - cap_min)

        def norm_irr(x: float) -> float:
            return 0.0 if irr_max == irr_min else (irr_max - x) / (irr_max - irr_min)

        d = (df["capex"].apply(norm_cap) ** 2 + df["irr"].apply(norm_irr) ** 2) ** 0.5
        return int(d.idxmin()) if not d.empty else None

    idx = _choose_knee_point(pareto_df)
    if idx is None:
        # Fallback: lowest CAPEX, highest IRR among feasible
        chosen = feasible_df.sort_values(
            ["capex", "irr"], ascending=[True, False]
        ).iloc[0]
    else:
        chosen = pareto_df.iloc[idx]

    best_solution = chosen.to_dict()
    # Ensure key fields are present
    best_solution["plant_kg_good"] = best_solution.get("capacity_kg", 0)

    return best_solution, all_results_df


def optimize_equipment_configuration(
    scenario: ScenarioInput,
    max_reactors: int = DEFAULT_MAX_REACTORS,
    max_ds_lines: int = DEFAULT_MAX_DS_LINES,
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


# Backward compatibility: Import original functions for existing code
# These re-export from this consolidated module
__all__ = [
    "evaluate_configuration",
    "optimize_for_minimal_excess",
    "optimize_with_constrained_pareto",
    "optimize_with_progressive_constraints",
    "optimize_with_capacity_enforcement",
    "optimize_equipment_configuration",
    "find_pareto_front",
    "select_knee_with_excess_penalty",
    "sensitivity_analysis",
]
