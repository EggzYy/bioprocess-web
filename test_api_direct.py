#!/usr/bin/env python3
"""
Test API directly to diagnose production overestimation issue.
Tests both with and without optimization.
"""

import requests

BASE_URL = "http://localhost:8000"


def test_scenario_no_optimization():
    """Test scenario without optimization - should match Python calculations"""

    scenario = {
        "name": "Test Yogurt Cultures No Opt",
        "target_tpa": 10,
        "strains": [
            {
                "name": "S. thermophilus",
                "fermentation_time_h": 17.0,
                "turnaround_time_h": 10.0,
                "downstream_time_h": 8.0,
                "yield_g_per_L": 3.0,
                "media_cost_usd": 600.0,
                "cryo_cost_usd": 50.0,
                "utility_rate_ferm_kw": 300,
                "utility_rate_cent_kw": 15,
                "utility_rate_lyo_kw": 1.5,
                "utility_cost_steam": 0.0228,
                "licensing_fixed_cost_usd": 0.0,
                "licensing_royalty_pct": 0.0,
                "cv_ferm": 0.1,
                "cv_turn": 0.1,
                "cv_down": 0.1,
            },
            {
                "name": "L. bulgaricus",
                "fermentation_time_h": 14.0,
                "turnaround_time_h": 9.0,
                "downstream_time_h": 9.0,
                "yield_g_per_L": 3.0,
                "media_cost_usd": 600.0,
                "cryo_cost_usd": 50.0,
                "utility_rate_ferm_kw": 300,
                "utility_rate_cent_kw": 15,
                "utility_rate_lyo_kw": 1.5,
                "utility_cost_steam": 0.0228,
                "licensing_fixed_cost_usd": 0.0,
                "licensing_royalty_pct": 0.0,
                "cv_ferm": 0.1,
                "cv_turn": 0.1,
                "cv_down": 0.1,
            },
        ],
        "optimize_equipment": False,
        "volumes": {
            "base_fermenter_vol_l": 500,
            "working_volume_fraction": 0.8,
            "volume_options_l": [500],
        },
        "equipment": {
            "reactors_total": 3,
            "ds_lines_total": 1,
            "reactor_allocation_policy": "inverse_ct",
            "ds_allocation_policy": "inverse_ct",
        },
        "optimization": {
            "simulation_type": "deterministic",
            "n_monte_carlo_samples": 1000,
            "confidence_level": 0.95,
        },
        "prices": {
            "product_prices": {
                "S. thermophilus": 6000,
                "L. bulgaricus": 6000,
                "default": 400,
            },
            "raw_prices": {},
        },
        "assumptions": {
            "discount_rate": 0.12,
            "tax_rate": 0.21,
            "project_lifetime_years": 10,
            "electricity_cost_kwh": 0.07,
        },
        "labor": {
            "operators_per_shift": 4,
            "shifts_per_day": 3,
            "operator_annual_salary": 52000,
            "supervisors": 2,
            "supervisor_annual_salary": 95000,
            "qc_staff": 2,
            "qc_annual_salary": 62000,
            "maintenance_staff": 2,
            "maintenance_annual_salary": 55000,
        },
        "capex": {
            "contingency_factor": 0.3,
            "working_capital_factor": 0.15,
            "land_cost_per_sqm": 100,
            "building_cost_per_sqm": 2000,
            "installation_factor": 0.15,
        },
        "opex": {
            "maintenance_rate": 0.04,
            "insurance_rate": 0.01,
            "ga_overhead_rate": 0.15,
        },
        "sensitivity": {"enabled": False, "parameters": [], "delta_percentage": 0.2},
    }

    # Test without optimization
    payload = {"scenario": scenario, "async_mode": False}

    print("=" * 80)
    print("Testing scenario WITHOUT optimization")
    print("Expected: ~11.4 TPA (from cross_validation_proper.py)")
    print("Configuration: 500L, 3 reactors, 1 DS line")
    print("=" * 80)

    response = requests.post(f"{BASE_URL}/api/scenarios/run", json=payload)

    if response.status_code == 200:
        result = response.json()
        production_tpa = result.get("kpis", {}).get("tpa", 0)
        target_tpa = result.get("kpis", {}).get("target_tpa", 10)

        print("✓ API call successful")
        print(f"Production: {production_tpa:.1f} TPA")
        print(f"Target: {target_tpa} TPA")

        if production_tpa > target_tpa * 1.5:
            print(
                f"❌ PROBLEM: Production is {production_tpa / target_tpa:.1f}x the target!"
            )
        elif production_tpa > target_tpa * 1.2:
            print(
                f"⚠ WARNING: Production is {production_tpa / target_tpa:.1f}x the target"
            )
        else:
            print(
                f"✓ Production is reasonable ({production_tpa / target_tpa:.1f}x target)"
            )

        # Show capacity details
        capacity = result.get("capacity", {})
        print("\nCapacity details:")
        print(f"  Total annual kg: {capacity.get('total_annual_kg', 0):.0f}")
        print(f"  Total good batches: {capacity.get('total_good_batches', 0):.0f}")
        print(f"  UP utilization: {capacity.get('weighted_up_utilization', 0):.1%}")
        print(f"  DS utilization: {capacity.get('weighted_ds_utilization', 0):.1%}")

        # Show per-strain details
        per_strain = capacity.get("per_strain", [])
        if per_strain:
            print("\nPer-strain production:")
            for strain in per_strain:
                print(
                    f"  {strain.get('name', 'Unknown')}: {strain.get('annual_kg', 0):.0f} kg/year"
                )

    else:
        print(f"❌ API call failed: {response.status_code}")
        print(response.text)

    return result if response.status_code == 200 else None


def test_scenario_with_optimization():
    """Test scenario with optimization - should find config that meets TPA"""

    scenario = {
        "name": "Test Yogurt Cultures With Opt",
        "target_tpa": 10,
        "strains": [
            {
                "name": "S. thermophilus",
                "fermentation_time_h": 17.0,
                "turnaround_time_h": 10.0,
                "downstream_time_h": 8.0,
                "yield_g_per_L": 3.0,
                "media_cost_usd": 600.0,
                "cryo_cost_usd": 50.0,
                "utility_rate_ferm_kw": 300,
                "utility_rate_cent_kw": 15,
                "utility_rate_lyo_kw": 1.5,
                "utility_cost_steam": 0.0228,
                "licensing_fixed_cost_usd": 0.0,
                "licensing_royalty_pct": 0.0,
                "cv_ferm": 0.1,
                "cv_turn": 0.1,
                "cv_down": 0.1,
            },
            {
                "name": "L. bulgaricus",
                "fermentation_time_h": 14.0,
                "turnaround_time_h": 9.0,
                "downstream_time_h": 9.0,
                "yield_g_per_L": 3.0,
                "media_cost_usd": 600.0,
                "cryo_cost_usd": 50.0,
                "utility_rate_ferm_kw": 300,
                "utility_rate_cent_kw": 15,
                "utility_rate_lyo_kw": 1.5,
                "utility_cost_steam": 0.0228,
                "licensing_fixed_cost_usd": 0.0,
                "licensing_royalty_pct": 0.0,
                "cv_ferm": 0.1,
                "cv_turn": 0.1,
                "cv_down": 0.1,
            },
        ],
        "optimize_equipment": True,
        "use_multiobjective": True,
        "max_reactors": 10,
        "max_ds_lines": 3,
        "volumes": {
            "base_fermenter_vol_l": 500,
            "working_volume_fraction": 0.8,
            "volume_options_l": [500, 1000, 1500, 2000, 3000, 4000, 5000],
        },
        "equipment": {
            "reactors_total": 4,
            "ds_lines_total": 2,
            "reactor_allocation_policy": "inverse_ct",
            "ds_allocation_policy": "inverse_ct",
        },
        "optimization": {
            "simulation_type": "deterministic",
            "n_monte_carlo_samples": 1000,
            "confidence_level": 0.95,
        },
        "prices": {
            "product_prices": {"S. thermophilus": 6000, "L. bulgaricus": 6000},
            "raw_prices": {},
        },
        "assumptions": {
            "discount_rate": 0.12,
            "tax_rate": 0.21,
            "project_lifetime_years": 10,
            "electricity_cost_kwh": 0.07,
        },
        "labor": {
            "operators_per_shift": 4,
            "shifts_per_day": 3,
            "operator_annual_salary": 52000,
            "supervisors": 2,
            "supervisor_annual_salary": 95000,
            "qc_staff": 2,
            "qc_annual_salary": 62000,
            "maintenance_staff": 2,
            "maintenance_annual_salary": 55000,
        },
        "capex": {
            "contingency_factor": 0.3,
            "working_capital_factor": 0.15,
            "land_cost_per_sqm": 100,
            "building_cost_per_sqm": 2000,
            "installation_factor": 0.15,
        },
        "opex": {
            "maintenance_rate": 0.04,
            "insurance_rate": 0.01,
            "ga_overhead_rate": 0.15,
        },
        "sensitivity": {"enabled": False, "parameters": [], "delta_percentage": 0.2},
    }

    # Test with optimization
    payload = {"scenario": scenario, "async_mode": False}

    print("\n" + "=" * 80)
    print("Testing scenario WITH optimization")
    print("Expected: ~11.4 TPA (from cross_validation_proper.py)")
    print(f"Volume options: {scenario['volumes']['volume_options_l']}")
    print("=" * 80)

    response = requests.post(f"{BASE_URL}/api/scenarios/run", json=payload)

    if response.status_code == 200:
        result = response.json()
        production_tpa = result.get("kpis", {}).get("tpa", 0)
        target_tpa = result.get("kpis", {}).get("target_tpa", 10)

        print("✓ API call successful")
        print(f"Production: {production_tpa:.1f} TPA")
        print(f"Target: {target_tpa} TPA")

        if production_tpa > target_tpa * 1.5:
            print(
                f"❌ PROBLEM: Production is {production_tpa / target_tpa:.1f}x the target!"
            )
        elif production_tpa > target_tpa * 1.2:
            print(
                f"⚠ WARNING: Production is {production_tpa / target_tpa:.1f}x the target"
            )
        else:
            print(
                f"✓ Production is reasonable ({production_tpa / target_tpa:.1f}x target)"
            )

        # Show optimization result
        optimization = result.get("optimization", {})
        if optimization:
            print("\nOptimized configuration:")
            print(
                f"  Fermenter volume: {optimization.get('selected_fermenter_volume', 0)} L"
            )
            print(f"  Reactors: {optimization.get('selected_reactors', 0)}")
            print(f"  DS lines: {optimization.get('selected_ds_lines', 0)}")

            best_solution = optimization.get("best_solution", {})
            if best_solution:
                print(f"  CAPEX: ${best_solution.get('capex', 0):,.0f}")
                print(f"  IRR: {best_solution.get('irr', 0):.1%}")

    else:
        print(f"❌ API call failed: {response.status_code}")
        print(response.text)

    return result if response.status_code == 200 else None


if __name__ == "__main__":
    # Kill any existing server and restart
    print("Stopping existing API server...")
    import subprocess

    subprocess.run(["pkill", "-f", "uvicorn.*main:app"], stderr=subprocess.DEVNULL)
    import time

    time.sleep(2)

    print("Starting fresh API server...")
    import os

    os.chdir("/home/eggzy/Downloads/Project_Hasan/bioprocess-web")
    server_process = subprocess.Popen(
        ["uvicorn", "api.main:app", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(5)  # Wait for server to start

    try:
        # Test without optimization first
        result_no_opt = test_scenario_no_optimization()

        # Test with optimization
        result_with_opt = test_scenario_with_optimization()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if result_no_opt:
            no_opt_tpa = result_no_opt.get("kpis", {}).get("tpa", 0)
            print(f"Without optimization: {no_opt_tpa:.1f} TPA")
            if no_opt_tpa > 15:
                print("  ❌ Excessive production")

        if result_with_opt:
            with_opt_tpa = result_with_opt.get("kpis", {}).get("tpa", 0)
            print(f"With optimization: {with_opt_tpa:.1f} TPA")
            if with_opt_tpa > 15:
                print("  ❌ Excessive production")

    finally:
        # Kill the server
        print("\nStopping API server...")
        server_process.terminate()
        server_process.wait()
