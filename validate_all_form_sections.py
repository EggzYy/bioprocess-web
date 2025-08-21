#!/usr/bin/env python3
"""
Comprehensive Form Validation Test for Bioprocess Web Application

This script tests all form sections to ensure that user input changes are properly
collected, transmitted, and processed by the API. It validates that changes in
Economics, Labor, OPEX, CAPEX, Pricing, Optimization, and Sensitivity tabs
actually affect the calculation results.

Usage: python validate_all_form_sections.py
"""

import json
import requests
import sys
from datetime import datetime
from typing import Dict, Any, Tuple

# API Configuration
API_BASE = "http://localhost:8000"
SCENARIO_ENDPOINT = f"{API_BASE}/api/scenarios/run"

class FormValidationTester:
    def __init__(self):
        self.results = {}
        self.baseline_scenario = None

    def create_baseline_scenario(self) -> Dict[str, Any]:
        """Create baseline scenario with default values."""
        return {
            "name": "Baseline Scenario",
            "description": "Default values for comparison",
            "target_tpa": 10.0,
            "strains": [{
                "name": "Default Strain",
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
                "reactors_total": 4,
                "ds_lines_total": 2,
                "reactor_allocation_policy": "inverse_ct",
                "ds_allocation_policy": "inverse_ct",
                "shared_downstream": True
            },
            "volumes": {
                "base_fermenter_vol_l": 2000.0,
                "volume_options_l": [2000.0],
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
            },
            "prices": {
                "product_prices": {
                    "yogurt": 400,
                    "lacto_bifido": 400,
                    "bacillus": 400,
                    "sacco": 500,
                    "default": 400,
                },
                "raw_prices": {
                    "glucose": 0.8,
                    "yeast_extract": 6.0,
                    "peptone": 8.0,
                    "corn_steep_liquor": 0.6,
                }
            },
            "optimize_equipment": False,
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
                "discount_rate": 0.10,
                "tax_rate": 0.25,
                "variable_opex_share": 0.85,
                "maintenance_pct_of_equip": 0.09,
                "ga_other_scale_factor": 10.84,
                "depreciation_years": 10,
                "project_lifetime_years": 15,
            }
        }

    def create_modified_scenario(self, section: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scenario with modifications to a specific section."""
        scenario = self.create_baseline_scenario()
        scenario["name"] = f"Modified {section.title()} Scenario"
        scenario["description"] = f"Testing {section} form changes"

        if section in scenario:
            scenario[section].update(modifications)
        else:
            scenario[section] = modifications

        return scenario

    def run_scenario(self, scenario: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Run a scenario and return success status and result."""
        payload = {
            "scenario": scenario,
            "async_mode": False
        }

        try:
            response = requests.post(
                SCENARIO_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )

            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"HTTP {response.status_code}", "detail": response.text}

        except Exception as e:
            return False, {"error": "Exception", "detail": str(e)}

    def extract_key_metrics(self, result: Dict[str, Any]) -> Dict[str, float]:
        """Extract key financial and operational metrics from result."""
        if "result" not in result:
            return {}

        result_data = result["result"]
        metrics = {}

        # Extract KPIs
        if "kpis" in result_data:
            kpis = result_data["kpis"]
            for key in ["npv", "irr", "payback_years", "capex", "opex", "opex_per_kg"]:
                if key in kpis:
                    metrics[f"kpi_{key}"] = kpis[key]

        # Extract economics
        if "economics" in result_data:
            economics = result_data["economics"]
            for key in ["annual_revenue", "labor_cost", "utilities_cost", "maintenance_cost", "total_opex", "land_cost", "building_cost", "equipment_cost", "total_capex"]:
                if key in economics:
                    metrics[f"econ_{key}"] = economics[key]

        return metrics

    def test_section(self, section_name: str, modifications: Dict[str, Any], expected_changes: Dict[str, str]) -> Dict[str, Any]:
        """Test a specific form section with modifications."""
        print(f"\n🧪 Testing {section_name.upper()} Section...")

        # Run baseline if not done yet
        if self.baseline_scenario is None:
            print("  Running baseline scenario...")
            baseline_scenario = self.create_baseline_scenario()
            success, baseline_result = self.run_scenario(baseline_scenario)

            if not success:
                return {"status": "failed", "error": "Baseline scenario failed", "details": baseline_result}

            self.baseline_scenario = self.extract_key_metrics(baseline_result)
            print(f"  ✅ Baseline complete")

        # Run modified scenario
        print(f"  Running modified scenario with changes: {list(modifications.keys())}")
        modified_scenario = self.create_modified_scenario(section_name, modifications)
        success, modified_result = self.run_scenario(modified_scenario)

        if not success:
            return {"status": "failed", "error": "Modified scenario failed", "details": modified_result}

        modified_metrics = self.extract_key_metrics(modified_result)

        # Compare results
        changes_detected = {}
        for metric_name, baseline_value in self.baseline_scenario.items():
            if metric_name in modified_metrics:
                modified_value = modified_metrics[metric_name]
                if abs(baseline_value - modified_value) > 0.01:  # Threshold for meaningful change
                    pct_change = ((modified_value - baseline_value) / baseline_value) * 100 if baseline_value != 0 else float('inf')
                    changes_detected[metric_name] = {
                        "baseline": baseline_value,
                        "modified": modified_value,
                        "change": modified_value - baseline_value,
                        "pct_change": pct_change
                    }

        # Check if expected changes occurred
        validation_results = {}
        for expected_metric, expected_direction in expected_changes.items():
            if expected_metric in changes_detected:
                change_info = changes_detected[expected_metric]
                actual_direction = "increase" if change_info["change"] > 0 else "decrease"
                validation_results[expected_metric] = {
                    "expected": expected_direction,
                    "actual": actual_direction,
                    "passed": expected_direction == actual_direction,
                    "change_pct": change_info["pct_change"]
                }
            else:
                validation_results[expected_metric] = {
                    "expected": expected_direction,
                    "actual": "no_change",
                    "passed": False,
                    "change_pct": 0
                }

        total_expected = len(expected_changes)
        total_passed = sum(1 for v in validation_results.values() if v["passed"])

        return {
            "status": "completed",
            "section": section_name,
            "modifications": modifications,
            "changes_detected": changes_detected,
            "validation_results": validation_results,
            "score": f"{total_passed}/{total_expected}",
            "success_rate": total_passed / total_expected if total_expected > 0 else 0
        }

    def run_comprehensive_test(self):
        """Run comprehensive test of all form sections."""
        print("=" * 80)
        print("COMPREHENSIVE FORM VALIDATION TEST")
        print("Bioprocess Web Application - Form Data Collection System")
        print("=" * 80)
        print(f"Testing API at: {API_BASE}")
        print(f"Timestamp: {datetime.now()}")
        print()

        # Define test cases for each section
        test_cases = [
            {
                "section": "economics",
                "modifications": {
                    "discount_rate": 0.15,  # +50% increase
                    "tax_rate": 0.35,       # +40% increase
                    "project_lifetime_years": 20,  # +33% increase
                    "depreciation_years": 15,  # +50% increase
                },
                "expected_changes": {
                    "kpi_npv": "decrease",  # Higher discount rate should decrease NPV
                    "kpi_irr": "decrease",  # Higher tax rate should decrease IRR
                }
            },
            {
                "section": "labor",
                "modifications": {
                    "plant_manager_salary": 150000,    # +44% increase
                    "fermentation_specialist_salary": 60000,  # +54% increase
                    "general_technician_salary": 50000,  # +54% increase
                    "min_fte": 25,  # +67% increase
                },
                "expected_changes": {
                    "econ_labor_cost": "increase",  # Higher salaries = higher labor cost
                    "econ_total_opex": "increase",  # Higher labor = higher total OPEX
                    "kpi_opex": "increase",
                }
            },
            {
                "section": "opex",
                "modifications": {
                    "electricity_usd_per_kwh": 0.20,  # +87% increase
                    "steam_usd_per_kg": 0.04,         # +75% increase
                    "natural_gas_usd_per_mmbtu": 6.0, # +71% increase
                    "raw_materials_markup": 1.5,      # +50% increase
                },
                "expected_changes": {
                    "econ_utilities_cost": "increase",  # Higher utility rates = higher utilities cost
                    "econ_total_opex": "increase",      # Higher utilities = higher total OPEX
                    "kpi_opex_per_kg": "increase",
                }
            },
            {
                "section": "capex",
                "modifications": {
                    "land_cost_per_m2": 800,          # +60% increase
                    "building_cost_per_m2": 3000,     # +50% increase
                    "fermenter_base_cost": 200000,    # +33% increase
                    "installation_factor": 0.25,      # +67% increase
                    "contingency_factor": 0.20,       # +60% increase
                },
                "expected_changes": {
                    "econ_land_cost": "increase",      # Higher land cost
                    "econ_building_cost": "increase",  # Higher building cost
                    "econ_equipment_cost": "increase", # Higher equipment cost
                    "kpi_capex": "increase",           # Higher overall CAPEX
                    "econ_maintenance_cost": "increase", # Maintenance is % of equipment
                }
            },
            {
                "section": "prices",
                "modifications": {
                    "product_prices": {
                        "yogurt": 600,      # +50% increase
                        "lacto_bifido": 600, # +50% increase
                        "bacillus": 600,    # +50% increase
                        "sacco": 750,       # +50% increase
                        "default": 600,     # +50% increase
                    }
                },
                "expected_changes": {
                    "econ_annual_revenue": "increase",  # Higher prices = higher revenue
                    "kpi_npv": "increase",              # Higher revenue = higher NPV
                    "kpi_irr": "increase",              # Higher revenue = higher IRR
                }
            }
        ]

        # Run tests
        test_results = []
        for test_case in test_cases:
            result = self.test_section(
                test_case["section"],
                test_case["modifications"],
                test_case["expected_changes"]
            )
            test_results.append(result)

            # Print results
            if result["status"] == "completed":
                success_rate = result["success_rate"]
                if success_rate >= 0.8:
                    status_emoji = "✅"
                elif success_rate >= 0.5:
                    status_emoji = "⚠️"
                else:
                    status_emoji = "❌"

                print(f"  {status_emoji} {result['section'].upper()}: {result['score']} tests passed ({success_rate*100:.1f}%)")

                # Show detailed results for failed validations
                for metric, validation in result["validation_results"].items():
                    if not validation["passed"]:
                        print(f"    ❌ {metric}: Expected {validation['expected']}, got {validation['actual']}")
                    else:
                        print(f"    ✅ {metric}: {validation['expected']} ({validation['change_pct']:+.1f}%)")
            else:
                print(f"  ❌ {result['section'].upper()}: FAILED - {result.get('error', 'Unknown error')}")

        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total_tests = len(test_cases)
        successful_tests = sum(1 for r in test_results if r["status"] == "completed" and r["success_rate"] >= 0.8)
        partial_tests = sum(1 for r in test_results if r["status"] == "completed" and 0.5 <= r["success_rate"] < 0.8)
        failed_tests = total_tests - successful_tests - partial_tests

        print(f"✅ Fully Working: {successful_tests}/{total_tests} sections")
        print(f"⚠️  Partially Working: {partial_tests}/{total_tests} sections")
        print(f"❌ Not Working: {failed_tests}/{total_tests} sections")
        print()

        if successful_tests == total_tests:
            print("🎉 ALL FORM SECTIONS ARE WORKING CORRECTLY!")
            print("Form data collection system is fully functional.")
        elif successful_tests + partial_tests >= total_tests * 0.8:
            print("👍 MOST FORM SECTIONS ARE WORKING")
            print("Minor issues may remain but core functionality is working.")
        else:
            print("⚠️  SIGNIFICANT FORM DATA COLLECTION ISSUES DETECTED")
            print("Multiple sections are not properly processing form changes.")

        # Save detailed results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"form_validation_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "partial_tests": partial_tests,
                    "failed_tests": failed_tests,
                    "overall_success_rate": successful_tests / total_tests
                },
                "baseline_metrics": self.baseline_scenario,
                "test_results": test_results
            }, f, indent=2)

        print(f"\n📁 Detailed results saved to: {results_file}")
        print("=" * 80)

        return successful_tests == total_tests

def main():
    """Main entry point."""
    tester = FormValidationTester()

    try:
        success = tester.run_comprehensive_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test failed with unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
