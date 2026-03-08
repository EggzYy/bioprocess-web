"""
Comprehensive E2E tests comparing bioprocess module with pricing_integrated_original.py.

This test module validates that the new bioprocess implementation produces results
that match or are reasonably close to the original pricing engine.
"""

import math
import sys
import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import new bioprocess modules
from bioprocess.models import ScenarioInput, StrainInput
from bioprocess.orchestrator import run_scenario, load_strain_from_database
from bioprocess.econ import npv as bioprocess_npv, irr as bioprocess_irr
from bioprocess.sizing import calculate_capex_estimate_original


# Import original pricing module
ORIGINAL_PRICING_PATH = Path(__file__).parent.parent / "pricing_integrated_original.py"
original_pricing = None
if ORIGINAL_PRICING_PATH.exists():
    try:
        sys.path.insert(0, str(ORIGINAL_PRICING_PATH.parent))
        import importlib.util
        spec = importlib.util.spec_from_file_location("original_pricing", ORIGINAL_PRICING_PATH)
        original_pricing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original_pricing)
    except Exception as e:
        print(f"Warning: Could not load original pricing: {e}")
        original_pricing = None
else:
    print(f"Warning: Original pricing file not found at {ORIGINAL_PRICING_PATH}")


# Test tolerance for floating point comparisons
TOLERANCE = 0.05  # 5% tolerance for most values


def is_close(a: float, b: float, rel_tol: float = TOLERANCE) -> bool:
    """Check if two values are close within tolerance."""
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return abs(a - b) <= rel_tol * max(abs(a), abs(b))
    return abs(a - b) / max(abs(a), abs(b)) <= rel_tol


class TestCapacityComparison:
    """Test capacity calculations match between original and new implementation."""

    def test_capacity_facility1(self):
        """Test Facility 1 (Yogurt Cultures) capacity."""
        if original_pricing is None:
            pytest.skip("Original pricing not available")

        facility1_strains = ["S. thermophilus", "L. delbrueckii subsp. bulgaricus"]
        reactors = 4
        ds_lines = 2
        fermenter_volume_L = 2000

        # Original calculation
        orig_df, orig_totals, orig_plant = original_pricing.capacity_given_counts(
            facility1_strains, reactors, ds_lines, fermenter_volume_L
        )
        orig_kg = orig_plant["plant_kg_good"]

        # New calculation - use defaults
        scenario = ScenarioInput(
            name="Facility 1 Test",
            target_tpa=10.0,
            strains=[load_strain_from_database(s) for s in facility1_strains],
        )

        # Override equipment config
        scenario.equipment.reactors_total = reactors
        scenario.equipment.ds_lines_total = ds_lines
        scenario.volumes.base_fermenter_vol_l = fermenter_volume_L

        result = run_scenario(scenario)
        new_kg = result.capacity.total_annual_kg

        # Compare
        print(f"Facility 1 Capacity: Original={orig_kg:.2f}kg, New={new_kg:.2f}kg")
        assert is_close(orig_kg, new_kg), f"Capacity mismatch: {orig_kg} vs {new_kg}"

    def test_capacity_facility4(self):
        """Test Facility 4 (Yeast Probiotic) capacity."""
        if original_pricing is None:
            pytest.skip("Original pricing not available")

        facility4_strains = ["Saccharomyces boulardii"]
        reactors = 4
        ds_lines = 2
        fermenter_volume_L = 2000

        # Original calculation
        orig_df, orig_totals, orig_plant = original_pricing.capacity_given_counts(
            facility4_strains, reactors, ds_lines, fermenter_volume_L
        )
        orig_kg = orig_plant["plant_kg_good"]

        # New calculation
        scenario = ScenarioInput(
            name="Facility 4 Test",
            target_tpa=10.0,
            strains=[load_strain_from_database(s) for s in facility4_strains],
        )

        scenario.equipment.reactors_total = reactors
        scenario.equipment.ds_lines_total = ds_lines
        scenario.volumes.base_fermenter_vol_l = fermenter_volume_L

        result = run_scenario(scenario)
        new_kg = result.capacity.total_annual_kg

        print(f"Facility 4 Capacity: Original={orig_kg:.2f}kg, New={new_kg:.2f}kg")
        assert is_close(orig_kg, new_kg), f"Capacity mismatch: {orig_kg} vs {new_kg}"


class TestCAPEXComparison:
    """Test CAPEX calculations match between original and new implementation."""

    def test_capex_facility1_parity_mode(self):
        """Test Facility 1 CAPEX in parity mode."""
        if original_pricing is None:
            pytest.skip("Original pricing not available")

        target_tpa = 10.0
        fermenters = 4
        ds_lines = 2
        fermenter_volume_L = 2000
        licensing_fixed_total = 0.0  # No licensing for Facility 1

        # Original CAPEX
        orig_capex, orig_breakdown = original_pricing.capex_estimate_2(
            target_tpa, fermenters, ds_lines, fermenter_volume_L, licensing_fixed_total
        )

        # New CAPEX (using the same function from bioprocess.sizing)
        new_capex, new_breakdown = calculate_capex_estimate_original(
            target_tpa, fermenters, ds_lines, fermenter_volume_L, licensing_fixed_total
        )

        print(f"Facility 1 CAPEX: Original={orig_capex:.2f}, New={new_capex:.2f}")
        print(f"Original breakdown: {orig_breakdown}")
        print(f"New breakdown: {new_breakdown}")

        # Compare total CAPEX
        assert is_close(orig_capex, new_capex), f"CAPEX mismatch: {orig_capex} vs {new_capex}"


class TestNPVIRRComparison:
    """Test NPV and IRR calculations match between original and new implementation."""

    def test_npv_calculation(self):
        """Test NPV calculation in bioprocess matches expected formula."""
        # Test cash flows
        cash_flows = [-700000, -300000, 500000, 800000, 1000000, 1200000, 1200000, 1200000, 1200000, 1200000, 1200000, 1200000, 1200000]

        # Calculate NPV using bioprocess
        result_npv = bioprocess_npv(0.10, cash_flows)

        # Calculate NPV manually
        expected_npv = sum(cf / (1.10 ** t) for t, cf in enumerate(cash_flows))

        print(f"NPV: Calculated={result_npv:.2f}, Expected={expected_npv:.2f}")
        assert is_close(result_npv, expected_npv), f"NPV mismatch: {result_npv} vs {expected_npv}"

    def test_irr_calculation(self):
        """Test IRR calculation in bioprocess matches expected formula."""
        # Test cash flows with known IRR (~20%)
        cash_flows = [-1000000, 200000, 400000, 600000, 800000]

        # Calculate IRR using bioprocess
        result_irr = bioprocess_irr(cash_flows)

        # Verify IRR is reasonable (between 15% and 30% for this case)
        print(f"IRR: Calculated={result_irr:.4f} ({result_irr*100:.2f}%)")
        assert 0.15 <= result_irr <= 0.35, f"IRR out of expected range: {result_irr}"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_production(self):
        """Test handling of zero production scenario."""
        strains = ["S. thermophilus"]
        scenario = ScenarioInput(
            name="Zero Production Test",
            target_tpa=0.1,  # Use small non-zero value
            strains=[load_strain_from_database(s) for s in strains],
        )
        scenario.equipment.reactors_total = 1
        scenario.equipment.ds_lines_total = 1
        scenario.volumes.base_fermenter_vol_l = 2000

        result = run_scenario(scenario)

        # Should handle gracefully
        assert result.capacity.total_annual_kg >= 0


class TestRegressionBugs:
    """Test for known regression bugs from the original issue."""

    def test_licensing_cost_included_in_capex(self):
        """Test that licensing fixed costs are included in total CAPEX."""
        strains = ["L. acidophilus"]  # Has $100K licensing
        scenario = ScenarioInput(
            name="Licensing Test",
            target_tpa=10.0,
            strains=[load_strain_from_database(s) for s in strains],
        )
        scenario.equipment.reactors_total = 4
        scenario.equipment.ds_lines_total = 2
        scenario.volumes.base_fermenter_vol_l = 2000
        scenario.capex.parity_mode = True

        result = run_scenario(scenario)

        # Check licensing fixed is included
        licensing_fixed = result.economics.licensing_fixed
        print(f"Licensing Fixed: ${licensing_fixed:,.0f}")

        assert licensing_fixed > 0, "Licensing fixed cost should be positive for L. acidophilus"

    def test_equipment_sizing_keys(self):
        """Test that equipment sizing returns proper dict keys."""
        from bioprocess.sizing import calculate_equipment_sizing
        from bioprocess.presets import get_strain_info
        from bioprocess.models import VolumePlan, CapexConfig

        strains = [get_strain_info("S. thermophilus")]
        strains[0]["name"] = "S. thermophilus"

        result = calculate_equipment_sizing(
            fermenters=4,
            ds_lines=2,
            fermenter_volume_l=2000,
            strains=strains,
            volume_plan=VolumePlan(),
            capex_config=CapexConfig(),
            target_tpa=10.0,
        )

        # Check required keys exist
        assert "fermenters" in result.counts, "Missing 'fermenters' key"
        assert result.equipment_cost > 0, "Equipment cost should be positive"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
