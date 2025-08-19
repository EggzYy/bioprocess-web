"""
Capacity calculation module.
Wraps fermentation_capacity_calculator functions with additional features.
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

# Import the original calculator
from .fermentation_capacity_calculator import (
    StrainSpec,
    EquipmentConfig as OriginalEquipmentConfig,
    calculate_deterministic_capacity,
    monte_carlo_capacity,
)

from .models import StrainInput, EquipmentConfig, CapacityResult
from .presets import STRAIN_BATCH_DB


def strain_input_to_spec(
    strain: StrainInput,
    fermenter_volume_l: float = 2000,
    working_volume_fraction: float = 0.8,
) -> StrainSpec:
    """Convert StrainInput model to StrainSpec for calculator.
    working_volume_fraction allows selecting 0.8 (standard) or 1.0 (legacy)
    """
    working_volume_l = fermenter_volume_l * working_volume_fraction

    return StrainSpec(
        name=strain.name,
        fermentation_time_h=strain.fermentation_time_h,
        turnaround_time_h=strain.turnaround_time_h,
        downstream_time_h=strain.downstream_time_h,
        batch_mass_kg=strain.yield_g_per_L * working_volume_l / 1000.0,
        cv_ferm=strain.cv_ferm,
        cv_turn=strain.cv_turn,
        cv_down=strain.cv_down,
        utility_rate_ferm_kw=strain.utility_rate_ferm_kw,
        utility_rate_cent_kw=strain.utility_rate_cent_kw,
        utility_rate_lyo_kw=strain.utility_rate_lyo_kw,
        utility_cost_steam=strain.utility_cost_steam,
    )


def equipment_config_to_original(config: EquipmentConfig) -> OriginalEquipmentConfig:
    """Convert EquipmentConfig model to original calculator format."""
    return OriginalEquipmentConfig(
        year_hours=config.year_hours,
        reactors_total=config.reactors_total,
        reactors_per_strain=config.reactors_per_strain,
        ds_lines_total=config.ds_lines_total,
        ds_lines_per_strain=config.ds_lines_per_strain,
        upstream_availability=config.upstream_availability,
        downstream_availability=config.downstream_availability,
        quality_yield=config.quality_yield,
    )


def calculate_capacity_deterministic(
    strains: List[StrainInput],
    equipment: EquipmentConfig,
    fermenter_volume_l: float = 2000,
    working_volume_fraction: float = 0.8,
) -> Tuple[pd.DataFrame, Dict[str, Any], CapacityResult]:
    """
    Calculate deterministic capacity for multiple strains.

    Args:
        strains: List of strain inputs
        equipment: Equipment configuration
        fermenter_volume_l: Fermenter volume in liters
        working_volume_fraction: Working volume fraction

    Returns:
        Tuple of (strain_df, totals_dict, capacity_result)
    """
    # Convert to calculator format
    strain_specs = [
        strain_input_to_spec(s, fermenter_volume_l, working_volume_fraction)
        for s in strains
    ]
    equip_config = equipment_config_to_original(equipment)

    # Run calculator
    df, totals = calculate_deterministic_capacity(
        strain_specs,
        equip_config,
        reactor_allocation_policy=equipment.reactor_allocation_policy.value,
        ds_allocation_policy=equipment.ds_allocation_policy.value,
        shared_downstream=equipment.shared_downstream,
    )

    # Determine bottleneck
    if totals["weighted_up_utilization"] > totals["weighted_ds_utilization"] + 0.05:
        bottleneck = "upstream"
    elif totals["weighted_ds_utilization"] > totals["weighted_up_utilization"] + 0.05:
        bottleneck = "downstream"
    else:
        bottleneck = "balanced"

    # Create result model
    result = CapacityResult(
        per_strain=df.to_dict("records"),
        total_feasible_batches=totals["total_feasible_batches"],
        total_good_batches=totals["total_good_batches"],
        total_annual_kg=totals.get("total_annual_kg_good", 0),
        weighted_up_utilization=totals["weighted_up_utilization"],
        weighted_ds_utilization=totals["weighted_ds_utilization"],
        bottleneck=bottleneck,
    )

    return df, totals, result


def calculate_capacity_monte_carlo(
    strains: List[StrainInput],
    equipment: EquipmentConfig,
    fermenter_volume_l: float = 2000,
    n_samples: int = 1000,
    seed: Optional[int] = None,
    confidence_level: float = 0.95,
    working_volume_fraction: float = 0.8,
) -> Tuple[pd.DataFrame, Dict[str, Any], CapacityResult]:
    """
    Calculate capacity using Monte Carlo simulation.

    Args:
        strains: List of strain inputs
        equipment: Equipment configuration
        fermenter_volume_l: Fermenter volume in liters
        n_samples: Number of Monte Carlo samples
        seed: Random seed for reproducibility
        confidence_level: Confidence level for percentile calculations
        working_volume_fraction: Working volume fraction

    Returns:
        Tuple of (summary_df, statistics_dict, capacity_result)
    """
    # Convert to calculator format
    strain_specs = [
        strain_input_to_spec(s, fermenter_volume_l, working_volume_fraction)
        for s in strains
    ]
    equip_config = equipment_config_to_original(equipment)

    # Run Monte Carlo - returns summary DataFrame
    summary_df = monte_carlo_capacity(
        strain_specs,
        equip_config,
        n_sims=n_samples,
        reactor_allocation_policy=equipment.reactor_allocation_policy.value,
        ds_allocation_policy=equipment.ds_allocation_policy.value,
        seed=seed,
    )

    # Extract statistics from summary
    # The summary has rows: mean, std, min, max, median, p05, p95
    # And columns: feasible_batches, good_batches, annual_kg_good

    # Get values from summary
    if "annual_kg_good" in summary_df.columns:
        kg_mean = summary_df.loc["mean", "annual_kg_good"]
        kg_std = summary_df.loc["std", "annual_kg_good"]
        kg_min = summary_df.loc["min", "annual_kg_good"]
        kg_max = summary_df.loc["max", "annual_kg_good"]
        kg_p50 = summary_df.loc["median", "annual_kg_good"]
        kg_p05 = summary_df.loc["p05", "annual_kg_good"]
        kg_p95 = summary_df.loc["p95", "annual_kg_good"]

        # Estimate P10 and P90 from available percentiles
        kg_p10 = kg_p05 + (kg_p50 - kg_p05) * 0.2  # Interpolate
        kg_p90 = kg_p50 + (kg_p95 - kg_p50) * 0.8  # Interpolate
    else:
        kg_mean = kg_std = kg_p10 = kg_p50 = kg_p90 = 0.0

    total_feasible = summary_df.loc["mean", "feasible_batches"]
    total_good = summary_df.loc["mean", "good_batches"]

    # Run deterministic to get utilization info
    _, totals_det, _ = calculate_capacity_deterministic(
        strains, equipment, fermenter_volume_l, working_volume_fraction
    )

    avg_up_util = totals_det["weighted_up_utilization"]
    avg_ds_util = totals_det["weighted_ds_utilization"]

    # Determine bottleneck
    if avg_up_util > avg_ds_util + 0.05:
        bottleneck = "upstream"
    elif avg_ds_util > avg_up_util + 0.05:
        bottleneck = "downstream"
    else:
        bottleneck = "balanced"

    # Create result model
    result = CapacityResult(
        per_strain=[],  # Monte Carlo doesn't give per-strain breakdown easily
        total_feasible_batches=total_feasible,
        total_good_batches=total_good,
        total_annual_kg=kg_mean,
        weighted_up_utilization=avg_up_util,
        weighted_ds_utilization=avg_ds_util,
        bottleneck=bottleneck,
        kg_p10=kg_p10,
        kg_p50=kg_p50,
        kg_p90=kg_p90,
    )

    statistics = {
        "kg_mean": kg_mean,
        "kg_std": kg_std,
        "kg_p10": kg_p10,
        "kg_p50": kg_p50,
        "kg_p90": kg_p90,
        "samples": n_samples,
    }

    return summary_df, statistics, result


def evaluate_volume_options(
    strains: List[StrainInput],
    equipment: EquipmentConfig,
    volume_options_l: List[float],
    use_monte_carlo: bool = False,
    n_samples: int = 100,
) -> pd.DataFrame:
    """
    Evaluate capacity across multiple fermenter volume options.

    Args:
        strains: List of strain inputs
        equipment: Equipment configuration
        volume_options_l: List of fermenter volumes to evaluate (liters)
        use_monte_carlo: Whether to use Monte Carlo simulation
        n_samples: Number of samples for Monte Carlo

    Returns:
        DataFrame with capacity metrics for each volume option
    """
    results = []

    for volume in volume_options_l:
        if use_monte_carlo:
            _, stats, result = calculate_capacity_monte_carlo(
                strains, equipment, volume, n_samples
            )
            results.append(
                {
                    "volume_l": volume,
                    "working_volume_l": volume * 0.8,
                    "total_annual_kg": result.total_annual_kg,
                    "kg_p10": result.kg_p10,
                    "kg_p50": result.kg_p50,
                    "kg_p90": result.kg_p90,
                    "up_utilization": result.weighted_up_utilization,
                    "ds_utilization": result.weighted_ds_utilization,
                    "bottleneck": result.bottleneck,
                }
            )
        else:
            _, _, result = calculate_capacity_deterministic(strains, equipment, volume)
            results.append(
                {
                    "volume_l": volume,
                    "working_volume_l": volume * 0.8,
                    "total_annual_kg": result.total_annual_kg,
                    "total_feasible_batches": result.total_feasible_batches,
                    "total_good_batches": result.total_good_batches,
                    "up_utilization": result.weighted_up_utilization,
                    "ds_utilization": result.weighted_ds_utilization,
                    "bottleneck": result.bottleneck,
                }
            )

    return pd.DataFrame(results)


def capacity_meets_target(
    capacity_kg: float, target_tpa: float, tolerance: float = 0.01
) -> bool:
    """
    Check if capacity meets target TPA.

    Args:
        capacity_kg: Annual capacity in kg
        target_tpa: Target tons per annum
        tolerance: Tolerance fraction (default 1%)

    Returns:
        True if capacity meets target within tolerance
    """
    target_kg = target_tpa * 1000
    return capacity_kg >= target_kg * (1 - tolerance)


def get_strain_allocations(
    strains: List[str], reactors: int, ds_lines: int, policy: str = "inverse_ct"
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Get reactor and DS line allocations for strains.

    Args:
        strains: List of strain names
        reactors: Total number of reactors
        ds_lines: Total number of DS lines
        policy: Allocation policy

    Returns:
        Tuple of (reactor_allocations, ds_allocations)
    """
    n_strains = len(strains)

    if policy == "equal":
        reactor_alloc = {s: reactors / n_strains for s in strains}
        ds_alloc = {s: ds_lines / n_strains for s in strains}

    elif policy == "inverse_ct":
        # Get cycle times from database
        ct_up = []
        ct_ds = []
        for strain in strains:
            if strain in STRAIN_BATCH_DB:
                data = STRAIN_BATCH_DB[strain]
                ct_up.append(data["t_fedbatch_h"] + data["t_turnaround_h"])
                ct_ds.append(data["t_downstrm_h"])
            else:
                # Default values if strain not found
                ct_up.append(24.0)
                ct_ds.append(4.0)

        # Calculate inverse weights
        inv_ct_up = [1.0 / ct for ct in ct_up]
        inv_ct_ds = [1.0 / ct for ct in ct_ds]

        # Normalize and allocate
        total_inv_up = sum(inv_ct_up)
        total_inv_ds = sum(inv_ct_ds)

        reactor_alloc = {
            strains[i]: reactors * inv_ct_up[i] / total_inv_up for i in range(n_strains)
        }
        ds_alloc = {
            strains[i]: ds_lines * inv_ct_ds[i] / total_inv_ds for i in range(n_strains)
        }

    else:  # proportional or other
        # Default to equal if policy not recognized
        reactor_alloc = {s: reactors / n_strains for s in strains}
        ds_alloc = {s: ds_lines / n_strains for s in strains}

    return reactor_alloc, ds_alloc
