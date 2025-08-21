#!/usr/bin/env python3
"""
Debug script to investigate volume options hardcoding issue.
This script tests whether volume options from checkboxes are properly used
in scenario processing and traces the exact flow of different volume variables.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bioprocess.models import ScenarioInput, StrainInput, EquipmentConfig, VolumePlan
from bioprocess.orchestrator import run_scenario
import json

def create_test_scenario(volume_options, base_volume):
    """Create a test scenario with specific volume options."""

    # Create strain configuration
    strain = StrainInput(
        name="ecoli",
        fermentation_titer=100.0,
        fermentation_yield=0.3,
        cell_density=50.0,
        fermentation_time=72.0,
        seed_train_time=48.0,
        downstream_time=24.0,
        downstream_yield=0.85,
        requires_tff=True,
        downstream_complexity="medium"
    )

    # Create equipment configuration
    equipment = EquipmentConfig(
        reactors_total=4,
        ds_lines_total=2,
        reactor_allocation_policy="equal",
        shared_downstream=True,
        optimize_equipment=False
    )

    # Create volume plan with the provided options
    volumes = VolumePlan(
        base_fermenter_vol_l=base_volume,
        volume_options_l=volume_options,
        working_volume_fraction=0.8,
        media_tank_ratio=1.25
    )

    # Create scenario
    scenario = ScenarioInput(
        name="Volume Debug Test",
        description="Testing volume options behavior",
        target_tpa=1000,
        strains=[strain],
        equipment=equipment,
        volumes=volumes,
        optimize_equipment=False
    )

    return scenario

def trace_volume_usage(scenario, expected_fermenter_vol):
    """Trace how volumes are used throughout the system."""
    print(f"\n=== TRACING VOLUME USAGE ===")
    print(f"Input Configuration:")
    print(f"  base_fermenter_vol_l: {scenario.volumes.base_fermenter_vol_l}L")
    print(f"  volume_options_l: {scenario.volumes.volume_options_l}")
    print(f"  working_volume_fraction: {scenario.volumes.working_volume_fraction}")
    print(f"  media_tank_ratio: {scenario.volumes.media_tank_ratio}")
    print(f"  optimize_equipment: {scenario.optimize_equipment}")

    # Calculate expected values
    expected_working_vol = expected_fermenter_vol * scenario.volumes.working_volume_fraction
    expected_media_tank = expected_fermenter_vol * scenario.volumes.media_tank_ratio

    print(f"\nExpected Calculations (if fermenter_volume_l = {expected_fermenter_vol}L):")
    print(f"  Working Volume: {expected_fermenter_vol}L × {scenario.volumes.working_volume_fraction} = {expected_working_vol}L")
    print(f"  Media Tank Volume: {expected_fermenter_vol}L × {scenario.volumes.media_tank_ratio} = {expected_media_tank}L")

    try:
        result = run_scenario(scenario)

        print(f"\nActual Results:")
        print(f"  Fermenter Volume Used: {result.equipment.specifications.fermenter_volume_l}L")
        print(f"  Media Tank Volume: {result.equipment.specifications.media_tank_volume_l}L")
        print(f"  Seed Fermenter Volume: {result.equipment.specifications.seed_fermenter_volume_l}L")

        # Verify calculations
        actual_fermenter = result.equipment.specifications.fermenter_volume_l
        actual_media = result.equipment.specifications.media_tank_volume_l
        calculated_media = actual_fermenter * scenario.volumes.media_tank_ratio

        print(f"\nValidation:")
        if actual_fermenter == expected_fermenter_vol:
            print(f"  ✓ Fermenter volume matches expected ({expected_fermenter_vol}L)")
        else:
            print(f"  ✗ Fermenter volume MISMATCH! Expected: {expected_fermenter_vol}L, Got: {actual_fermenter}L")

        if abs(actual_media - calculated_media) < 0.1:
            print(f"  ✓ Media tank calculation is correct: {actual_fermenter}L × 1.25 = {actual_media}L")
        else:
            print(f"  ✗ Media tank calculation WRONG! Expected: {calculated_media}L, Got: {actual_media}L")

        # Check if this is where the 2500L comes from
        if abs(actual_media - 2500.0) < 0.1:
            print(f"  🔍 FOUND THE 2500L! It's the media tank volume.")
            print(f"     This comes from fermenter {actual_fermenter}L × media_tank_ratio 1.25 = {actual_media}L")

        return result

    except Exception as e:
        print(f"Error running scenario: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_checkbox_scenarios():
    """Test scenarios that simulate different checkbox selections."""
    print("=" * 60)
    print("TESTING CHECKBOX SELECTION SCENARIOS")
    print("=" * 60)

    # Test 1: Default case - 2000L checkbox selected (mimics default HTML)
    print(f"\n" + "="*50)
    print("TEST 1: Default case (2000L checkbox selected)")
    print(f"="*50)
    print("This simulates the default HTML state where vol2000 checkbox is checked")
    scenario1 = create_test_scenario([2000], 2000)
    result1 = trace_volume_usage(scenario1, 2000)

    # Test 2: User selects only 500L checkbox
    print(f"\n" + "="*50)
    print("TEST 2: User selects only 500L checkbox")
    print(f"="*50)
    print("This simulates user unchecking 2000L and selecting only 500L")
    scenario2 = create_test_scenario([500], 500)
    result2 = trace_volume_usage(scenario2, 500)

    # Test 3: User selects multiple checkboxes (500L, 1000L, 5000L)
    print(f"\n" + "="*50)
    print("TEST 3: User selects multiple checkboxes")
    print(f"="*50)
    print("Volume options: [500, 1000, 5000], base should be first (500L)")
    scenario3 = create_test_scenario([500, 1000, 5000], 500)
    result3 = trace_volume_usage(scenario3, 500)

    # Test 4: Potential bug - base_fermenter_vol_l different from first volume option
    print(f"\n" + "="*50)
    print("TEST 4: Potential bug scenario")
    print(f"="*50)
    print("base_fermenter_vol_l=2000L but volume_options_l=[500, 1000]")
    print("This could happen if there's a bug in form collection")
    scenario4 = create_test_scenario([500, 1000], 2000)
    result4 = trace_volume_usage(scenario4, 2000)  # System should use base_fermenter_vol_l=2000

    # Test 5: Empty volume options (fallback case)
    print(f"\n" + "="*50)
    print("TEST 5: No checkboxes selected (fallback)")
    print(f"="*50)
    print("volume_options_l=[], base_fermenter_vol_l=2000L")
    print("This simulates user unchecking all boxes, should fall back to base field")
    scenario5 = create_test_scenario([], 2000)
    result5 = trace_volume_usage(scenario5, 2000)

    return [result1, result2, result3, result4, result5]

def test_optimization_scenarios():
    """Test how optimization handles volume options."""
    print(f"\n" + "="*60)
    print("TESTING OPTIMIZATION SCENARIOS")
    print("="*60)

    # Test 6: Optimization with single volume option
    print(f"\n" + "="*50)
    print("TEST 6: Optimization with single volume (500L)")
    print(f"="*50)
    scenario6 = create_test_scenario([500], 500)
    scenario6.optimize_equipment = True

    print("With optimization enabled, system should consider volume_options_l")
    try:
        result6 = run_scenario(scenario6)
        print(f"Optimization result:")
        if result6.optimization and result6.optimization.best_solution:
            best = result6.optimization.best_solution
            opt_volume = best.get('fermenter_volume_l', 'N/A')
            print(f"  Optimized fermenter volume: {opt_volume}L")
            print(f"  Final media tank volume: {result6.equipment.specifications.media_tank_volume_l}L")

            if opt_volume == 500:
                print(f"  ✓ Optimizer used the provided volume option")
            else:
                print(f"  ✗ Optimizer didn't use provided volume option")
        else:
            print(f"  ✗ Optimization failed")
    except Exception as e:
        print(f"Error in optimization test: {e}")

    # Test 7: Optimization with multiple volume options
    print(f"\n" + "="*50)
    print("TEST 7: Optimization with multiple volumes")
    print(f"="*50)
    scenario7 = create_test_scenario([500, 1000, 2000, 5000], 500)
    scenario7.optimize_equipment = True

    try:
        result7 = run_scenario(scenario7)
        print(f"Optimization with multiple options:")
        if result7.optimization and result7.optimization.best_solution:
            best = result7.optimization.best_solution
            opt_volume = best.get('fermenter_volume_l', 'N/A')
            print(f"  Optimized fermenter volume: {opt_volume}L")
            print(f"  Available options were: [500, 1000, 2000, 5000]L")

            if opt_volume in [500, 1000, 2000, 5000]:
                print(f"  ✓ Optimizer selected from provided options")
            else:
                print(f"  ✗ Optimizer selected volume NOT in options!")
        else:
            print(f"  ✗ Optimization failed")
    except Exception as e:
        print(f"Error in multi-volume optimization test: {e}")

def main():
    """Main debug function."""
    print("=" * 60)
    print("VOLUME OPTIONS DEBUG SCRIPT")
    print("=" * 60)
    print("Investigating: '2500L appears in results regardless of checkbox selection'")
    print("Hypothesis: 2500L is media tank volume from 2000L fermenter × 1.25 ratio")

    # Run comprehensive tests
    regular_results = test_checkbox_scenarios()
    test_optimization_scenarios()

    print(f"\n" + "="*60)
    print("SUMMARY AND DIAGNOSIS")
    print("="*60)

    print("Key Findings:")
    print("1. There are multiple volume variables with different purposes:")
    print("   - base_fermenter_vol_l: Used for non-optimization scenarios & equipment costing")
    print("   - volume_options_l: Used for optimization grid search")
    print("   - working_volume = fermenter_volume × working_volume_fraction (0.8)")
    print("   - media_tank_volume = fermenter_volume × media_tank_ratio (1.25)")

    print("\n2. In NON-OPTIMIZATION mode:")
    print("   - System uses base_fermenter_vol_l for all calculations")
    print("   - volume_options_l is ignored")
    print("   - If base_fermenter_vol_l = 2000L, then media_tank = 2500L")

    print("\n3. In OPTIMIZATION mode:")
    print("   - System should test all values in volume_options_l")
    print("   - Best solution should pick one of these volumes")

    print("\nPOSSIBLE ROOT CAUSES:")
    print("A. JavaScript form collection bug:")
    print("   - Checkboxes not properly setting base_fermenter_vol_l")
    print("   - base_fermenter_vol_l always defaults to 2000L input field")

    print("B. User confusion about volume types:")
    print("   - User sees 2500L media tank volume and thinks it's fermenter volume")
    print("   - Need to clarify what volumes are displayed in results")

    print("C. Optimization not enabled:")
    print("   - User expects volume options to work without optimization")
    print("   - But system only uses volume_options_l in optimization mode")

    print("\nNEXT INVESTIGATION STEPS:")
    print("1. Check JavaScript console logs during form submission")
    print("2. Verify what values are actually sent to API")
    print("3. Check if results display clearly labels volume types")
    print("4. Determine if volume options should work in non-optimization mode")

if __name__ == "__main__":
    main()
    print("Debugging complete.")
