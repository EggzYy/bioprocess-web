#!/usr/bin/env python3
"""
Debug Optimization Evaluations
Direct API test to investigate why optimization is only reporting 1 evaluation
when it should be doing many more in grid search mode.
"""

import json
import requests
import time
from datetime import datetime

# API Configuration
API_BASE = "http://localhost:8000"
OPTIMIZATION_ENDPOINT = f"{API_BASE}/api/optimization/run"
SCENARIO_ENDPOINT = f"{API_BASE}/api/scenarios/run"

def create_test_scenario_for_optimization():
    """Create a scenario optimized for testing optimization evaluation counts."""
    return {
        "name": "Optimization Debug Test",
        "description": "Testing optimization evaluation counts",
        "target_tpa": 15.0,
        "strains": [{
            "name": "Debug Strain",
            "fermentation_time_h": 18.0,
            "turnaround_time_h": 9.0,
            "downstream_time_h": 4.0,
            "yield_g_per_L": 82.87,
            "media_cost_usd": 245.0,
            "cryo_cost_usd": 189.0,
            "utility_rate_ferm_kw": 324.0,
            "utility_rate_cent_kw": 15.0,
            "utility_rate_lyo_kw": 1.5,
            "utility_cost_steam": 0.0228,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
        }],
        "equipment": {
            "reactors_total": 6,    # Should explore 1-5 reactors (5 options)
            "ds_lines_total": 3,    # Should explore 1-3 DS lines (3 options)
            "reactor_allocation_policy": "inverse_ct",
            "ds_allocation_policy": "inverse_ct",
            "shared_downstream": True
        },
        "volumes": {
            "base_fermenter_vol_l": 2000.0,
            "volume_options_l": [1500.0, 2000.0, 2500.0],  # 3 volume options
            # Expected evaluations: 3 volumes × 5 reactors × 3 DS lines = 45 evaluations
            "working_volume_fraction": 0.8,
            "seed_fermenter_ratio": 0.125,
            "media_tank_ratio": 1.25,
        },
        "economics": {
            "discount_rate": 0.10,
            "tax_rate": 0.25,
            "depreciation_years": 10,
            "project_lifetime_years": 15,
            "variable_opex_share": 0.85,
            "maintenance_pct_of_equip": 0.09,
            "ga_other_scale_factor": 10.84,
        },
        "labor": {
            "plant_manager_salary": 104000,
            "fermentation_specialist_salary": 39000,
            "downstream_process_operator_salary": 52000,
            "general_technician_salary": 32500,
            "qaqc_lab_tech_salary": 39000,
            "maintenance_tech_salary": 39000,
            "utility_operator_salary": 39000,
            "logistics_clerk_salary": 39000,
            "office_clerk_salary": 32500,
            "min_fte": 15,
            "fte_per_tpa": 1.0,
        },
        "opex": {
            "electricity_usd_per_kwh": 0.107,
            "steam_usd_per_kg": 0.0228,
            "water_usd_per_m3": 0.002,
            "natural_gas_usd_per_mmbtu": 3.50,
            "raw_materials_markup": 1.0,
            "utilities_efficiency": 0.85,
        },
        "capex": {
            "land_cost_per_m2": 500,
            "building_cost_per_m2": 2000,
            "fermenter_base_cost": 150000,
            "fermenter_scale_exponent": 0.6,
            "centrifuge_cost": 200000,
            "tff_skid_cost": 150000,
            "lyophilizer_cost_per_m2": 50000,
            "utilities_cost_factor": 0.25,
            "installation_factor": 0.15,
            "contingency_factor": 0.125,
            "working_capital_months": 3,
            "parity_mode": False,
        },
        "prices": {
            "product_prices": {
                "default": 400,
            },
            "raw_prices": {
                "glucose": 0.8,
                "yeast_extract": 6.0,
                "peptone": 8.0,
                "corn_steep_liquor": 0.6,
            }
        },
        "optimize_equipment": True,
        "use_multiobjective": False,
        "optimization": {
            "enabled": True,
            "simulation_type": "deterministic",
            "objectives": ["npv"],
            "min_tpa": 5.0,
            "max_capex_usd": 50000000,
            "min_utilization": 0.50,
            "max_payback": 10.0,
            "max_evaluations": 1000,  # High limit to ensure grid search completes
            "population_size": 100,
            "n_generations": 50,
            "n_monte_carlo_samples": 100,
            "confidence_level": 0.95,
        },
        "sensitivity": {
            "enabled": False,
            "parameters": [],
            "delta_percentage": 0.1,
            "grid_points": 5,
            "n_samples": 1000,
        },
        "assumptions": {
            "hours_per_year": 8760.0,
            "upstream_availability": 0.92,
            "downstream_availability": 0.90,
            "quality_yield": 0.98,
            "discount_rate": 0.10,
            "tax_rate": 0.25,
            "variable_opex_share": 0.85,
            "maintenance_pct_of_equip": 0.09,
            "ga_other_scale_factor": 10.84,
            "depreciation_years": 10,
            "project_lifetime_years": 15,
        }
    }

def test_optimization_api_direct():
    """Test optimization API directly to debug evaluation counts."""
    print("=" * 80)
    print("OPTIMIZATION EVALUATION COUNT DEBUG TEST")
    print("=" * 80)
    print(f"Testing API at: {API_BASE}")
    print(f"Timestamp: {datetime.now()}")
    print()

    scenario = create_test_scenario_for_optimization()

    # Calculate expected evaluations
    volume_count = len(scenario["volumes"]["volume_options_l"])
    max_reactors = scenario["equipment"]["reactors_total"]
    max_ds_lines = scenario["equipment"]["ds_lines_total"]
    expected_evaluations = volume_count * (max_reactors - 1) * max_ds_lines

    print(f"📊 Expected Grid Search Calculations:")
    print(f"   Volume options: {volume_count} ({scenario['volumes']['volume_options_l']})")
    print(f"   Reactor range: 1 to {max_reactors-1} ({max_reactors-1} options)")
    print(f"   DS line range: 1 to {max_ds_lines} ({max_ds_lines} options)")
    print(f"   Expected evaluations: {volume_count} × {max_reactors-1} × {max_ds_lines} = {expected_evaluations}")
    print()

    # Test 1: Direct optimization API call
    print("🧪 Test 1: Direct Optimization API Call")
    optimization_payload = {
        "scenario": scenario,
        "max_reactors": max_reactors * 2,  # Give it plenty of room
        "max_ds_lines": max_ds_lines * 2,
        "objectives": ["npv", "irr"]
    }

    try:
        print("   📡 Sending optimization request...")
        start_time = time.time()

        response = requests.post(
            OPTIMIZATION_ENDPOINT,
            json=optimization_payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        end_time = time.time()
        duration = end_time - start_time

        print(f"   ⏱️  Request completed in {duration:.2f} seconds")
        print(f"   📈 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("   ✅ Optimization API call successful!")

            # Examine the response structure
            print("\n   🔍 Response Structure Analysis:")
            if "result" in result:
                optimization_result = result["result"]

                # Look for evaluation count indicators
                evaluation_indicators = [
                    "evaluations_completed", "total_evaluations", "evaluation_count",
                    "iterations", "generations", "function_calls"
                ]

                for indicator in evaluation_indicators:
                    if indicator in optimization_result:
                        print(f"      {indicator}: {optimization_result[indicator]}")

                # Check optimization section
                if "optimization" in optimization_result:
                    opt_section = optimization_result["optimization"]
                    print(f"      optimization section keys: {list(opt_section.keys()) if isinstance(opt_section, dict) else 'Not a dict'}")

                    if isinstance(opt_section, dict):
                        for key, value in opt_section.items():
                            if "eval" in key.lower() or "count" in key.lower() or "total" in key.lower():
                                print(f"      optimization.{key}: {value}")

                # Check if there's a pareto front or solution list
                if "pareto_front" in optimization_result:
                    pareto_size = len(optimization_result["pareto_front"])
                    print(f"      pareto_front size: {pareto_size}")

                if "all_solutions" in optimization_result:
                    solutions_count = len(optimization_result["all_solutions"])
                    print(f"      all_solutions count: {solutions_count}")

                # Look for best solution
                if "best_solution" in optimization_result:
                    best = optimization_result["best_solution"]
                    print(f"      best_solution NPV: ${best.get('npv', 'N/A'):,.0f}" if isinstance(best, dict) else "N/A")
                    print(f"      best_solution config: {best.get('reactors', 'N/A')} reactors, {best.get('ds_lines', 'N/A')} DS lines, {best.get('fermenter_volume_l', 'N/A')}L")

            # Save detailed result
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = f"optimization_debug_result_{timestamp}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n   📁 Full result saved to: {result_file}")

        else:
            print(f"   ❌ Optimization API call failed!")
            try:
                error_detail = response.json()
                print(f"      Error: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"      Raw error: {response.text}")

    except requests.exceptions.Timeout:
        print("   ⏱️  Optimization request timed out (>120 seconds)")
    except Exception as e:
        print(f"   ❌ Optimization request failed: {str(e)}")

    print()

    # Test 2: Scenario with optimization enabled
    print("🧪 Test 2: Scenario API Call with Optimization Enabled")
    scenario_payload = {
        "scenario": scenario,
        "async_mode": False
    }

    try:
        print("   📡 Sending scenario request with optimization...")
        start_time = time.time()

        response = requests.post(
            SCENARIO_ENDPOINT,
            json=scenario_payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        end_time = time.time()
        duration = end_time - start_time

        print(f"   ⏱️  Request completed in {duration:.2f} seconds")
        print(f"   📈 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("   ✅ Scenario API call successful!")

            if "result" in result:
                scenario_result = result["result"]

                # Check for optimization results in scenario response
                if "optimization" in scenario_result:
                    opt_data = scenario_result["optimization"]
                    print(f"   🔍 Optimization data found in scenario result")
                    print(f"      Keys: {list(opt_data.keys()) if isinstance(opt_data, dict) else 'Not a dict'}")

                    if isinstance(opt_data, dict):
                        # Look for evaluation counts
                        for key, value in opt_data.items():
                            if any(keyword in key.lower() for keyword in ["eval", "count", "total", "iter"]):
                                print(f"      {key}: {value}")
                else:
                    print("   ⚠️  No optimization section found in scenario result")

                # Check KPIs
                if "kpis" in scenario_result:
                    kpis = scenario_result["kpis"]
                    print(f"   💰 NPV: ${kpis.get('npv', 'N/A'):,.0f}")
                    print(f"   📊 IRR: {kpis.get('irr', 'N/A'):.1%}" if kpis.get('irr') else "   📊 IRR: N/A")

            # Save detailed result
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = f"scenario_debug_result_{timestamp}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"   📁 Full result saved to: {result_file}")

        else:
            print(f"   ❌ Scenario API call failed!")
            try:
                error_detail = response.json()
                print(f"      Error: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"      Raw error: {response.text}")

    except requests.exceptions.Timeout:
        print("   ⏱️  Scenario request timed out (>120 seconds)")
    except Exception as e:
        print(f"   ❌ Scenario request failed: {str(e)}")

    print("\n" + "=" * 80)
    print("DEBUG TEST SUMMARY")
    print("=" * 80)
    print("This test examined the optimization API responses to understand")
    print("why evaluation counts are showing as 1 instead of the expected")
    print(f"grid search count of {expected_evaluations} evaluations.")
    print()
    print("Check the saved JSON files for detailed API response analysis.")
    print("=" * 80)

if __name__ == "__main__":
    try:
        test_optimization_api_direct()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
