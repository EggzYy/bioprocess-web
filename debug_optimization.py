#!/usr/bin/env python3
"""
Debug script to isolate optimization infinity values issue.
Tests individual components to find where infinity is generated.
"""

import sys
import os
import numpy as np
import pandas as pd
import logging

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bioprocess.models import ScenarioInput, StrainInput, VolumePlan, EquipmentConfig
from bioprocess.orchestrator import run_scenario
from bioprocess.optimizer_enhanced import optimize_with_capacity_enforcement
from bioprocess.optimizer import evaluate_configuration
from bioprocess.presets import RAW_PRICES

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_simple_test_scenario():
    """Create a simple test scenario that should work."""

    # Single strain with reasonable values
    strain = StrainInput(
        name="Test Strain",
        fermentation_time_h=18.0,
        turnaround_time_h=9.0,
        downstream_time_h=4.0,
        yield_g_per_L=50.0,
        media_cost_usd=100.0,
        cryo_cost_usd=50.0,
        utility_rate_ferm_kw=300.0,
        utility_rate_cent_kw=15.0,
        utility_rate_lyo_kw=1.5,
        utility_cost_steam=0.05,
        licensing_fixed_cost_usd=100000.0,
        licensing_royalty_pct=0.02,
        cv_ferm=0.1,
        cv_turn=0.1,
        cv_down=0.1
    )

    # Equipment config
    equipment = EquipmentConfig(
        reactors_total=4,
        ds_lines_total=2,
        reactor_allocation_policy="inverse_ct",
        shared_downstream=True,
        year_hours=8760,
        reactors_per_strain={"Test Strain": 4},
        ds_lines_per_strain={"Test Strain": 2},
        upstream_availability=0.85,
        downstream_availability=0.85,
        quality_yield=0.95,
        ds_allocation_policy="inverse_ct"
    )

    # Volume config
    volumes = VolumePlan(
        base_fermenter_vol_l=2000,
        volume_options_l=[500, 1000, 2000],  # Small set for testing
        working_volume_fraction=0.8,
        seed_fermenter_ratio=0.1,
        media_tank_ratio=1.2
    )

    # Scenario with explicit product prices
    scenario = ScenarioInput(
        name="Debug Test",
        description="Simple test scenario for debugging infinity values",
        target_tpa=10,
        strains=[strain],
        equipment=equipment,
        volumes=volumes,
        optimize_equipment=True,
        use_multiobjective=True,
        prices={
            "product_prices": {"Test Strain": 425.0, "default": 425.0},
            "raw_prices": RAW_PRICES
        }
    )

    return scenario

def check_for_infinity(data, name="data"):
    """Check data structure for infinity values."""
    if isinstance(data, dict):
        for key, value in data.items():
            if check_for_infinity(value, f"{name}.{key}"):
                return True
    elif isinstance(data, (list, tuple)):
        for i, value in enumerate(data):
            if check_for_infinity(value, f"{name}[{i}]"):
                return True
    elif isinstance(data, (int, float)):
        if np.isinf(data):
            print(f"🚨 INFINITY FOUND: {name} = {data}")
            return True
        elif np.isnan(data):
            print(f"🚨 NaN FOUND: {name} = {data}")
            return True
    elif hasattr(data, '__dict__'):
        return check_for_infinity(data.__dict__, name)

    return False

def test_single_configuration():
    """Test a single configuration to isolate the issue."""
    print("=" * 60)
    print("TESTING SINGLE CONFIGURATION")
    print("=" * 60)

    scenario = create_simple_test_scenario()

    # Test parameters that should be safe
    reactors = 4
    ds_lines = 2
    fermenter_volume_l = 2000

    print(f"Testing: {reactors} reactors, {ds_lines} DS lines, {fermenter_volume_l}L")

    try:
        result = evaluate_configuration(reactors, ds_lines, fermenter_volume_l, scenario)

        print("✅ evaluate_configuration completed")
        print(f"Result keys: {list(result.keys())}")

        # Check for infinity in result
        has_inf = check_for_infinity(result, "result")

        if has_inf:
            print("❌ Infinity values found in single configuration!")
        else:
            print("✅ No infinity values in single configuration")

        # Print key metrics
        print(f"Capacity (kg): {result.get('capacity_kg', 'N/A')}")
        print(f"CAPEX: {result.get('capex', 'N/A')}")
        print(f"NPV: {result.get('npv', 'N/A')}")
        print(f"IRR: {result.get('irr', 'N/A')}")
        print(f"Meets capacity: {result.get('meets_capacity', 'N/A')}")

        return result

    except Exception as e:
        print(f"❌ Error in evaluate_configuration: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_small_grid_search():
    """Test a very small grid search to isolate issues."""
    print("\n" + "=" * 60)
    print("TESTING SMALL GRID SEARCH")
    print("=" * 60)

    scenario = create_simple_test_scenario()

    # Very small search space
    volumes = [2000]  # Single volume
    reactors_range = [4, 5]  # Just 2 reactor counts
    ds_range = [2]  # Single DS count

    print(f"Testing {len(volumes)} volumes × {len(reactors_range)} reactors × {len(ds_range)} DS = {len(volumes) * len(reactors_range) * len(ds_range)} evaluations")

    results = []

    try:
        for volume in volumes:
            for reactors in reactors_range:
                for ds_lines in ds_range:
                    print(f"  Testing: {volume}L, {reactors}R, {ds_lines}DS")

                    result = evaluate_configuration(reactors, ds_lines, volume, scenario)
                    results.append(result)

                    # Check for infinity immediately
                    if check_for_infinity(result, f"config_{volume}_{reactors}_{ds_lines}"):
                        print(f"❌ Infinity found at {volume}L, {reactors}R, {ds_lines}DS")
                        return results

        print(f"✅ Completed {len(results)} evaluations without infinity")

        # Convert to DataFrame to check for infinity
        df = pd.DataFrame(results)

        # Check DataFrame for infinity
        inf_columns = []
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64']:
                if df[col].isin([np.inf, -np.inf]).any():
                    inf_columns.append(col)
                    print(f"🚨 Infinity in column: {col}")
                    print(f"   Values: {df[col].tolist()}")

        if inf_columns:
            print(f"❌ Found infinity in columns: {inf_columns}")
        else:
            print("✅ No infinity in DataFrame")

        return results

    except Exception as e:
        print(f"❌ Error in small grid search: {e}")
        import traceback
        traceback.print_exc()
        return results

def test_full_optimization():
    """Test the full optimization function with minimal parameters."""
    print("\n" + "=" * 60)
    print("TESTING FULL OPTIMIZATION (MINIMAL)")
    print("=" * 60)

    scenario = create_simple_test_scenario()

    # Use minimal search space
    volume_options = [500, 1000, 2000]  # Triple volume
    max_reactors = 6  # Just 4, 5, 6 reactors (3 values)
    max_ds_lines = 3  # Just 1, 2, 3 DS lines (3 values)

    total_evals = len(volume_options) * (max_reactors - 1) * max_ds_lines
    print(f"Expected evaluations: {total_evals}")

    try:
        best_solution, all_results_df = optimize_with_capacity_enforcement(
            scenario,
            max_reactors=max_reactors,
            max_ds_lines=max_ds_lines,
            volume_options=volume_options,
            enforce_capacity=True,
            max_allowed_excess=0.2
        )

        print("✅ Optimization completed")

        if best_solution:
            print(f"Best solution keys: {list(best_solution.keys())}")
            if check_for_infinity(best_solution, "best_solution"):
                print("❌ Infinity in best solution")
            else:
                print("✅ No infinity in best solution")

        if not all_results_df.empty:
            print(f"Results DataFrame shape: {all_results_df.shape}")

            # Check DataFrame for infinity
            inf_columns = []
            for col in all_results_df.columns:
                if all_results_df[col].dtype in ['float64', 'int64']:
                    if all_results_df[col].isin([np.inf, -np.inf]).any():
                        inf_columns.append(col)

            if inf_columns:
                print(f"❌ Infinity in DataFrame columns: {inf_columns}")
                for col in inf_columns:
                    inf_rows = all_results_df[all_results_df[col].isin([np.inf, -np.inf])]
                    print(f"   Column {col} infinity rows:")
                    print(inf_rows[['reactors', 'ds_lines', 'fermenter_volume_l', col]].to_string(index=False))
            else:
                print("✅ No infinity in results DataFrame")

        return best_solution, all_results_df

    except Exception as e:
        print(f"❌ Error in optimization: {e}")
        import traceback
        traceback.print_exc()
        return None, pd.DataFrame()

def test_scenario_run():
    """Test the full scenario run to see where infinity gets introduced."""
    print("\n" + "=" * 60)
    print("TESTING FULL SCENARIO RUN")
    print("=" * 60)

    scenario = create_simple_test_scenario()

    # Use very minimal optimization to isolate issue
    scenario.volumes.volume_options_l = [2000]  # Single volume

    try:
        result = run_scenario(scenario, optimize=True)

        print("✅ Scenario run completed")

        # Check result for infinity
        if hasattr(result, '__dict__'):
            has_inf = check_for_infinity(result.__dict__, "scenario_result")
            if has_inf:
                print("❌ Infinity found in scenario result")
            else:
                print("✅ No infinity in scenario result")

        return result

    except Exception as e:
        print(f"❌ Error in scenario run: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main debugging function."""
    print("🔍 DEBUG: Optimization Infinity Values")
    print("=" * 60)

    # Test 1: Single configuration
    single_result = test_single_configuration()

    if single_result and not check_for_infinity(single_result):
        # Test 2: Small grid search
        grid_results = test_small_grid_search()

        if grid_results:
            # Test 3: Full optimization (minimal)
            best, all_results = test_full_optimization()

            if best is not None:
                # Test 4: Full scenario run
                scenario_result = test_scenario_run()

                print(f"\n" + "=" * 60)
                print("DEBUGGING COMPLETE")
                print("=" * 60)

                if scenario_result:
                    print("✅ All tests passed - no infinity source found")
                    print("The issue might be in API serialization or response handling")
                else:
                    print("❌ Issue found in scenario run")
            else:
                print("❌ Issue found in optimization function")
        else:
            print("❌ Issue found in grid search")
    else:
        print("❌ Issue found in single configuration evaluation")

def test_json_serialization():
    """Test JSON serialization of optimization results to find infinity issue."""
    print("\n" + "=" * 60)
    print("TESTING JSON SERIALIZATION")
    print("=" * 60)

    scenario = create_simple_test_scenario()

    try:
        result = run_scenario(scenario, optimize=True)

        print("✅ Scenario run completed, testing JSON serialization...")

        import json

        # Test serializing the full result
        try:
            result_dict = result.__dict__ if hasattr(result, '__dict__') else result
            json_str = json.dumps(result_dict, default=str)
            print("✅ Basic JSON serialization successful")
        except (ValueError, TypeError) as e:
            print(f"❌ JSON serialization failed: {e}")

            # Try to find the specific field causing issues
            if hasattr(result, '__dict__'):
                print("Testing individual fields...")
                for key, value in result.__dict__.items():
                    try:
                        json.dumps({key: value}, default=str)
                        print(f"  ✅ {key}: OK")
                    except (ValueError, TypeError) as field_error:
                        print(f"  ❌ {key}: {field_error}")

                        # Dive deeper into nested objects
                        if hasattr(value, '__dict__'):
                            print(f"    Testing nested fields in {key}:")
                            for nested_key, nested_value in value.__dict__.items():
                                try:
                                    json.dumps({nested_key: nested_value}, default=str)
                                    print(f"      ✅ {nested_key}: OK")
                                except Exception as nested_error:
                                    print(f"      ❌ {nested_key}: {nested_error}")
                                    print(f"         Value: {nested_value}")
                                    print(f"         Type: {type(nested_value)}")

        # Test API-style response format
        print("\nTesting API response format...")
        try:
            api_response = {
                "job_id": None,
                "result": result.__dict__ if hasattr(result, '__dict__') else result,
                "status": "completed",
                "message": "success"
            }
            json_str = json.dumps(api_response, default=str)
            print("✅ API response JSON serialization successful")
        except Exception as api_error:
            print(f"❌ API response JSON serialization failed: {api_error}")

        return result

    except Exception as e:
        print(f"❌ Error in scenario run: {e}")
        import traceback
        traceback.print_exc()
        return None

    print("\n🎯 RECOMMENDATIONS:")
    print("1. Check the specific error messages above")
    print("2. Look for division by zero in economics calculations")
    print("3. Check for invalid parameter combinations")
    print("4. Verify all input data has finite values")
    print("5. Check JSON serialization issues in API response")

def main():
    """Main debugging function."""
    print("🔍 DEBUG: Optimization Infinity Values")
    print("=" * 60)

    # Test 1: Single configuration
    single_result = test_single_configuration()

    if single_result and not check_for_infinity(single_result):
        # Test 2: Small grid search
        grid_results = test_small_grid_search()

        if grid_results:
            # Test 3: Full optimization (minimal)
            best, all_results = test_full_optimization()

            if best is not None:
                # Test 4: Full scenario run
                scenario_result = test_scenario_run()

                if scenario_result:
                    # Test 5: JSON serialization
                    json_result = test_json_serialization()

                print(f"\n" + "=" * 60)
                print("DEBUGGING COMPLETE")
                print("=" * 60)

                if json_result:
                    print("✅ All tests passed - no infinity source found")
                    print("The issue might be in API serialization or response handling")
                else:
                    print("❌ Issue found in JSON serialization")
            else:
                print("❌ Issue found in optimization function")
        else:
            print("❌ Issue found in grid search")
    else:
        print("❌ Issue found in single configuration evaluation")

if __name__ == "__main__":
    main()
