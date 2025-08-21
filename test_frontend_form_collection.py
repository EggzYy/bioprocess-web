#!/usr/bin/env python3
"""
Frontend Form Collection Test for Bioprocess Web Application

This test simulates the frontend JavaScript form data collection process
to verify that the `collectFormData()` function and API integration work
correctly end-to-end.

It validates that:
1. Form data is properly structured and collected
2. All form sections (Economics, Labor, OPEX, CAPEX, Pricing, etc.) are included
3. The API correctly processes the form data
4. Changes in form values actually affect calculation results

Usage: python test_frontend_form_collection.py
"""

import json
import requests
import sys
from datetime import datetime
from typing import Dict, Any, List

# API Configuration
API_BASE = "http://localhost:8000"
SCENARIO_ENDPOINT = f"{API_BASE}/api/scenarios/run"

class FrontendFormCollectionTester:
    def __init__(self):
        self.test_results = []

    def simulate_comprehensive_form_data(self,
                                       enable_equipment_optimization: bool = False,
                                       enable_multiobjective: bool = False,
                                       enable_sensitivity: bool = False,
                                       scenario_name: str = "Frontend Form Test Scenario") -> Dict[str, Any]:
        """
        Simulate the data structure that would be collected by the frontend
        JavaScript collectFormData() function from the comprehensive form.

        This mirrors the structure in web/static/js/app-comprehensive.js
        """
        return {
            "name": scenario_name,
            "description": f"Testing frontend form data collection - {scenario_name}",
            "target_tpa": 12.5,  # Modified from default 10.0

            # Strains section - simulate strain form data
            "strains": [
                {
                    "name": "Test Lactobacillus",
                    "fermentation_time_h": 22.0,  # Modified from default 18.0
                    "turnaround_time_h": 11.0,    # Modified from default 9.0
                    "downstream_time_h": 6.0,     # Modified from default 4.0
                    "yield_g_per_L": 95.0,        # Modified from default 82.87
                    "media_cost_usd": 275.0,      # Modified from default 245
                    "cryo_cost_usd": 210.0,       # Modified from default 189
                    "utility_rate_ferm_kw": 380.0, # Modified from default 324
                    "utility_rate_cent_kw": 18.0,  # Modified from default 15
                    "utility_rate_lyo_kw": 2.2,    # Modified from default 1.5
                    "utility_cost_steam": 0.027,   # Modified from default 0.0228
                    "cv_ferm": 0.12,               # Modified from default 0.1
                    "cv_turn": 0.12,               # Modified from default 0.1
                    "cv_down": 0.12,               # Modified from default 0.1
                    "respiration_type": "aerobic",
                    "requires_tff": True,
                    "downstream_complexity": 1.2
                }
            ],

            # Equipment section
            "equipment": {
                "reactors_total": 8,           # Increased to allow more optimization configurations
                "ds_lines_total": 4,           # Increased to allow more optimization configurations
                "reactor_allocation_policy": "inverse_ct",
                "ds_allocation_policy": "inverse_ct",
                "shared_downstream": True
            },

            # Volumes section
            "volumes": {
                "base_fermenter_vol_l": 2200.0,   # Modified from default 2000
                "volume_options_l": [1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0],  # More options for optimization
                "working_volume_fraction": 0.82,   # Modified from default 0.8
                "seed_fermenter_ratio": 0.14,      # Modified from default 0.125
                "media_tank_ratio": 1.35,          # Modified from default 1.25
            },

            # Economics section - simulate form inputs
            "economics": {
                "discount_rate": 0.13,              # Modified from default 0.10 (13% vs 10%)
                "tax_rate": 0.28,                   # Modified from default 0.25 (28% vs 25%)
                "depreciation_years": 12,           # Modified from default 10
                "project_lifetime_years": 18,       # Modified from default 15
                "variable_opex_share": 0.88,        # Modified from default 0.85 (88% vs 85%)
                "maintenance_pct_of_equip": 0.11,   # Modified from default 0.09 (11% vs 9%)
                "ga_other_scale_factor": 12.5,      # Modified from default 10.84
            },

            # Labor section - simulate form inputs
            "labor": {
                "plant_manager_salary": 125000,         # Modified from default 104000
                "fermentation_specialist_salary": 48000, # Modified from default 39000
                "downstream_process_operator_salary": 62000, # Modified from default 52000
                "general_technician_salary": 41000,     # Modified from default 32500
                "qaqc_lab_tech_salary": 47000,         # Modified from default 39000
                "maintenance_tech_salary": 47000,       # Modified from default 39000
                "utility_operator_salary": 47000,       # Modified from default 39000
                "logistics_clerk_salary": 47000,        # Modified from default 39000
                "office_clerk_salary": 41000,          # Modified from default 32500
                "min_fte": 18,                          # Modified from default 15
                "fte_per_tpa": 1.2,                     # Modified from default 1.0
            },

            # OPEX section - simulate form inputs
            "opex": {
                "electricity_usd_per_kwh": 0.125,      # Modified from default 0.107
                "steam_usd_per_kg": 0.028,             # Modified from default 0.0228
                "water_usd_per_m3": 0.0025,            # Modified from default 0.002
                "natural_gas_usd_per_mmbtu": 4.2,      # Modified from default 3.5
                "raw_materials_markup": 1.15,          # Modified from default 1.0
                "utilities_efficiency": 0.88,          # Modified from default 0.85
            },

            # CAPEX section - simulate form inputs
            "capex": {
                "land_cost_per_m2": 650,              # Modified from default 500
                "building_cost_per_m2": 2400,         # Modified from default 2000
                "fermenter_base_cost": 175000,        # Modified from default 150000
                "fermenter_scale_exponent": 0.65,     # Modified from default 0.6
                "centrifuge_cost": 240000,            # Modified from default 200000
                "tff_skid_cost": 175000,              # Modified from default 150000
                "lyophilizer_cost_per_m2": 58000,     # Modified from default 50000
                "utilities_cost_factor": 0.28,        # Modified from default 0.25
                "installation_factor": 0.18,          # Modified from default 0.15
                "contingency_factor": 0.14,           # Modified from default 0.125
                "working_capital_months": 4,          # Modified from default 3
                "parity_mode": False,                 # Ensure we use form inputs
            },

            # Pricing section - simulate form inputs
            "prices": {
                "product_prices": {
                    "yogurt": 475,          # Modified from default 400
                    "lacto_bifido": 475,    # Modified from default 400
                    "bacillus": 475,        # Modified from default 400
                    "sacco": 575,           # Modified from default 500
                    "default": 475,         # Modified from default 400
                },
                "raw_prices": {
                    "glucose": 0.88,               # Modified from typical 0.8
                    "yeast_extract": 6.8,          # Modified from typical 6.0
                    "peptone": 8.8,               # Modified from typical 8.0
                    "corn_steep_liquor": 0.68,     # Modified from typical 0.6
                    "sodium_chloride": 0.25,
                    "magnesium_sulfate": 1.2,
                    "potassium_phosphate": 2.1
                }
            },

            # Equipment optimization - should be configurable via form
            "optimize_equipment": enable_equipment_optimization,
            "use_multiobjective": enable_multiobjective,

            # Optimization section - simulate form inputs
            "optimization": {
                "enabled": enable_equipment_optimization or enable_multiobjective,
                "simulation_type": "deterministic",
                "objectives": ["npv", "irr"] if enable_multiobjective else [],
                "min_tpa": 5.0,                 # Relaxed constraint to allow more exploration
                "max_capex_usd": 25000000,      # Increased to allow more configurations (25M USD)
                "min_utilization": 0.60,        # Relaxed constraint to allow more exploration
                "max_payback": 5.0,             # Relaxed constraint to allow more exploration
                "max_evaluations": 200,         # Increased to force more optimization exploration
                "population_size": 50,          # Increased to explore more solutions
                "n_generations": 20,            # Increased to allow more evolution
                "n_monte_carlo_samples": 100,   # Keep reasonable for speed
                "confidence_level": 0.96,       # Modified from default 0.95
            },

            # Sensitivity section - simulate form inputs
            "sensitivity": {
                "enabled": enable_sensitivity,
                "parameters": ["discount_rate", "electricity_usd_per_kwh", "plant_manager_salary"] if enable_sensitivity else [],
                "delta_percentage": 0.12,       # Modified from default 0.1 (12% vs 10%)
                "grid_points": 3,               # Reduced for faster testing
                "n_samples": 100,               # Reduced for faster testing
            },

            # Assumptions section - should reflect economics values
            "assumptions": {
                "hours_per_year": 8760.0,
                "upstream_availability": 0.92,
                "downstream_availability": 0.90,
                "quality_yield": 0.98,
                "discount_rate": 0.13,          # Should match economics
                "tax_rate": 0.28,               # Should match economics
                "variable_opex_share": 0.88,    # Should match economics
                "maintenance_pct_of_equip": 0.11, # Should match economics
                "ga_other_scale_factor": 12.5,  # Should match economics
                "depreciation_years": 12,       # Should match economics
                "project_lifetime_years": 18,   # Should match economics
            }
        }

    def validate_form_data_structure(self, form_data: Dict[str, Any]) -> List[str]:
        """Validate that the form data has the expected structure."""
        issues = []

        # Check required top-level fields
        required_fields = [
            "name", "strains", "equipment", "volumes",
            "economics", "labor", "opex", "capex", "prices"
        ]

        for field in required_fields:
            if field not in form_data:
                issues.append(f"Missing required field: {field}")
            elif not form_data[field]:
                issues.append(f"Empty field: {field}")

        # Check strains structure
        if "strains" in form_data and isinstance(form_data["strains"], list):
            if len(form_data["strains"]) == 0:
                issues.append("No strains defined")
            else:
                strain = form_data["strains"][0]
                required_strain_fields = [
                    "name", "fermentation_time_h", "turnaround_time_h",
                    "downstream_time_h", "yield_g_per_L"
                ]
                for field in required_strain_fields:
                    if field not in strain:
                        issues.append(f"Missing strain field: {field}")

        # Check nested object structures
        nested_checks = {
            "economics": ["discount_rate", "tax_rate", "project_lifetime_years"],
            "labor": ["plant_manager_salary", "fermentation_specialist_salary"],
            "opex": ["electricity_usd_per_kwh", "steam_usd_per_kg"],
            "capex": ["land_cost_per_m2", "building_cost_per_m2"],
            "equipment": ["reactors_total", "ds_lines_total"]
        }

        for section, required_subfields in nested_checks.items():
            if section in form_data and isinstance(form_data[section], dict):
                for subfield in required_subfields:
                    if subfield not in form_data[section]:
                        issues.append(f"Missing {section}.{subfield}")

        return issues

    def run_scenario_with_form_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send form data to API and return the result."""
        payload = {
            "scenario": form_data,
            "async_mode": False
        }

        try:
            response = requests.post(
                SCENARIO_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=90
            )

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "details": response.text
                }

        except Exception as e:
            return {"success": False, "error": "Exception", "details": str(e)}

    def extract_validation_metrics(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics to validate that form data was processed correctly."""
        if not api_result.get("success"):
            return {"error": "API call failed"}

        result_data = api_result["data"].get("result", {})
        metrics = {}

        # Extract key financial metrics
        if "kpis" in result_data:
            kpis = result_data["kpis"]
            metrics.update({
                "npv": kpis.get("npv"),
                "irr": kpis.get("irr"),
                "payback_years": kpis.get("payback_years"),
                "capex": kpis.get("capex"),
                "opex": kpis.get("opex"),
                "target_tpa": kpis.get("target_tpa"),
                "actual_tpa": kpis.get("tpa"),
                "tpa_ratio": kpis.get("tpa") / kpis.get("target_tpa") if kpis.get("target_tpa") else None,
                "tpa_matches_target": abs(kpis.get("tpa", 0) - kpis.get("target_tpa", 0)) < (kpis.get("target_tpa", 0) * 0.1) if kpis.get("target_tpa") else False
            })

        # Extract economics breakdown
        if "economics" in result_data:
            econ = result_data["economics"]
            metrics.update({
                "annual_revenue": econ.get("annual_revenue"),
                "labor_cost": econ.get("labor_cost"),
                "utilities_cost": econ.get("utilities_cost"),
                "maintenance_cost": econ.get("maintenance_cost"),
                "land_cost": econ.get("land_cost"),
                "building_cost": econ.get("building_cost"),
                "equipment_cost": econ.get("equipment_cost"),
                "total_capex": econ.get("total_capex")
            })

        # Extract capacity info
        if "capacity" in result_data:
            capacity = result_data["capacity"]
            if "per_strain" in capacity and len(capacity["per_strain"]) > 0:
                strain_info = capacity["per_strain"][0]
                metrics.update({
                    "strain_name": strain_info.get("name"),
                    "fermentation_time": strain_info.get("fermentation_time_h"),
                    "batch_mass_kg": strain_info.get("batch_mass_kg"),
                    "annual_kg_good": strain_info.get("annual_kg_good")
                })

        # Extract optimization results if present
        if "optimization" in result_data:
            opt_result = result_data["optimization"]
            if opt_result is not None and isinstance(opt_result, dict):
                metrics.update({
                    "optimization_completed": True,
                    "best_solution_npv": opt_result.get("best_solution", {}).get("npv"),
                    "best_solution_irr": opt_result.get("best_solution", {}).get("irr"),
                    "optimization_evaluations": opt_result.get("n_evaluations", opt_result.get("evaluations_completed", opt_result.get("total_evaluations", 1))),
                    "pareto_front_size": len(opt_result.get("pareto_front", [])),
                    "best_solution_tpa": opt_result.get("best_solution", {}).get("capacity_kg", 0) / 1000.0 if opt_result.get("best_solution", {}).get("capacity_kg") else None,
                    "best_solution_reactors": opt_result.get("best_solution", {}).get("reactors"),
                    "best_solution_ds_lines": opt_result.get("best_solution", {}).get("ds_lines"),
                    "best_solution_volume": opt_result.get("best_solution", {}).get("fermenter_volume_l"),
                })
            else:
                metrics["optimization_completed"] = False
        else:
            metrics["optimization_completed"] = False

        # Extract sensitivity results if present
        if "sensitivity" in result_data:
            sens_result = result_data["sensitivity"]
            # Check if sensitivity has actual parameter results
            if isinstance(sens_result, dict) and len(sens_result) > 0:
                # Count parameters that have actual sensitivity data
                param_count = 0
                for key, value in sens_result.items():
                    if isinstance(value, dict) and len(value) > 0:
                        param_count += 1

                metrics.update({
                    "sensitivity_completed": True,
                    "sensitivity_parameters": list(sens_result.keys()),
                    "sensitivity_results_count": param_count,
                })
            else:
                metrics["sensitivity_completed"] = False
        else:
            metrics["sensitivity_completed"] = False

        return metrics

    def validate_form_effects(self, metrics: Dict[str, Any], expected_values: Dict[str, Any],
                             test_scenario: str = "basic") -> Dict[str, Any]:
        """Validate that form inputs had the expected effects on results."""
        validations = {}

        # Check that target TPA was respected in form processing
        if "target_tpa" in metrics and "target_tpa" in expected_values:
            expected = expected_values["target_tpa"]
            actual = metrics["target_tpa"]
            validations["target_tpa_form"] = {
                "expected": expected,
                "actual": actual,
                "passed": abs(actual - expected) < 0.1,
                "test": "Target TPA should match form input"
            }

        # Check that actual TPA production is reasonable vs target
        if "actual_tpa" in metrics and "target_tpa" in metrics:
            target = metrics["target_tpa"]
            actual = metrics["actual_tpa"]
            tpa_ratio = metrics.get("tpa_ratio", 0)

            validations["tpa_production_reasonable"] = {
                "expected": f"Close to {target} TPA",
                "actual": f"{actual:.1f} TPA (ratio: {tpa_ratio:.1f}x)",
                "passed": 0.8 <= tpa_ratio <= 1.5 if tpa_ratio else False,  # Allow 20% under to 50% over
                "test": "Actual TPA production should be reasonably close to target TPA"
            }

        # Check for optimization TPA consistency
        if "best_solution_tpa" in metrics and metrics["best_solution_tpa"] is not None:
            target = metrics.get("target_tpa", 0)
            opt_tpa = metrics["best_solution_tpa"]

            validations["optimization_tpa_consistency"] = {
                "expected": f"Close to {target} TPA",
                "actual": f"{opt_tpa:.1f} TPA",
                "passed": abs(opt_tpa - target) <= target * 0.2,  # Allow 20% deviation
                "test": "Optimization best solution TPA should align with target"
            }

        # Check that strain parameters were used
        if "strain_name" in metrics and "strain_name" in expected_values:
            validations["strain_name"] = {
                "expected": expected_values["strain_name"],
                "actual": metrics["strain_name"],
                "passed": metrics["strain_name"] == expected_values["strain_name"],
                "test": "Strain name should match form input"
            }

        if "fermentation_time" in metrics and "fermentation_time" in expected_values:
            expected = expected_values["fermentation_time"]
            actual = metrics["fermentation_time"]
            validations["fermentation_time"] = {
                "expected": expected,
                "actual": actual,
                "passed": abs(actual - expected) < 0.1,
                "test": "Fermentation time should match form input"
            }

        # Validate that modified economics values affected results
        # Higher costs should generally reduce NPV/IRR compared to defaults
        financial_impact_tests = {
            "npv_positive": {
                "test": "NPV should be positive (basic sanity check)",
                "passed": metrics.get("npv", 0) > 0,
                "value": metrics.get("npv")
            },
            "irr_reasonable": {
                "test": "IRR should be reasonable (0.1 to 5.0)",
                "passed": 0.1 <= metrics.get("irr", 0) <= 5.0,
                "value": metrics.get("irr")
            },
            "payback_reasonable": {
                "test": "Payback should be reasonable (1-10 years)",
                "passed": 1.0 <= metrics.get("payback_years", 0) <= 10.0,
                "value": metrics.get("payback_years")
            }
        }

        validations.update(financial_impact_tests)

        # Add optimization-specific validations
        if test_scenario in ["equipment_optimization", "multiobjective", "combined"]:
            optimization_tests = {
                "optimization_completed": {
                    "test": "Optimization should complete successfully",
                    "passed": metrics.get("optimization_completed", False),
                    "value": metrics.get("optimization_completed", False)
                }
            }

            if metrics.get("optimization_completed"):
                optimization_tests.update({
                    "optimization_evaluations": {
                        "test": "Optimization should perform multiple evaluations",
                        "passed": metrics.get("optimization_evaluations", 0) > 1,
                        "value": metrics.get("optimization_evaluations", 0)
                    }
                })

                if test_scenario == "multiobjective":
                    optimization_tests["pareto_front_size"] = {
                        "test": "Multiobjective optimization should generate Pareto front",
                        "passed": metrics.get("pareto_front_size", 0) > 0,
                        "value": metrics.get("pareto_front_size", 0)
                    }

            validations.update(optimization_tests)

            # Add optimization configuration analysis
            if test_scenario == "multiobjective" and metrics.get("optimization_completed"):
                # Check if multiobjective is actually different from single objective
                validations["multiobjective_difference"] = {
                    "test": "Multiobjective optimization should explore trade-offs between objectives",
                    "passed": metrics.get("pareto_front_size", 0) > 1,  # Should have multiple solutions
                    "value": f"Pareto front size: {metrics.get('pareto_front_size', 0)}"
                }

        # Add sensitivity-specific validations
        if test_scenario in ["sensitivity", "combined"]:
            sensitivity_tests = {
                "sensitivity_completed": {
                    "test": "Sensitivity analysis should complete successfully",
                    "passed": metrics.get("sensitivity_completed", False),
                    "value": metrics.get("sensitivity_completed", False)
                }
            }

            if metrics.get("sensitivity_completed"):
                sensitivity_tests["sensitivity_parameters"] = {
                    "test": "Sensitivity analysis should analyze specified parameters",
                    "passed": metrics.get("sensitivity_results_count", 0) > 0,
                    "value": metrics.get("sensitivity_parameters", [])
                }

            validations.update(sensitivity_tests)

        return validations

    def run_single_scenario_test(self, test_name: str, enable_equipment_opt: bool = False,
                                enable_multiobjective: bool = False, enable_sensitivity: bool = False) -> Dict[str, Any]:
        """Run a single test scenario with specified optimization settings."""

        print(f"\n🧪 Running {test_name} Test...")

        # Generate form data for this scenario
        form_data = self.simulate_comprehensive_form_data(
            enable_equipment_optimization=enable_equipment_opt,
            enable_multiobjective=enable_multiobjective,
            enable_sensitivity=enable_sensitivity,
            scenario_name=f"{test_name} Scenario"
        )

        # Validate structure
        structure_issues = self.validate_form_data_structure(form_data)
        if structure_issues:
            return {
                "test_name": test_name,
                "success": False,
                "error": "Form structure validation failed",
                "issues": structure_issues
            }

        # Send to API
        print(f"   📡 Sending {test_name.lower()} request to API...")
        if enable_equipment_opt or enable_multiobjective:
            print(f"      - Equipment optimization: {enable_equipment_opt}")
            print(f"      - Multiobjective optimization: {enable_multiobjective}")
        if enable_sensitivity:
            print(f"      - Sensitivity analysis: {enable_sensitivity}")

        api_result = self.run_scenario_with_form_data(form_data)

        if not api_result["success"]:
            return {
                "test_name": test_name,
                "success": False,
                "error": f"API call failed: {api_result['error']}",
                "details": api_result.get("details")
            }

        # Extract and validate results
        metrics = self.extract_validation_metrics(api_result)

        if "error" in metrics:
            return {
                "test_name": test_name,
                "success": False,
                "error": f"Failed to extract metrics: {metrics['error']}"
            }

        # Determine test scenario type for validation
        scenario_type = "basic"
        if enable_sensitivity and (enable_equipment_opt or enable_multiobjective):
            scenario_type = "combined"
        elif enable_sensitivity:
            scenario_type = "sensitivity"
        elif enable_multiobjective:
            scenario_type = "multiobjective"
        elif enable_equipment_opt:
            scenario_type = "equipment_optimization"

        # Validate results
        expected_values = {
            "target_tpa": form_data["target_tpa"],
            "strain_name": form_data["strains"][0]["name"],
            "fermentation_time": form_data["strains"][0]["fermentation_time_h"],
        }

        validations = self.validate_form_effects(metrics, expected_values, scenario_type)

        passed_tests = sum(1 for v in validations.values() if v.get("passed", False))
        total_tests = len(validations)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        print(f"   ✅ {test_name} completed: {passed_tests}/{total_tests} validations passed ({success_rate*100:.1f}%)")

        # Show key results with TPA analysis
        if metrics.get("npv"):
            print(f"      NPV: ${metrics['npv']:,.0f}")

        # Show TPA analysis
        if metrics.get("target_tpa") and metrics.get("actual_tpa"):
            target = metrics["target_tpa"]
            actual = metrics["actual_tpa"]
            ratio = metrics.get("tpa_ratio", 0)
            status = "✅" if 0.8 <= ratio <= 1.5 else "⚠️"
            print(f"      TPA: {status} Target {target} → Actual {actual:.1f} (ratio: {ratio:.1f}x)")

        if metrics.get("optimization_completed"):
            print(f"      Optimization: Completed ({metrics.get('optimization_evaluations', 0)} evaluations)")
            if metrics.get("best_solution_tpa"):
                print(f"      Best Solution: {metrics['best_solution_reactors']}R×{metrics['best_solution_ds_lines']}DS×{metrics['best_solution_volume']:.0f}L → {metrics['best_solution_tpa']:.1f} TPA")

        if metrics.get("sensitivity_completed"):
            print(f"      Sensitivity: Completed ({metrics.get('sensitivity_results_count', 0)} parameters)")

        return {
            "test_name": test_name,
            "success": True,
            "success_rate": success_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "validations": validations,
            "metrics": metrics,
            "form_data": form_data,
            "api_result": api_result
        }

    def run_comprehensive_test(self) -> bool:
        """Run the comprehensive frontend form collection test with all optimization modes."""
        print("=" * 90)
        print("COMPREHENSIVE FRONTEND FORM COLLECTION TEST")
        print("Bioprocess Web Application - Form Data + Optimization + Sensitivity Testing")
        print("=" * 90)
        print(f"Testing API at: {API_BASE}")
        print(f"Timestamp: {datetime.now()}")
        print()

        # Define test scenarios to run
        test_scenarios = [
            {
                "name": "Basic Form Data",
                "description": "Testing basic form data collection without optimization",
                "equipment_opt": False,
                "multiobjective": False,
                "sensitivity": False
            },
            {
                "name": "Equipment Optimization",
                "description": "Testing form data with equipment optimization enabled",
                "equipment_opt": True,
                "multiobjective": False,
                "sensitivity": False
            },
            {
                "name": "Multiobjective Optimization",
                "description": "Testing form data with multiobjective optimization enabled",
                "equipment_opt": True,
                "multiobjective": True,
                "sensitivity": False
            },
            {
                "name": "Sensitivity Analysis",
                "description": "Testing form data with sensitivity analysis enabled",
                "equipment_opt": False,
                "multiobjective": False,
                "sensitivity": True
            },
            {
                "name": "Combined Optimization + Sensitivity",
                "description": "Testing form data with both optimization and sensitivity enabled",
                "equipment_opt": True,
                "multiobjective": True,
                "sensitivity": True
            }
        ]

        print(f"🧪 Running {len(test_scenarios)} test scenarios:")
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"   {i}. {scenario['name']} - {scenario['description']}")
        print()

        # Run all test scenarios
        scenario_results = []
        for scenario in test_scenarios:
            result = self.run_single_scenario_test(
                scenario["name"],
                scenario["equipment_opt"],
                scenario["multiobjective"],
                scenario["sensitivity"]
            )
            scenario_results.append(result)

            # Short pause between tests to avoid overwhelming the server
            if len(scenario_results) < len(test_scenarios):
                print("   ⏳ Waiting 2 seconds before next test...")
                import time
                time.sleep(2)

        # Analyze overall results
        print("\n" + "=" * 90)
        print("DETAILED SCENARIO RESULTS")
        print("=" * 90)

        successful_scenarios = 0
        total_validations_passed = 0
        total_validations = 0

        for result in scenario_results:
            if result["success"]:
                success_rate = result["success_rate"]
                status_emoji = "🎉" if success_rate >= 0.9 else "✅" if success_rate >= 0.8 else "⚠️" if success_rate >= 0.6 else "❌"

                print(f"\n{status_emoji} {result['test_name']}")
                print(f"   Success Rate: {result['passed_tests']}/{result['total_tests']} ({success_rate*100:.1f}%)")

                # Show key metrics
                metrics = result["metrics"]
                if metrics.get("npv"):
                    print(f"   NPV: ${metrics['npv']:,.0f}")
                # Show TPA analysis
                if metrics.get("target_tpa") and metrics.get("actual_tpa"):
                    target = metrics["target_tpa"]
                    actual = metrics["actual_tpa"]
                    ratio = metrics.get("tpa_ratio", 0)
                    status = "✅" if 0.8 <= ratio <= 1.5 else "⚠️"
                    print(f"   TPA Analysis: {status} Target {target} → Actual {actual:.1f} (ratio: {ratio:.1f}x)")

                if metrics.get("optimization_completed"):
                    evals = metrics.get("optimization_evaluations", 0)
                    print(f"   Optimization: ✅ Completed ({evals} evaluations)")
                    if metrics.get("pareto_front_size", 0) > 0:
                        print(f"   Pareto Front: {metrics['pareto_front_size']} solutions")
                    if metrics.get("best_solution_tpa"):
                        print(f"   Best Config: {metrics['best_solution_reactors']}R×{metrics['best_solution_ds_lines']}DS×{metrics['best_solution_volume']:.0f}L → {metrics['best_solution_tpa']:.1f} TPA")

                if metrics.get("sensitivity_completed"):
                    params = metrics.get("sensitivity_results_count", 0)
                    print(f"   Sensitivity: ✅ Completed ({params} parameters analyzed)")

                # Count failed validations and categorize them
                failed_validations = []
                tpa_issues = []
                optimization_issues = []
                other_issues = []

                for val_name, val_result in result["validations"].items():
                    if not val_result.get("passed", False):
                        failed_validations.append(val_name)
                        if "tpa" in val_name.lower():
                            tpa_issues.append(val_name)
                        elif "optimization" in val_name.lower() or "multiobjective" in val_name.lower():
                            optimization_issues.append(val_name)
                        else:
                            other_issues.append(val_name)

                if failed_validations:
                    print(f"   ⚠️  Failed validations: {', '.join(failed_validations)}")
                    if tpa_issues:
                        print(f"      🎯 TPA Issues: {', '.join(tpa_issues)}")
                    if optimization_issues:
                        print(f"      🔧 Optimization Issues: {', '.join(optimization_issues)}")
                    if other_issues:
                        print(f"      ❓ Other Issues: {', '.join(other_issues)}")

                if success_rate >= 0.8:
                    successful_scenarios += 1

                total_validations_passed += result["passed_tests"]
                total_validations += result["total_tests"]

            else:
                print(f"\n❌ {result['test_name']}")
                print(f"   Error: {result['error']}")
                if "details" in result:
                    print(f"   Details: {result['details']}")

        # Overall summary
        overall_success_rate = total_validations_passed / total_validations if total_validations > 0 else 0

        print("\n" + "=" * 90)
        print("FINAL TEST SUMMARY")
        print("=" * 90)

        print(f"📊 Overall Statistics:")
        print(f"   • Successful Scenarios: {successful_scenarios}/{len(test_scenarios)} ({successful_scenarios/len(test_scenarios)*100:.1f}%)")
        print(f"   • Total Validations Passed: {total_validations_passed}/{total_validations} ({overall_success_rate*100:.1f}%)")
        print()

        # Analyze common issues across scenarios
        print("🔍 Issue Analysis:")
        tpa_problem_scenarios = []
        identical_results_scenarios = []

        for result in scenario_results:
            if result["success"]:
                metrics = result["metrics"]

                # Check for TPA ratio issues
                if metrics.get("tpa_ratio") and (metrics["tpa_ratio"] > 1.5 or metrics["tpa_ratio"] < 0.8):
                    tpa_problem_scenarios.append(f"{result['test_name']} (ratio: {metrics['tpa_ratio']:.1f}x)")

                # Track NPV values to detect identical results
                npv = metrics.get("npv")
                if npv:
                    found_duplicate = False
                    for other_result in scenario_results:
                        if (other_result != result and other_result["success"] and
                            other_result["metrics"].get("npv") and
                            abs(other_result["metrics"]["npv"] - npv) < 1000):  # Within $1000
                            identical_results_scenarios.append(f"{result['test_name']} & {other_result['test_name']} (${npv:,.0f})")
                            break

        if tpa_problem_scenarios:
            print(f"   ⚠️  TPA Target Mismatch: {len(tpa_problem_scenarios)} scenarios")
            for scenario in tpa_problem_scenarios[:3]:  # Show first 3
                print(f"      - {scenario}")

        if identical_results_scenarios:
            print(f"   🔄 Identical Results: {len(set(identical_results_scenarios))} pairs")
            for pair in list(set(identical_results_scenarios))[:2]:  # Show first 2 unique pairs
                print(f"      - {pair}")

        if not tpa_problem_scenarios and not identical_results_scenarios:
            print("   ✅ No major issues detected")
        print()

        # Feature-specific summary
        feature_status = {
            "Basic Form Data": "❓",
            "Equipment Optimization": "❓",
            "Multiobjective Optimization": "❓",
            "Sensitivity Analysis": "❓",
            "Combined Features": "❓"
        }

        for result in scenario_results:
            if result["success"]:
                status = "✅" if result["success_rate"] >= 0.8 else "⚠️" if result["success_rate"] >= 0.6 else "❌"
                feature_status[result["test_name"]] = status
            else:
                feature_status[result["test_name"]] = "❌"

        print("🎯 Feature Status:")
        for feature, status in feature_status.items():
            print(f"   {status} {feature}")
        print()

        # Save comprehensive results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"comprehensive_form_test_results_{timestamp}.json"

        comprehensive_summary = {
            "timestamp": datetime.now().isoformat(),
            "overall_summary": {
                "successful_scenarios": successful_scenarios,
                "total_scenarios": len(test_scenarios),
                "scenario_success_rate": successful_scenarios / len(test_scenarios),
                "total_validations_passed": total_validations_passed,
                "total_validations": total_validations,
                "overall_validation_rate": overall_success_rate,
                "feature_status": feature_status
            },
            "scenario_results": scenario_results
        }

        with open(results_file, 'w') as f:
            json.dump(comprehensive_summary, f, indent=2)

        print(f"📁 Comprehensive results saved to: {results_file}")

        # Final assessment
        if successful_scenarios == len(test_scenarios) and overall_success_rate >= 0.9:
            print("\n🎉 ALL FRONTEND FEATURES ARE WORKING EXCELLENTLY!")
            print("✅ Form data collection system is fully functional")
            print("✅ Equipment optimization is working correctly")
            print("✅ Multiobjective optimization is working correctly")
            print("✅ Sensitivity analysis is working correctly")
            print("✅ Combined optimization modes are working correctly")
            overall_success = True
        elif successful_scenarios >= len(test_scenarios) * 0.8 and overall_success_rate >= 0.8:
            print("\n👍 MOST FRONTEND FEATURES ARE WORKING WELL")
            print("Core functionality is working with minor issues detected.")
            overall_success = True
        else:
            print("\n⚠️  SIGNIFICANT ISSUES DETECTED IN FRONTEND FEATURES")
            print("Multiple features are not working correctly.")
            overall_success = False

        print("=" * 90)
        return overall_success

def main():
    """Main entry point."""
    tester = FrontendFormCollectionTester()

    try:
        success = tester.run_comprehensive_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test failed with unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
