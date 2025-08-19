#!/usr/bin/env python3
"""
Test script to verify bioprocess calculation pipeline.
"""

import json
from bioprocess.models import (
    ScenarioInput,
    StrainInput,
    EquipmentConfig,
    VolumePlan,
    CapexConfig,
    OpexConfig,
    LaborConfig,
    PriceTables,
    EconomicAssumptions,
    OptimizationConfig,
    SensitivityConfig,
    SimulationType,
)
from bioprocess.orchestrator import run_scenario


def create_test_scenario():
    """Create a test scenario for yogurt production facility."""

    # Create strain inputs
    strains = [
        StrainInput(
            name="S. thermophilus",
            fermentation_time_h=14.0,
            turnaround_time_h=9.0,
            downstream_time_h=4.0,
            yield_g_per_L=12.56,
            media_cost_usd=100.0,
            cryo_cost_usd=50.0,
            utility_rate_ferm_kw=252,
            utility_rate_cent_kw=15,
            utility_rate_lyo_kw=1.5,
            utility_cost_steam=0.0228,
            licensing_fixed_cost_usd=0.0,
            licensing_royalty_pct=0.0,
            cv_ferm=0.1,
            cv_turn=0.1,
            cv_down=0.1,
        ),
        StrainInput(
            name="L. delbrueckii subsp. bulgaricus",
            fermentation_time_h=24.0,
            turnaround_time_h=9.0,
            downstream_time_h=4.0,
            yield_g_per_L=4.63,
            media_cost_usd=120.0,
            cryo_cost_usd=55.0,
            utility_rate_ferm_kw=432,
            utility_rate_cent_kw=15,
            utility_rate_lyo_kw=1.5,
            utility_cost_steam=0.0228,
            licensing_fixed_cost_usd=0.0,
            licensing_royalty_pct=0.0,
            cv_ferm=0.1,
            cv_turn=0.1,
            cv_down=0.1,
        ),
    ]

    # Create equipment configuration
    equipment = EquipmentConfig(reactors_total=4, ds_lines_total=2)

    # Volume configuration
    volumes = VolumePlan(
        base_fermenter_vol_l=2000,
        volume_options_l=[1000, 2000, 5000],
        seed_fermenter_ratio=0.125,
        media_tank_ratio=1.25,
    )

    # CAPEX configuration
    capex = CapexConfig(
        fermenter_base_cost=150000,
        fermenter_scale_exponent=0.6,
        centrifuge_cost=200000,
        tff_skid_cost=150000,
        lyophilizer_cost_per_m2=50000,
        installation_factor=0.15,
        building_cost_per_m2=2000,
        contingency_factor=0.125,
    )

    # OPEX configuration
    opex = OpexConfig(
        electricity_usd_per_kwh=0.107, steam_usd_per_kg=0.0228, water_usd_per_m3=0.002
    )

    # Labor configuration
    labor = LaborConfig(
        plant_manager_salary=104000,
        fermentation_specialist_salary=39000,
        downstream_process_operator_salary=52000,
        general_technician_salary=32500,
        qaqc_lab_tech_salary=39000,
        maintenance_tech_salary=39000,
        utility_operator_salary=39000,
        logistics_clerk_salary=39000,
        office_clerk_salary=32500,
    )

    # Price specifications
    prices = PriceTables(
        product_prices={
            "yogurt": 400,
            "lacto_bifido": 400,
            "bacillus": 400,
            "sacco": 500,
        },
        raw_prices={"Glucose": 0.22, "Yeast Extract": 1.863, "Soy Peptone": 4.50},
    )

    # Economic assumptions
    assumptions = EconomicAssumptions(
        discount_rate=0.10,
        tax_rate=0.25,
        depreciation_years=10,
        project_lifetime_years=15,
    )

    # Optimization configuration
    optimization = OptimizationConfig(
        enabled=False,
        simulation_type=SimulationType.DETERMINISTIC,
        n_monte_carlo_samples=1000,
    )

    # Sensitivity configuration
    sensitivity = SensitivityConfig(
        enabled=False, parameters=["discount_rate", "tax_rate"], delta_percentage=0.1
    )

    # Create scenario
    scenario = ScenarioInput(
        name="Test Yogurt Facility",
        target_tpa=10.0,
        strains=strains,
        equipment=equipment,
        volumes=volumes,
        capex=capex,
        opex=opex,
        labor=labor,
        prices=prices,
        assumptions=assumptions,
        optimization=optimization,
        sensitivity=sensitivity,
        optimize_equipment=False,
    )

    return scenario


def main():
    """Run test scenario."""
    print("Creating test scenario...")
    scenario = create_test_scenario()

    print(f"Running scenario: {scenario.name}")
    print(f"Target capacity: {scenario.target_tpa} TPA")
    print(f"Strains: {[s.name for s in scenario.strains]}")
    print(
        f"Equipment: {scenario.equipment.reactors_total} reactors, {scenario.equipment.ds_lines_total} DS lines"
    )
    print(f"Fermenter volume: {scenario.volumes.base_fermenter_vol_l} L")
    print()

    try:
        # Run the scenario
        result = run_scenario(scenario)

        # Print results
        print("Results:")
        print("-" * 50)
        print(f"Scenario: {result.scenario_name}")
        print(f"Status: {'SUCCESS' if not result.errors else 'FAILED'}")

        if result.kpis:
            print("\nKey Performance Indicators:")
            print(f"  NPV: ${result.kpis.get('npv', 0):,.0f}")
            print(f"  IRR: {result.kpis.get('irr', 0):.1%}")
            print(f"  Payback: {result.kpis.get('payback_years', 0):.1f} years")
            print(f"  CAPEX: ${result.kpis.get('capex', 0):,.0f}")
            print(f"  OPEX: ${result.kpis.get('opex', 0):,.0f}")
            print(f"  Capacity: {result.kpis.get('tpa', 0):.1f} TPA")
            print(f"  Utilization (UP): {result.kpis.get('up_utilization', 0):.1%}")
            print(f"  Utilization (DS): {result.kpis.get('ds_utilization', 0):.1%}")

        if result.capacity:
            print("\nCapacity Details:")
            print(f"  Total batches: {result.capacity.total_feasible_batches:.0f}")
            print(f"  Good batches: {result.capacity.total_good_batches:.0f}")
            print(f"  Annual production: {result.capacity.total_annual_kg:,.0f} kg")
            print(f"  Bottleneck: {result.capacity.bottleneck}")

        if result.economics:
            print("\nEconomic Summary:")
            print(f"  Annual Revenue: ${result.economics.annual_revenue:,.0f}")
            print(f"  Total OPEX: ${result.economics.total_opex:,.0f}")
            print(f"  Total CAPEX: ${result.economics.total_capex:,.0f}")
            print(f"  EBITDA Margin: {result.economics.ebitda_margin:.1%}")

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")

        print(f"\nCalculation time: {result.calculation_time_s:.2f} seconds")

        # Save results to file
        output_file = "test_scenario_results.json"
        with open(output_file, "w") as f:
            json.dump(result.dict(), f, indent=2, default=str)
        print(f"\nResults saved to: {output_file}")

    except Exception as e:
        print(f"Error running scenario: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
