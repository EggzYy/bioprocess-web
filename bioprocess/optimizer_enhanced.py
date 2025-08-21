"""
Enhanced optimizer with improved capacity constraint enforcement.
This module provides better handling of excess capacity during multi-objective optimization.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, Tuple, List, Optional
from .models import ScenarioInput
from .optimizer import evaluate_configuration, optimize_for_minimal_excess

logger = logging.getLogger(__name__)


def optimize_with_progressive_constraints(
    scenario: ScenarioInput,
    max_reactors: int = 20,
    max_ds_lines: int = 10,
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
        max_excess_targets: List of maximum excess ratios to try (default: [2.0, 1.0, 0.5, 0.3, 0.2, 0.1])

    Returns:
        Tuple of (best_solution, all_results_df)
    """
    if max_excess_targets is None:
        # Start with generous allowance and progressively tighten
        max_excess_targets = [2.0, 1.0, 0.5, 0.3, 0.2, 0.1]

    # Get all solutions with minimal excess
    minimal_solution, all_results_df = optimize_for_minimal_excess(
        scenario, max_reactors, max_ds_lines, volume_options
    )

    if minimal_solution is None:
        return minimal_solution, all_results_df

    # Only consider solutions that meet capacity
    feasible_df = all_results_df[all_results_df["meets_capacity"]].copy()

    if feasible_df.empty:
        # No feasible solutions, return best capacity even if below target
        return minimal_solution, all_results_df

    best_solution = None
    best_pareto_set = []

    # Try progressively tighter excess constraints
    for max_excess in max_excess_targets:
        # Filter to solutions within this excess limit
        constrained_df = feasible_df[feasible_df["excess_ratio"] <= max_excess].copy()

        if constrained_df.empty:
            # Can't meet this constraint, use previous best
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
                # Prefer tighter excess constraint if IRR/CAPEX tradeoff is reasonable
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
    # Ideal point: (CAPEX_norm=1, IRR_norm=1, excess_norm=1)
    # Weights: prioritize excess minimization, then balance CAPEX and IRR
    w_capex = 0.3
    w_irr = 0.3
    w_excess = 0.4  # Higher weight for minimizing excess

    distances = np.sqrt(
        w_capex * (1 - capex_norm) ** 2
        + w_irr * (1 - irr_norm) ** 2
        + w_excess * (1 - excess_norm) ** 2
    )

    knee_idx = distances.idxmin()
    return pareto_df.loc[knee_idx].to_dict()


def optimize_with_capacity_enforcement(
    scenario: ScenarioInput,
    max_reactors: int = 60,
    max_ds_lines: int = 12,
    volume_options: Optional[List[float]] = None,
    enforce_capacity: bool = True,
    max_allowed_excess: float = 0.2,
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
    import time
    start_time = time.time()

    target_kg = scenario.target_tpa * 1000.0

    # If no volume options provided, use scenario volumes
    if volume_options is None:
        if hasattr(scenario, 'volumes') and scenario.volumes.volume_options_l:
            volume_options = scenario.volumes.volume_options_l
        else:
            volume_options = [scenario.volumes.base_fermenter_vol_l]

    all_results = []
    total_evaluations = len(volume_options) * (max_reactors - 1) * max_ds_lines
    evaluation_count = 0

    logger.info(f"Starting FULL grid search optimization: {len(volume_options)} volumes × {max_reactors-1} reactors × {max_ds_lines} DS lines = {total_evaluations} evaluations")

    # FULL grid search over ALL configurations - NO EARLY BREAKING
    for volume in volume_options:
        for reactors in range(2, max_reactors + 1):
            for ds_lines in range(1, max_ds_lines + 1):
                evaluation_count += 1
                if evaluation_count % 100 == 0:
                    logger.info(f"Progress: {evaluation_count}/{total_evaluations} evaluations ({evaluation_count/total_evaluations*100:.1f}%)")
                # Evaluate this configuration
                result = evaluate_configuration(reactors, ds_lines, volume, scenario)
                all_results.append(result)

    # Convert to DataFrame
    all_results_df = pd.DataFrame(all_results)

    end_time = time.time()
    runtime = end_time - start_time
    logger.info(f"Completed {total_evaluations} evaluations in {runtime:.2f}s ({total_evaluations/runtime:.1f} evals/sec)")

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
        # Note: Ignore external max_allowed_excess for parity with original requirement
        tiers = [0.05, 0.15, 0.25]
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
