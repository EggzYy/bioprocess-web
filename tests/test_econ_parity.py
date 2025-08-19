import math
from bioprocess.econ import build_cash_flows, calculate_labor_cost
from bioprocess.models import LaborConfig


def test_build_cash_flows_parity_mode_variable_ramp():
    # Steady-state values
    capex = 1_000_000.0
    annual_revenue = 10_000_000.0
    annual_opex = 4_000_000.0
    tax_rate = 0.25
    depreciation_schedule = [0.0] * 10
    # Ramp schedule aligns with econ.build_cash_flows indexing:
    # year 0: -70% CAPEX, year 1: -30% CAPEX, year 2 uses ramp[0]=0.0, year 3 ramp[1]=0.0, year 4 ramp[2]=0.40
    ramp = [0.0, 0.0, 0.40, 0.60, 0.75, 0.85] + [0.85] * 7

    flows = build_cash_flows(
        capex,
        annual_revenue,
        annual_opex,
        tax_rate,
        depreciation_schedule,
        ramp,
        licensing_fixed=0.0,
        licensing_royalty_rate=0.0,
        project_years=12,
        variable_opex_share=0.85,
        parity_mode=True,
    )

    # Years 0 and 1 are CAPEX outflows
    assert flows[0] == -capex * 0.70
    assert flows[1] == -capex * 0.30

    # Year 2 (first operating year): utilization=0.0 -> only fixed OPEX applied
    fixed = annual_opex * (1 - 0.85)
    assert math.isclose(flows[2], -fixed, rel_tol=1e-9)

    # Year 4 (third operating year by ramp): utilization=0.40
    util = 0.40
    variable = annual_opex * 0.85 * util
    opex = fixed + variable
    revenue = annual_revenue * util
    ebitda = revenue - opex
    tax = max(0.0, ebitda * tax_rate)
    expected_cf = ebitda - tax
    assert math.isclose(flows[4], expected_cf, rel_tol=1e-9)


def test_calculate_labor_cost_parity_floor():
    # Configure non-default to ensure difference is visible
    lab = LaborConfig(min_fte=5, fte_per_tpa=0.5)
    # Parity mode uses max(15, TPA)
    cost_parity, ftes_parity = calculate_labor_cost(lab, target_tpa=10, parity_mode=True)
    # Non-parity mode uses min_fte + (tp - 10)*fte_per_tpa
    cost_nonpar, ftes_nonpar = calculate_labor_cost(lab, target_tpa=10, parity_mode=False)

    assert ftes_parity >= 15
    assert ftes_nonpar <= ftes_parity
    assert cost_parity >= cost_nonpar

