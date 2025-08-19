"""
Equipment sizing module.
Calculates equipment counts, specifications, and costs.
"""

import math
from typing import Dict, List, Any, Tuple
from .models import CapexConfig, VolumePlan, EquipmentResult


def scale_equipment_cost(
    base_cost: float, base_size: float, actual_size: float, exponent: float = 0.6
) -> float:
    """
    Scale equipment cost using the six-tenths rule.

    Args:
        base_cost: Cost at base size
        base_size: Base equipment size
        actual_size: Actual equipment size
        exponent: Scaling exponent (typically 0.6)

    Returns:
        Scaled equipment cost
    """
    if base_size <= 0 or actual_size <= 0:
        return base_cost
    return base_cost * (actual_size / base_size) ** exponent


def calculate_fermenter_costs(
    count: int, volume_l: float, capex_config: CapexConfig
) -> Dict[str, float]:
    """
    Calculate fermenter costs.

    Args:
        count: Number of fermenters
        volume_l: Volume per fermenter (liters)
        capex_config: CAPEX configuration

    Returns:
        Dictionary with cost breakdown
    """
    # Scale cost from base 2000L
    base_volume = 2000.0
    unit_cost = scale_equipment_cost(
        capex_config.fermenter_base_cost,
        base_volume,
        volume_l,
        capex_config.fermenter_scale_exponent,
    )

    total_cost = unit_cost * count

    return {
        "unit_cost": unit_cost,
        "total_cost": total_cost,
        "count": count,
        "volume_l": volume_l,
    }


def calculate_downstream_equipment(
    ds_lines: int,
    fermenter_volume_l: float,
    strains: List[Dict[str, Any]],  # Pass strain data instead of anaerobic flag
    capex_config: CapexConfig,
) -> Dict[str, Any]:
    """
    Calculate downstream equipment requirements and costs.

    Args:
        ds_lines: Number of downstream lines
        fermenter_volume_l: Fermenter volume
        strains: List of strain dictionaries with processing properties
        capex_config: CAPEX configuration

    Returns:
        Dictionary with equipment specifications and costs
    """
    equipment = {}

    # Determine if extra TFF is needed based on strain properties
    requires_extra_tff = any(
        strain.get("requires_tff", False)
        or strain.get("respiration_type", "aerobic") in ["anaerobic", "facultative"]
        for strain in strains
    )

    # Get maximum downstream complexity factor
    max_complexity = (
        max(strain.get("downstream_complexity", 1.0) for strain in strains)
        if strains
        else 1.0
    )

    # Centrifuges (one per DS line, adjusted for complexity)
    centrifuges = max(1, ds_lines)
    centrifuge_cost = capex_config.centrifuge_cost * max_complexity
    equipment["centrifuges"] = {
        "count": centrifuges,
        "unit_cost": centrifuge_cost,
        "total_cost": centrifuges * centrifuge_cost,
    }

    # TFF skids (for anaerobic/facultative or shear-sensitive strains)
    tff_skids = max(1, ds_lines if requires_extra_tff else 1)
    equipment["tff_skids"] = {
        "count": tff_skids,
        "unit_cost": capex_config.tff_skid_cost,
        "total_cost": tff_skids * capex_config.tff_skid_cost,
    }

    # Lyophilizers (20 m² units, adjusted for complexity)
    lyophilizers = ds_lines
    lyophilizer_cost = (
        capex_config.lyophilizer_cost_per_m2 * 20 * max_complexity
    )  # 20 m² units
    equipment["lyophilizers"] = {
        "count": lyophilizers,
        "unit_cost": lyophilizer_cost,
        "total_cost": lyophilizers * lyophilizer_cost,
        "size_m2": 20,
        "complexity_factor": max_complexity,
    }

    # Calculate total downstream cost
    total_ds_cost = (
        equipment["centrifuges"]["total_cost"]
        + equipment["tff_skids"]["total_cost"]
        + equipment["lyophilizers"]["total_cost"]
    )

    equipment["total_downstream_cost"] = total_ds_cost

    return equipment


def calculate_auxiliary_equipment(
    fermenters: int,
    fermenter_volume_l: float,
    volume_plan: VolumePlan,
    capex_config: CapexConfig,
) -> Dict[str, Any]:
    """
    Calculate auxiliary equipment (seed fermenters, media tanks, etc.).

    Args:
        fermenters: Number of main fermenters
        fermenter_volume_l: Main fermenter volume
        volume_plan: Volume configuration
        capex_config: CAPEX configuration

    Returns:
        Dictionary with auxiliary equipment specs and costs
    """
    equipment = {}

    # Seed fermenters (12.5% of main fermenter size)
    seed_volume = fermenter_volume_l * volume_plan.seed_fermenter_ratio
    seed_count = max(2, math.ceil(fermenters * 0.7))  # 70% of main fermenters
    seed_unit_cost = scale_equipment_cost(
        capex_config.fermenter_base_cost * 0.3,  # Seed fermenters are cheaper
        2000.0,
        seed_volume,
        capex_config.fermenter_scale_exponent,
    )

    equipment["seed_fermenters"] = {
        "count": seed_count,
        "volume_l": seed_volume,
        "unit_cost": seed_unit_cost,
        "total_cost": seed_count * seed_unit_cost,
    }

    # Media preparation tanks (125% of fermenter volume)
    media_volume = fermenter_volume_l * volume_plan.media_tank_ratio
    media_count = fermenters  # One per fermenter
    media_unit_cost = scale_equipment_cost(
        capex_config.fermenter_base_cost * 0.2,  # Media tanks are simpler
        2000.0,
        media_volume,
        capex_config.fermenter_scale_exponent,
    )

    equipment["media_tanks"] = {
        "count": media_count,
        "volume_l": media_volume,
        "unit_cost": media_unit_cost,
        "total_cost": media_count * media_unit_cost,
    }

    # Other equipment (fixed items)
    equipment["cone_mill"] = {"count": 1, "unit_cost": 50000, "total_cost": 50000}

    equipment["v_blender"] = {
        "count": 1,
        "volume_l": 500,
        "unit_cost": 30000,
        "total_cost": 30000,
    }

    equipment["qc_lab"] = {"count": 1, "unit_cost": 250000, "total_cost": 250000}

    # Total auxiliary cost
    total_aux_cost = sum(
        eq["total_cost"]
        for eq in equipment.values()
        if isinstance(eq, dict) and "total_cost" in eq
    )
    equipment["total_auxiliary_cost"] = total_aux_cost

    return equipment


def calculate_utilities_infrastructure(
    process_equipment_cost: float,
    tff_skids: int,
    target_tpa: float,
    capex_config: CapexConfig,
) -> Dict[str, float]:
    """
    Calculate utilities infrastructure costs.
    Matches original pricing_integrated.py implementation.

    Args:
        process_equipment_cost: Total process equipment cost
        tff_skids: Number of TFF skids
        target_tpa: Target production (TPA)
        capex_config: CAPEX configuration

    Returns:
        Dictionary with utilities costs
    """
    # Based on original implementation:
    # max(1, ceil(tff_skids*0.5))*(100000+150000+400000+120000+250000)
    # AutoClave, Purified Water, Water for Injection, Clean Steam, CIP

    utility_lines = max(1, math.ceil(tff_skids * 0.5))
    base_costs = {
        "autoclave": 100000,
        "purified_water": 150000,
        "wfi_system": 400000,
        "clean_steam": 120000,
        "cip_system": 250000,
    }

    utilities = {}
    total_cost = 0

    for name, cost in base_costs.items():
        utilities[name] = cost * utility_lines
        total_cost += utilities[name]

    utilities["total_utilities"] = total_cost
    return utilities


def calculate_equipment_sizing(
    fermenters: int,
    ds_lines: int,
    fermenter_volume_l: float,
    strains: List[Dict[str, Any]],  # Pass strain data instead of anaerobic flag
    volume_plan: VolumePlan,
    capex_config: CapexConfig,
    target_tpa: float,
) -> EquipmentResult:
    """
    Calculate complete equipment sizing and costs.

    Args:
        fermenters: Number of fermenters
        ds_lines: Number of downstream lines
        fermenter_volume_l: Fermenter volume
        strains: List of strain dictionaries with processing properties
        volume_plan: Volume configuration
        capex_config: CAPEX configuration

    Returns:
        EquipmentResult with all specifications and costs
    """
    # Main fermenters
    fermenter_costs = calculate_fermenter_costs(
        fermenters, fermenter_volume_l, capex_config
    )

    # Downstream equipment
    downstream_eq = calculate_downstream_equipment(
        ds_lines, fermenter_volume_l, strains, capex_config
    )

    # Auxiliary equipment
    auxiliary_eq = calculate_auxiliary_equipment(
        fermenters, fermenter_volume_l, volume_plan, capex_config
    )

    # Process equipment total
    process_equipment_cost = (
        fermenter_costs["total_cost"]
        + downstream_eq["total_downstream_cost"]
        + auxiliary_eq["total_auxiliary_cost"]
    )

    # Utilities infrastructure (matching original implementation)
    utilities = calculate_utilities_infrastructure(
        process_equipment_cost,
        downstream_eq["tff_skids"]["count"],
        target_tpa,
        capex_config,
    )

    # Total equipment cost
    total_equipment_cost = process_equipment_cost + utilities["total_utilities"]

    # Installation cost
    installation_cost = total_equipment_cost * capex_config.installation_factor

    # Total installed cost
    total_installed_cost = total_equipment_cost + installation_cost

    # Build counts dictionary
    counts = {
        "fermenters": fermenters,  # Use standard key name
        f"{fermenter_volume_l}L_fermenters": fermenters,  # Keep detailed key too
        "seed_fermenters": auxiliary_eq["seed_fermenters"]["count"],
        "media_tanks": auxiliary_eq["media_tanks"]["count"],
        "centrifuges": downstream_eq["centrifuges"]["count"],
        "tff_skids": downstream_eq["tff_skids"]["count"],
        "lyophilizers": downstream_eq["lyophilizers"]["count"],
        "cone_mills": 1,
        "v_blenders": 1,
        "qc_labs": 1,
    }

    # Build specifications dictionary
    specifications = {
        "fermenter_volume_l": fermenter_volume_l,
        "seed_fermenter_volume_l": auxiliary_eq["seed_fermenters"]["volume_l"],
        "media_tank_volume_l": auxiliary_eq["media_tanks"]["volume_l"],
        "lyophilizer_size_m2": downstream_eq["lyophilizers"]["size_m2"],
        "v_blender_volume_l": 500,
        "strain_processing_requirements": [
            {
                "name": strain.get("name", "Unknown"),
                "respiration_type": strain.get("respiration_type", "aerobic"),
                "requires_tff": strain.get("requires_tff", False),
                "downstream_complexity": strain.get("downstream_complexity", 1.0),
            }
            for strain in strains
        ]
        if strains
        else [],
    }

    # Add detailed breakdown to specifications
    specifications["cost_breakdown"] = {
        "fermenters": fermenter_costs,
        "downstream": downstream_eq,
        "auxiliary": auxiliary_eq,
        "utilities": utilities,
    }

    return EquipmentResult(
        counts=counts,
        specifications=specifications,
        equipment_cost=total_equipment_cost,
        installation_cost=installation_cost,
        utilities_cost=utilities["total_utilities"],
        total_installed_cost=total_installed_cost,
    )


def estimate_facility_area(
    fermenters: int, ds_lines: int, fermenter_volume_l: float
) -> Dict[str, float]:
    """
    Estimate facility area requirements.

    Args:
        fermenters: Number of fermenters
        ds_lines: Number of downstream lines
        fermenter_volume_l: Fermenter volume

    Returns:
        Dictionary with area breakdown in m²
    """
    # Scale areas based on equipment
    fermenter_area_per_unit = 50 + (fermenter_volume_l / 1000) * 10  # m²
    ds_area_per_line = 100  # m² per DS line

    areas = {
        "fermentation_suite": fermenters * fermenter_area_per_unit,
        "downstream_suite": ds_lines * ds_area_per_line,
        "seed_lab": 100,
        "qc_lab": 150,
        "warehouse": 200 + fermenters * 20,
        "utilities": 150 + fermenters * 10,
        "offices": 200,
        "corridors_hvac": 0,  # Will be calculated as % of production
    }

    production_area = sum(areas.values())
    areas["corridors_hvac"] = production_area * 0.3  # 30% for corridors/HVAC

    areas["total_area"] = sum(areas.values())

    return areas


def calculate_capex_estimate_original(
    target_tpa: float,
    fermenters: int,
    ds_lines: int,
    fermenter_volume_l: float,
    licensing_fixed_total: float = 0.0,
) -> Tuple[float, Dict[str, Any]]:
    """
    Replicate original capex_estimate_2 from pricing_integrated_original.py.
    Returns total CAPEX and a breakdown dict with keys matching the original:
    {"equip", "building", "land", "install", "direct", "cont", "wc", "licensing_fixed_total"}
    """
    from math import ceil

    # Map DS lines ~ lyophilizer trains (conservative)
    lyos_needed = max(2, ds_lines)
    centrifuges = ceil(lyos_needed * 0.4)
    tff_skids = ceil(lyos_needed * 0.4)

    # Scale fermenter cost with volume using six-tenths rule
    base_volume = 2000.0
    base_fermenter_cost = 150000.0
    volume_scale_factor = (
        (fermenter_volume_l / base_volume) ** 0.6 if fermenter_volume_l > 0 else 1.0
    )

    # Building/land formulas from original
    facility_area = 1000 + (fermenters * 500) * volume_scale_factor
    land_cost = 250 * facility_area
    building_cost = (
        500 * 500
        + 500 * 2000 * volume_scale_factor
        + 2000 * (fermenters * 500 * volume_scale_factor)
    )

    # Equipment items (scaled where applicable)
    fermenter_cost = fermenters * base_fermenter_cost * volume_scale_factor
    seed_fermenter_cost = (
        (max(2, ceil(fermenters * 0.7)) + 1) * 50000 * volume_scale_factor
    )
    media_tank_cost = ceil(fermenters * 4 / 7) * 75000 * volume_scale_factor
    lyophilizer_cost = max(1, ds_lines) * 400000 * volume_scale_factor
    centrifuge_cost = centrifuges * 120000 * volume_scale_factor
    tff_cost = tff_skids * 100000 * volume_scale_factor
    mill_blend_transfer_cost = max(1, ceil(tff_skids * 0.5)) * 125000
    utility_systems_cost = max(1, ceil(tff_skids * 0.5)) * (
        100000 + 150000 + 400000 + 120000 + 250000
    )  # AutoClave, Purified Water, WFI, Clean Steam, CIP
    qc_lab_equipment = 180000 / 20000 * target_tpa * 1000

    total_equipment_cost = (
        fermenter_cost
        + seed_fermenter_cost
        + media_tank_cost
        + lyophilizer_cost
        + centrifuge_cost
        + tff_cost
        + mill_blend_transfer_cost
        + utility_systems_cost
        + qc_lab_equipment
    )

    installation_cost = total_equipment_cost * 0.15

    direct_costs = building_cost + total_equipment_cost + installation_cost

    contingency = direct_costs * 0.125

    working_capital = direct_costs * 0.10

    total_capex = direct_costs + contingency + working_capital + licensing_fixed_total

    breakdown = {
        "equip": total_equipment_cost,
        "building": building_cost,
        "land": land_cost,
        "install": installation_cost,
        "direct": direct_costs,
        "cont": contingency,
        "wc": working_capital,
        "lyos_needed": lyos_needed,
        "licensing_fixed_total": licensing_fixed_total,
        "total": total_capex,
    }

    return total_capex, breakdown


def calculate_capex_estimate(
    target_tpa: float,
    fermenters: int,
    ds_lines: int,
    fermenter_volume_l: float,
    strains: List[Dict[str, Any]],  # Pass strain data instead of anaerobic flag
    volume_plan: VolumePlan,
    capex_config: CapexConfig,
    licensing_fixed_total: float = 0.0,
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate complete CAPEX estimate.

    Args:
        target_tpa: Target production (TPA)
        fermenters: Number of fermenters
        ds_lines: Number of downstream lines
        fermenter_volume_l: Fermenter volume
        strains: List of strain dictionaries with processing properties
        volume_plan: Volume configuration
        capex_config: CAPEX configuration
        licensing_fixed_total: Total fixed licensing costs

    Returns:
        Tuple of (total_capex, breakdown_dict)
    """
    # Equipment sizing and costs
    equipment_result = calculate_equipment_sizing(
        fermenters,
        ds_lines,
        fermenter_volume_l,
        strains,
        volume_plan,
        capex_config,
        target_tpa,
    )

    # Facility area
    areas = estimate_facility_area(fermenters, ds_lines, fermenter_volume_l)

    # Land and building costs
    land_cost = areas["total_area"] * capex_config.land_cost_per_m2
    building_cost = areas["total_area"] * capex_config.building_cost_per_m2

    # Direct costs
    direct_costs = land_cost + building_cost + equipment_result.total_installed_cost

    # Contingency
    contingency = direct_costs * capex_config.contingency_factor

    # Working capital (placeholder - should be based on OPEX)
    working_capital = target_tpa * 50000  # Simplified estimate

    # Total CAPEX
    total_capex = direct_costs + contingency + working_capital + licensing_fixed_total

    breakdown = {
        "land": land_cost,
        "building": building_cost,
        "equipment": equipment_result.equipment_cost,
        "installation": equipment_result.installation_cost,
        "utilities_infrastructure": equipment_result.utilities_cost,
        "direct_total": direct_costs,
        "contingency": contingency,
        "working_capital": working_capital,
        "licensing_fixed": licensing_fixed_total,
        "total": total_capex,
        "areas": areas,
        "equipment_details": equipment_result,
    }

    return total_capex, breakdown
