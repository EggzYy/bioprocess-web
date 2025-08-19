"""
Economic calculations module.
Provides NPV, IRR, cash flow analysis, and financial metrics.
"""

import math
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from .models import (
    EconomicAssumptions,
    LaborConfig,
    OpexConfig,
    CapexConfig,
    EconomicsResult,
    StrainInput,
)
from .presets import STRAIN_BATCH_DB


def npv(discount_rate: float, cash_flows: List[float]) -> float:
    """
    Calculate Net Present Value.

    Args:
        discount_rate: Discount rate (e.g., 0.10 for 10%)
        cash_flows: List of cash flows by period (year 0, 1, 2, ...)

    Returns:
        Net Present Value
    """
    return sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cash_flows))


def irr(
    cash_flows: List[float], guess: float = 0.2, tol: float = 1e-6, maxiter: int = 500
) -> float:
    """
    Calculate Internal Rate of Return with robust algorithm.
    Preserves behavior from pricing_integrated.py including bisection fallback.

    Args:
        cash_flows: List of cash flows
        guess: Initial guess for IRR
        tol: Tolerance for convergence
        maxiter: Maximum iterations

    Returns:
        Internal Rate of Return (NaN if undefined)
    """
    # Check if IRR is defined
    if not any(cf > 0 for cf in cash_flows) or not any(cf < 0 for cf in cash_flows):
        return float("nan")

    def npv_at_rate(r: float) -> float:
        """Calculate NPV at given rate."""
        total = 0.0
        denom = 1.0
        for t, cf in enumerate(cash_flows):
            if t == 0:
                total += cf
            else:
                denom *= 1.0 + r
                if denom <= 0:
                    return float("inf") if cf >= 0 else -float("inf")
                total += cf / denom
        return total

    # Try bisection method first if sign change exists
    low = -0.9999
    high = 1.0
    f_low = npv_at_rate(low)
    f_high = npv_at_rate(high)

    # Expand search range if needed
    while (
        math.isfinite(f_low)
        and math.isfinite(f_high)
        and f_low * f_high > 0
        and high < 1e3
    ):
        high *= 2.0
        f_high = npv_at_rate(high)

    # Bisection if sign change found
    if math.isfinite(f_low) and math.isfinite(f_high) and f_low * f_high <= 0:
        for _ in range(maxiter):
            mid = (low + high) / 2.0
            f_mid = npv_at_rate(mid)
            if not math.isfinite(f_mid) or abs(f_mid) < tol:
                return mid
            if f_low * f_mid <= 0:
                high, f_high = mid, f_mid
            else:
                low, f_low = mid, f_mid
        return (low + high) / 2.0

    # Fall back to Newton's method
    r = guess
    for _ in range(maxiter):
        if r <= -0.9999:
            r = -0.9999 + 1e-6
        f = npv_at_rate(r)

        # Calculate derivative
        try:
            fp = sum(
                -t * cf / ((1.0 + r) ** (t + 1))
                for t, cf in enumerate(cash_flows[1:], start=1)
            )
        except ZeroDivisionError:
            fp = float("inf")

        if not math.isfinite(f) or abs(fp) < 1e-12:
            break

        r_new = r - f / fp
        if r_new <= -0.9999 or not math.isfinite(r_new):
            r_new = r - 0.5  # Dampen away from singularity

        if abs(r_new - r) < tol:
            return r_new
        r = r_new

    return r


def payback_period(cash_flows: List[float]) -> float:
    """
    Calculate simple payback period.

    Args:
        cash_flows: List of cash flows

    Returns:
        Payback period in years (inf if never pays back)
    """
    cumulative = 0.0
    for year, cf in enumerate(cash_flows):
        cumulative += cf
        if cumulative >= 0:
            if year == 0:
                return 0.0
            # Linear interpolation for partial year
            prev_cumulative = cumulative - cf
            fraction = -prev_cumulative / cf if cf != 0 else 0
            return year - 1 + fraction
    return 999.0  # Return a large number instead of infinity


def calculate_depreciation(
    depreciable_amount: float, years: int = 10, method: str = "straight_line"
) -> List[float]:
    """
    Calculate depreciation schedule.

    Args:
        depreciable_amount: Amount to depreciate
        years: Depreciation period
        method: Depreciation method ('straight_line' or 'macrs')

    Returns:
        List of annual depreciation amounts
    """
    if method == "straight_line":
        annual_dep = depreciable_amount / years
        return [annual_dep] * years

    elif method == "macrs":
        # 7-year MACRS percentages
        macrs_7 = [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446]
        if years <= 7:
            return [depreciable_amount * pct for pct in macrs_7[:years]]
        else:
            deps = [depreciable_amount * pct for pct in macrs_7]
            deps.extend([0] * (years - 7))
            return deps

    else:
        # Default to straight line
        return [depreciable_amount / years] * years


def calculate_labor_cost(
    labor_config: LaborConfig, target_tpa: float, parity_mode: bool = False
) -> Tuple[float, int]:
    """
    Calculate total labor cost and FTE count.

    Args:
        labor_config: Labor configuration
        target_tpa: Target production (TPA)
        parity_mode: When True, mirror original baseline: min 15 FTEs; scale ~ linearly with TPA

    Returns:
        Tuple of (total_annual_cost, fte_count)
    """
    # Average salary (aligned with original position set of 15 roles)
    avg_salary = (
        labor_config.plant_manager_salary * 1
        + labor_config.fermentation_specialist_salary * 3
        + labor_config.downstream_process_operator_salary * 3
        + labor_config.general_technician_salary * 2
        + labor_config.qaqc_lab_tech_salary * 1
        + labor_config.maintenance_tech_salary * 1
        + labor_config.utility_operator_salary * 2
        + labor_config.logistics_clerk_salary * 1
        + labor_config.office_clerk_salary * 1
    ) / 15

    if parity_mode:
        # Original-equivalent: floor at 15 FTEs and scale ~ linearly beyond
        ftes = max(15.0, float(target_tpa))
    else:
        # New model: min_fte baseline plus growth per TPA over 10
        ftes = max(
            float(labor_config.min_fte),
            float(labor_config.min_fte) + (float(target_tpa) - 10.0) * float(labor_config.fte_per_tpa),
        )
    ftes = int(np.ceil(ftes))

    total_cost = ftes * avg_salary
    return total_cost, ftes


def calculate_raw_materials_cost(
    strains: List[StrainInput],
    batches_per_strain: Dict[str, float],
    fermenter_volume_l: float,
    working_volume_fraction: float = 0.8,
) -> float:
    """
    Calculate total raw materials cost.

    Args:
        strains: List of strain inputs
        batches_per_strain: Number of batches per strain
        fermenter_volume_l: Fermenter volume
        working_volume_fraction: Working volume fraction

    Returns:
        Total annual raw materials cost
    """
    total_cost = 0.0
    base_working_volume = 1600.0  # Base working volume from original (2000L @ 0.8)
    actual_working_volume = fermenter_volume_l * working_volume_fraction
    scale_factor = actual_working_volume / base_working_volume

    for strain in strains:
        if strain.name in batches_per_strain:
            batches = batches_per_strain[strain.name]
            # Scale costs for volume
            media_cost = strain.media_cost_usd * scale_factor
            cryo_cost = strain.cryo_cost_usd * scale_factor
            total_cost += (media_cost + cryo_cost) * batches

    return total_cost


def calculate_utilities_cost(
    strains: List[StrainInput],
    batches_per_strain: Dict[str, float],
    fermenter_volume_l: float,
    opex_config: OpexConfig,
    working_volume_fraction: float = 0.8,
) -> float:
    """
    Calculate total utilities cost.

    Args:
        strains: List of strain inputs
        batches_per_strain: Number of batches per strain
        fermenter_volume_l: Fermenter volume
        opex_config: OPEX configuration
        working_volume_fraction: Working volume fraction

    Returns:
        Total annual utilities cost
    """
    total_cost = 0.0
    working_volume_l = fermenter_volume_l * working_volume_fraction
    volume_m3 = working_volume_l / 1000.0

    for strain in strains:
        if strain.name in batches_per_strain:
            batches = batches_per_strain[strain.name]

            # Calculate electricity per batch (following documented units)
            # utility_rate_ferm_kw is already total kWh per batch
            ferm_kwh = strain.utility_rate_ferm_kw

            # Centrifuge scales with volume and time
            cent_kwh = (
                strain.utility_rate_cent_kw * strain.downstream_time_h * volume_m3
            )

            # Lyophilizer scales with 15% of working volume (m³) and time
            lyo_kwh = (
                strain.utility_rate_lyo_kw
                * strain.downstream_time_h
                * (working_volume_l * 0.15 / 1000.0)
            )

            total_kwh = ferm_kwh + cent_kwh + lyo_kwh
            electricity_cost = total_kwh * opex_config.electricity_usd_per_kwh

            # Steam cost
            batch_mass_kg = strain.yield_g_per_L * working_volume_l / 1000.0
            steam_cost = strain.utility_cost_steam * batch_mass_kg

            total_cost += (electricity_cost + steam_cost) * batches

    return total_cost


def calculate_revenue(
    annual_production_kg: float,
    product_prices: Dict[str, float],
    product_mix: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate annual revenue.

    Args:
        annual_production_kg: Total annual production in kg
        product_prices: Product prices by category
        product_mix: Optional product mix percentages

    Returns:
        Annual revenue
    """
    if product_mix:
        revenue = 0.0
        for product, fraction in product_mix.items():
            if product in product_prices:
                revenue += annual_production_kg * fraction * product_prices[product]
        return revenue
    else:
        # Use average price if no mix specified
        avg_price = np.mean(list(product_prices.values()))
        return annual_production_kg * avg_price


def calculate_licensing_costs(
    strains: List[StrainInput], ebitda: float
) -> Tuple[float, float]:
    """
    Calculate licensing costs.

    Args:
        strains: List of strain inputs
        ebitda: EBITDA before royalties

    Returns:
        Tuple of (fixed_cost, royalty_amount)
    """
    # Fixed licensing costs (one-time)
    fixed_cost = sum(s.licensing_fixed_cost_usd for s in strains)

    # Weighted royalty rate
    total_royalty_rate = 0.0
    if len(strains) > 0:
        # Simple average for now (should be production-weighted in full implementation)
        royalty_rates = [s.licensing_royalty_pct for s in strains]
        total_royalty_rate = np.mean(royalty_rates)

    royalty_amount = max(0.0, ebitda * total_royalty_rate)

    return fixed_cost, royalty_amount


def build_cash_flows(
    capex: float,
    annual_revenue: float,
    annual_opex: float,
    tax_rate: float,
    depreciation_schedule: List[float],
    ramp_up_schedule: List[float],
    licensing_fixed: float = 0.0,
    licensing_royalty_rate: float = 0.0,
    variable_opex_share: float = 0.85,
    parity_mode: bool = False,
    steady_state_kg: float = 0.0,  # Required for parity mode
    project_years: int = 12,
) -> List[float]:
    """
    Build cash flow projections.
    """
    cash_flows = []
    total_capex = capex + licensing_fixed

    # Parity mode requires a different OPEX calculation method
    if parity_mode:
        if steady_state_kg <= 0:
            raise ValueError("steady_state_kg must be positive for parity mode cash flow calculation.")
        var_opex_per_kg = (variable_opex_share * annual_opex) / steady_state_kg
        fixed_opex = (1 - variable_opex_share) * annual_opex
    else:
        # Modern implementation logic (can be refined later)
        var_opex_per_kg = 0  # Not used in this path
        fixed_opex = 0  # Not used in this path

    for year in range(project_years + 1):
        if year == 0:
            cf = -total_capex * 0.70
        elif year == 1:
            cf = -total_capex * 0.30
        else:
            idx = year - 2
            utilization = ramp_up_schedule[idx] if idx < len(ramp_up_schedule) else (ramp_up_schedule[-1] if ramp_up_schedule else 1.0)

            revenue = annual_revenue * utilization

            if parity_mode:
                # Mimic original script: COGS = (ramped kg * var_opex/kg) + fixed_opex
                # The revenue is based on actual production, but COGS ramp-up is based on target production (steady_state_kg)
                ramped_kg = steady_state_kg * utilization
                cogs = ramped_kg * var_opex_per_kg + fixed_opex
            else:
                # Modern mode: scale total opex by utilization
                cogs = annual_opex * utilization

            ebitda_pre = revenue - cogs
            royalty = max(0.0, ebitda_pre * licensing_royalty_rate)
            ebitda = ebitda_pre - royalty

            depreciation = depreciation_schedule[idx] if idx < len(depreciation_schedule) else 0.0
            ebt = ebitda - depreciation
            tax = max(0.0, ebt * tax_rate)
            cf = ebitda - tax

        cash_flows.append(cf)

    return cash_flows


def calculate_economics(
    target_tpa: float,
    annual_production_kg: float,
    total_batches: float,
    batches_per_strain: Dict[str, float],
    strains: List[StrainInput],
    fermenter_volume_l: float,
    equipment_cost: float,
    assumptions: EconomicAssumptions,
    labor_config: LaborConfig,
    capex_config: CapexConfig,
    opex_config: OpexConfig,
    product_prices: Dict[str, float],
    working_volume_fraction: float = 0.8,
    capex_override: Optional[Dict[str, float]] = None,
) -> EconomicsResult:
    """
    Calculate complete economic analysis.

    Args:
        target_tpa: Target production (TPA)
        annual_production_kg: Actual annual production (kg)
        total_batches: Total batches per year
        batches_per_strain: Batches by strain name
        strains: List of strain inputs
        fermenter_volume_l: Fermenter volume
        equipment_cost: Total equipment cost
        assumptions: Economic assumptions
        labor_config: Labor configuration
        capex_config: CAPEX configuration
        opex_config: OPEX configuration
        product_prices: Product prices
        working_volume_fraction: Working volume fraction

    Returns:
        EconomicsResult with all financial metrics
    """
    # If override is provided, trust it for CAPEX components and use parity economics
    if capex_override:
        land_cost = float(capex_override.get("land", 0.0))
        building_cost = float(capex_override.get("building", 0.0))
        equipment_cost = float(capex_override.get("equipment", equipment_cost))
        contingency = float(capex_override.get("cont", 0.0))
        working_capital = float(capex_override.get("wc", 0.0))
        total_capex = float(
            capex_override.get(
                "total",
                land_cost
                + building_cost
                + equipment_cost
                + contingency
                + working_capital,
            )
        )
        fixed_licensing = float(capex_override.get("licensing_fixed_total", 0.0))
    else:
        # CAPEX components
        if capex_config.parity_mode:
            # Parity with original (capex_estimate_2):
            # land/building from facility area; include installation at 15% of equipment;
            # working capital = 10% of direct costs (land + building + equipment + installation)
            # Facility area scales with fermenters and volume scale
            fermenters = 0
            try:
                fermenters = equipment_result.counts.get("fermenters", 0)  # type: ignore[attr-defined]
            except Exception:
                fermenters = 0
            if fermenters <= 0:
                # Fallback to suggested/reactors_total
                fermenters = (
                    0
                )
            volume_scale = (fermenter_volume_l / 2000.0) ** 0.6 if fermenter_volume_l > 0 else 1.0
            facility_area = 1000.0 + (fermenters * 500.0) * volume_scale
            land_cost = 250.0 * facility_area
            building_cost = 500.0 * 500.0 + 500.0 * 2000.0 * volume_scale + 2000.0 * (
                fermenters * 500.0 * volume_scale
            )
            installation_cost = equipment_cost * 0.15
            direct_capex = land_cost + building_cost + equipment_cost + installation_cost
            contingency = direct_capex * 0.125
            working_capital = direct_capex * 0.10
        else:
            # Area-based modern path
            facility_area = 1000 + (fermenter_volume_l / 2000) * 500  # Scale with volume
            land_cost = facility_area * capex_config.land_cost_per_m2
            building_cost = facility_area * capex_config.building_cost_per_m2
            installation_cost = equipment_cost * capex_config.installation_factor
            # Total direct CAPEX (include installation like original)
            direct_capex = land_cost + building_cost + equipment_cost + installation_cost
            contingency = direct_capex * capex_config.contingency_factor
            # Working capital estimated from OPEX months (modern path)
            raw_materials_cost = calculate_raw_materials_cost(
                strains,
                batches_per_strain,
                fermenter_volume_l,
                working_volume_fraction=working_volume_fraction,
            )
            utilities_cost = calculate_utilities_cost(
                strains,
                batches_per_strain,
                fermenter_volume_l,
                opex_config,
                working_volume_fraction=working_volume_fraction,
            )
            labor_cost, _ = calculate_labor_cost(labor_config, target_tpa, parity_mode=capex_config.parity_mode)
            maintenance_cost = equipment_cost * assumptions.maintenance_pct_of_equip
            ga_other_cost = assumptions.ga_other_scale_factor * target_tpa * 1000
            total_opex = (
                raw_materials_cost
                + utilities_cost
                + labor_cost
                + maintenance_cost
                + ga_other_cost
            )
            working_capital = total_opex * (capex_config.working_capital_months / 12.0)

        # Licensing
        fixed_licensing = sum(s.licensing_fixed_cost_usd for s in strains)

        # Total CAPEX
        total_capex = direct_capex + contingency + working_capital + fixed_licensing

    # OPEX components still needed for EBITDA
    raw_materials_cost = calculate_raw_materials_cost(
        strains,
        batches_per_strain,
        fermenter_volume_l,
        working_volume_fraction=working_volume_fraction,
    )
    utilities_cost = calculate_utilities_cost(
        strains,
        batches_per_strain,
        fermenter_volume_l,
        opex_config,
        working_volume_fraction=working_volume_fraction,
    )
    labor_cost, _ = calculate_labor_cost(labor_config, target_tpa, parity_mode=capex_config.parity_mode)
    maintenance_cost = equipment_cost * assumptions.maintenance_pct_of_equip
    ga_other_cost = assumptions.ga_other_scale_factor * target_tpa * 1000
    total_opex = (
        raw_materials_cost
        + utilities_cost
        + labor_cost
        + maintenance_cost
        + ga_other_cost
    )

    # Production-weighted royalty rate
    total_kg_for_royalty = sum(
        batches_per_strain.get(s.name, 0)
        * s.yield_g_per_L
        * (fermenter_volume_l * working_volume_fraction)
        / 1000.0
        for s in strains
    )
    if total_kg_for_royalty > 0:
        weighted_royalty_sum = sum(
            s.licensing_royalty_pct
            * (
                batches_per_strain.get(s.name, 0)
                * s.yield_g_per_L
                * (fermenter_volume_l * working_volume_fraction)
                / 1000.0
            )
            for s in strains
        )
        avg_royalty_rate = weighted_royalty_sum / total_kg_for_royalty
    else:
        avg_royalty_rate = (
            np.mean([s.licensing_royalty_pct for s in strains]) if strains else 0.0
        )

    # Revenue (per-strain, using strain-specific prices when available)
    annual_revenue = 0.0
    if annual_production_kg > 0 and total_batches > 0:
        working_volume_l = fermenter_volume_l * working_volume_fraction
        avg_price = (
            float(np.mean(list(product_prices.values()))) if product_prices else 0.0
        )
        logger = logging.getLogger(__name__)
        for s in strains:
            batches = float(batches_per_strain.get(s.name, 0.0))
            batch_mass_kg = s.yield_g_per_L * working_volume_l / 1000.0
            kg = batches * batch_mass_kg
            # Prefer strain-specific price from STRAIN_BATCH_DB if defined
            price = None
            sb = STRAIN_BATCH_DB.get(s.name, {})
            explicit = sb.get("price_per_kg")
            if explicit is not None:
                price = float(explicit)
            else:
                for k, v in sb.items():
                    if k.startswith("price_") and k.endswith("_per_kg"):
                        price = float(v)
                        break
            if price is None:
                logger.warning(
                    f"No explicit price found for strain '{s.name}'. Using average product price {avg_price}."
                )
                price = avg_price
            annual_revenue += kg * price

    # EBITDA calculation and margins
    ebitda_pre_royalty = annual_revenue - total_opex
    royalty_amount = max(0.0, ebitda_pre_royalty * avg_royalty_rate)
    ebitda = ebitda_pre_royalty - royalty_amount
    ebitda_margin = ebitda / annual_revenue if annual_revenue > 0 else 0.0

    # Depreciation schedule parity: (total_capex - licensing_fixed) * 0.5 over 10 years
    depreciable_base = max(0.0, total_capex - fixed_licensing) * 0.5
    depreciation_schedule = calculate_depreciation(
        depreciable_base, assumptions.depreciation_years
    )

    # Ramp-up schedule parity: [0.40, 0.60, 0.75, 0.85] + [0.85]*7
    ramp_up = [0.40, 0.60, 0.75, 0.85] + [0.85] * 7

    # Build cash flows (Year 0: -70%, Year 1: -30%)
    cash_flows = build_cash_flows(
        capex=total_capex - fixed_licensing,  # base CAPEX (exclude licensing from base)
        annual_revenue=annual_revenue,
        annual_opex=total_opex,
        tax_rate=assumptions.tax_rate,
        depreciation_schedule=depreciation_schedule,
        ramp_up_schedule=ramp_up,
        licensing_fixed=fixed_licensing,
        licensing_royalty_rate=avg_royalty_rate,
        project_years=12,
        variable_opex_share=assumptions.variable_opex_share,
        parity_mode=capex_config.parity_mode,
        steady_state_kg=target_tpa * 1000.0,  # Use target for ramp-up calculations
    )

    # Financial metrics
    npv_value = npv(assumptions.discount_rate, cash_flows)
    irr_value = irr(cash_flows)
    payback = payback_period(cash_flows)

    return EconomicsResult(
        annual_revenue=annual_revenue,
        raw_materials_cost=raw_materials_cost,
        utilities_cost=utilities_cost,
        labor_cost=labor_cost,
        maintenance_cost=maintenance_cost,
        ga_other_cost=ga_other_cost,
        total_opex=total_opex,
        land_cost=land_cost if "land_cost" in locals() else 0.0,
        building_cost=building_cost if "building_cost" in locals() else 0.0,
        equipment_cost=equipment_cost,
        contingency=contingency,
        working_capital=working_capital,
        total_capex=total_capex,
        npv=npv_value,
        irr=irr_value if math.isfinite(irr_value) else 0.0,
        payback_years=payback,
        ebitda_margin=ebitda_margin,
        cash_flows=cash_flows,
        licensing_fixed=fixed_licensing,
        licensing_royalty_rate=avg_royalty_rate,
    )
