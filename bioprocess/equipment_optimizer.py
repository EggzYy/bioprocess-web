"""
Equipment optimizer module.
Calculates optimal equipment configuration to meet target production.
"""

import math
from typing import List, Tuple
from .models import StrainInput, EquipmentConfig
from .presets import STRAIN_BATCH_DB


def calculate_required_equipment_for_target(
    target_tpa: float,
    strains: List[StrainInput],
    fermenter_volume_l: float = 2000,
    hours_per_year: float = 8760,
    upstream_availability: float = 0.92,
    downstream_availability: float = 0.90,
    quality_yield: float = 0.98,
) -> Tuple[int, int]:
    """
    Calculate minimum equipment required to meet target production.

    Args:
        target_tpa: Target production in tons per annum
        strains: List of strains to produce
        fermenter_volume_l: Fermenter volume in liters
        hours_per_year: Operating hours per year
        upstream_availability: Upstream equipment availability
        downstream_availability: Downstream equipment availability
        quality_yield: Quality/rejection yield

    Returns:
        Tuple of (required_reactors, required_ds_lines)
    """
    target_kg = target_tpa * 1000
    working_volume = fermenter_volume_l * 0.8

    # Calculate average batch size and cycle times
    total_batch_mass = 0
    total_upstream_time = 0
    total_downstream_time = 0

    for strain in strains:
        # Get strain properties
        if hasattr(strain, "yield_g_per_L"):
            yield_g_l = strain.yield_g_per_L
            ferm_h = strain.fermentation_time_h
            turn_h = strain.turnaround_time_h
            down_h = strain.downstream_time_h
        else:
            # Fallback to database
            strain_name = strain.name if hasattr(strain, "name") else str(strain)
            if strain_name in STRAIN_BATCH_DB:
                data = STRAIN_BATCH_DB[strain_name]
                yield_g_l = data.get("yield_g_per_L", 10)
                ferm_h = data.get("t_fedbatch_h", 24)
                turn_h = data.get("t_turnaround_h", 9)
                down_h = data.get("t_downstrm_h", 4)
            else:
                # Default values
                yield_g_l = 10
                ferm_h = 24
                turn_h = 9
                down_h = 4

        batch_mass_kg = (working_volume * yield_g_l) / 1000
        upstream_cycle_h = ferm_h + turn_h

        total_batch_mass += batch_mass_kg
        total_upstream_time += upstream_cycle_h
        total_downstream_time += down_h

    # Calculate averages
    n_strains = len(strains) if strains else 1
    avg_batch_mass = total_batch_mass / n_strains
    avg_upstream_cycle = total_upstream_time / n_strains
    avg_downstream_time = total_downstream_time / n_strains

    # Calculate required batches
    required_batches_good = target_kg / avg_batch_mass
    required_batches_total = required_batches_good / quality_yield

    # Calculate reactor requirements
    available_upstream_hours = hours_per_year * upstream_availability
    batches_per_reactor_year = available_upstream_hours / avg_upstream_cycle
    required_reactors = math.ceil(required_batches_total / batches_per_reactor_year)

    # Ensure minimum reactors
    required_reactors = max(2, required_reactors)  # Minimum 2 for redundancy

    # Calculate downstream requirements
    available_downstream_hours = hours_per_year * downstream_availability
    batches_per_ds_line_year = available_downstream_hours / avg_downstream_time
    required_ds_lines = math.ceil(required_batches_total / batches_per_ds_line_year)

    # Ensure minimum DS lines
    required_ds_lines = max(1, required_ds_lines)

    return required_reactors, required_ds_lines


def adjust_equipment_for_target(scenario_input, target_tpa: float) -> EquipmentConfig:
    """
    Adjust equipment configuration to meet target production.

    Args:
        scenario_input: ScenarioInput object
        target_tpa: Target production TPA

    Returns:
        Adjusted EquipmentConfig
    """
    # Calculate required equipment
    required_reactors, required_ds_lines = calculate_required_equipment_for_target(
        target_tpa,
        scenario_input.strains,
        scenario_input.volumes.base_fermenter_vol_l,
        scenario_input.assumptions.hours_per_year,
        scenario_input.assumptions.upstream_availability,
        scenario_input.assumptions.downstream_availability,
        scenario_input.assumptions.quality_yield,
    )

    # Create adjusted config
    adjusted_config = EquipmentConfig(
        reactors_total=required_reactors,
        ds_lines_total=required_ds_lines,
        spare_reactors=scenario_input.equipment.spare_reactors,
        seed_fermenters_ratio=scenario_input.equipment.seed_fermenters_ratio,
    )

    return adjusted_config
