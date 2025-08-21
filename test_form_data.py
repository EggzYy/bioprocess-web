#!/usr/bin/env python3
"""
Test script to verify form data collection issue in the bioprocess web application.
This script will send test data to the API and verify that form changes are actually processed.
"""

import json
import requests
import sys
from datetime import datetime

# Test API endpoint
API_BASE = "http://localhost:8000"
SCENARIO_ENDPOINT = f"{API_BASE}/api/scenarios/run"

def create_test_scenario_with_modified_values():
    """Create a test scenario with modified values that should be different from defaults."""
    scenario = {
        "name": "Form Data Test Scenario",
        "description": "Testing if form data changes are processed",
        "target_tpa": 15.0,  # Changed from default 10.0
        "strains": [{
            "name": "Test Strain",
            "fermentation_time_h": 20.0,  # Changed from default 18.0
            "turnaround_time_h": 10.0,  # Changed from default 9.0
            "downstream_time_h": 5.0,  # Changed from default 4.0
            "yield_g_per_L": 90.0,  # Changed from default 82.87
            "media_cost_usd": 300.0,  # Changed from default 245
            "cryo_cost_usd": 200.0,  # Changed from default 189
            "utility_rate_ferm_kw": 350.0,  # Changed from default 324
            "utility_rate_cent_kw": 20.0,  # Changed from default 15
            "utility_rate_lyo_kw": 2.0,  # Changed from default 1.5
            "utility_cost_steam": 0.025,  # Changed from default 0.0228
            "cv_ferm": 0.15,  # Changed from default 0.1
            "cv_turn": 0.15,  # Changed from default 0.1
            "cv_down": 0.15,  # Changed from default 0.1
        }],
        "equipment": {
            "reactors_total": 6,  # Changed from default 4
            "ds_lines_total": 3,  # Changed from default 2
            "reactor_allocation_policy": "inverse_ct",
            "ds_allocation_policy": "inverse_ct",
            "shared_downstream": True
        },
        "volumes": {
            "base_fermenter_vol_l": 2500.0,  # Changed from default 2000
            "volume_options_l": [2500.0, 3000.0],  # Changed
            "working_volume_fraction": 0.85,  # Changed from default 0.8
            "seed_fermenter_ratio": 0.15,  # Changed from default 0.125
            "media_tank_ratio": 1.5,  # Changed from default 1.25
        },
        "economics": {
            "discount_rate": 0.12,  # Changed from default 0.10
            "tax_rate": 0.30,  # Changed from default 0.25
            "depreciation_years": 12,  # Changed from default 10
            "project_lifetime_years": 20,  # Changed from default 15
            "variable_opex_share": 0.90,  # Changed from default 0.85
            "maintenance_pct_of_equip": 0.12,  # Changed from default 0.09
            "ga_other_scale_factor": 12.0,  # Changed from default 10.84
        },
        "labor": {
            "plant_manager_salary": 120000,  # Changed from default 104000
            "fermentation_specialist_salary": 45000,  # Changed from default 39000
            "downstream_process_operator_salary": 60000,  # Changed from default 52000
            "general_technician_salary": 40000,  # Changed from default 32500
            "qaqc_lab_tech_salary": 45000,  # Changed from default 39000
            "maintenance_tech_salary": 45000,  # Changed from default 39000
            "utility_operator_salary": 45000,  # Changed from default 39000
            "logistics_clerk_salary": 45000,  # Changed from default 39000
            "office_clerk_salary": 40000,  # Changed from default 32500
            "min_fte": 20,  # Changed from default 15
            "fte_per_tpa": 1.5,  # Changed from default 1.0
        },
        "opex": {
            "electricity_usd_per_kwh": 0.15,  # Changed from default 0.107
            "steam_usd_per_kg": 0.03,  # Changed from default 0.0228
            "water_usd_per_m3": 0.003,  # Changed from default 0.002
            "natural_gas_usd_per_mmbtu": 4.0,  # Changed from default 3.5
            "raw_materials_markup": 1.2,  # Changed from default 1.0
            "utilities_efficiency": 0.90,  # Changed from default 0.85
        },
        "capex": {
            "land_cost_per_m2": 600,  # Changed from default 500
            "building_cost_per_m2": 2500,  # Changed from default 2000
            "fermenter_base_cost": 180000,  # Changed from default 150000
            "fermenter_scale_exponent": 0.65,  # Changed from default 0.6
            "centrifuge_cost": 250000,  # Changed from default 200000
            "tff_skid_cost": 180000,  # Changed from default 150000
            "lyophilizer_cost_per_m2": 60000,  # Changed from default 50000
            "utilities_cost_factor": 0.30,  # Changed from default 0.25
            "installation_factor": 0.20,  # Changed from default 0.15
            "contingency_factor": 0.15,  # Changed from default 0.125
            "working_capital_months": 4,  # Changed from default 3
        },
        "prices": {
            "product_prices": {
                "yogurt": 450,  # Changed from default 400
                "lacto_bifido": 450,  # Changed from default 400
                "bacillus": 450,  # Changed from default 400
                "sacco": 550,  # Changed from default 500
                "default": 450,  # Changed from default 400
            },
            "raw_prices": {
                "glucose": 0.85,  # Will be populated with test values
                "yeast_extract": 6.5,
                "peptone": 8.5,
                "corn_steep_liquor": 0.65,
            }
        },
        "optimize_equipment": False,  # Disable optimization to see direct form effects
        "use_multiobjective": False,
        "optimization": {
            "enabled": False,
            "simulation_type": "deterministic",
            "objectives": [],
            "min_tpa": None,
            "max_capex_usd": None,
            "min_utilization": None,
            "max_payback": None,
            "max_evaluations": 100,
            "population_size": 50,
            "n_generations": 100,
            "n_monte_carlo_samples": 1000,
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
            "discount_rate": 0.12,  # Should match economics
            "tax_rate": 0.30,  # Should match economics
            "variable_opex_share": 0.90,  # Should match economics
            "maintenance_pct_of_equip": 0.12,  # Should match economics
            "ga_other_scale_factor": 12.0,  # Should match economics
            "depreciation_years": 12,  # Should match economics
            "project_lifetime_years": 20,  # Should match economics
        }
    }

    return scenario

def test_form_data_processing():
    """Test if form data changes are actually processed by the API."""
    print("=" * 60)
    print("BIOPROCESS FORM DATA COLLECTION TEST")
    print("=" * 60)
    print(f"Testing API at: {API_BASE}")
    print(f"Timestamp: {datetime.now()}")
    print()

    # Create test scenario with modified values
    test_scenario = create_test_scenario_with_modified_values()

    # Prepare request payload
    payload = {
        "scenario": test_scenario,
        "async_mode": False
    }

    print("Sending test scenario with modified form values...")
    print("Key test values being sent:")
    print(f"  - Target TPA: {test_scenario['target_tpa']} (should be 15.0, not 10.0)")
    print(f"  - Discount Rate: {test_scenario['economics']['discount_rate']} (should be 0.12, not 0.10)")
    print(f"  - Plant Manager Salary: ${test_scenario['labor']['plant_manager_salary']:,} (should be $120,000, not $104,000)")
    print(f"  - Electricity Cost: ${test_scenario['opex']['electricity_usd_per_kwh']}/kWh (should be $0.15, not $0.107)")
    print(f"  - Land Cost: ${test_scenario['capex']['land_cost_per_m2']}/m² (should be $600, not $500)")
    print(f"  - Product Price: ${test_scenario['prices']['product_prices']['default']}/kg (should be $450, not $400)")
    print()

    try:
        # Send request to API
        response = requests.post(
            SCENARIO_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ API request successful!")

            # Check if we got results
            if "result" in result and result["result"]:
                scenario_result = result["result"]
                print("\nAnalyzing results to verify form data was used...")

                # Check some key financial metrics that should be affected by our changes
                if "financial_metrics" in scenario_result:
                    metrics = scenario_result["financial_metrics"]

                    print("\n📊 FINANCIAL METRICS ANALYSIS:")
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            print(f"  - {key}: {value:,.2f}")

                    # The changed parameters should affect these results
                    # If the default values were used instead of our form values,
                    # the results would be different

                else:
                    print("⚠️  No financial_metrics found in result")

                # Check if scenario input was logged/returned (for debugging)
                if "scenario_input" in scenario_result:
                    input_data = scenario_result["scenario_input"]
                    print("\n🔍 VERIFYING SCENARIO INPUT DATA:")

                    # Check key values to see if our form data was used
                    checks = [
                        ("Target TPA", input_data.get("target_tpa"), 15.0),
                        ("Discount Rate", input_data.get("assumptions", {}).get("discount_rate"), 0.12),
                        ("Plant Manager Salary", input_data.get("labor", {}).get("plant_manager_salary"), 120000),
                        ("Electricity Cost", input_data.get("opex", {}).get("electricity_usd_per_kwh"), 0.15),
                        ("Land Cost", input_data.get("capex", {}).get("land_cost_per_m2"), 600),
                    ]

                    for check_name, actual_value, expected_value in checks:
                        if actual_value == expected_value:
                            print(f"  ✅ {check_name}: {actual_value} (CORRECT)")
                        else:
                            print(f"  ❌ {check_name}: {actual_value} (EXPECTED: {expected_value})")

                print(f"\n📁 Full result saved to: form_data_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

                # Save full result for analysis
                with open(f"form_data_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
                    json.dump(result, f, indent=2)

            else:
                print("❌ No result data returned from API")

        else:
            print(f"❌ API request failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Raw error response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Could not connect to the API.")
        print("Make sure the bioprocess web application is running on localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: API request took too long")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_form_data_processing()
    sys.exit(0 if success else 1)
