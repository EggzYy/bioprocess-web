"""
Unit tests for edge cases in bioprocess calculations.
"""

import unittest
from pathlib import Path
import math

# Import the bioprocess modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioprocess.models import ScenarioInput
from bioprocess.orchestrator import run_scenario
from bioprocess.econ import npv, irr, payback_period
from bioprocess.sizing import calculate_capex_estimate_original


class TestEconomicEdgeCases(unittest.TestCase):
    """Test edge cases in economic calculations."""

    def test_npv_with_zero_discount(self):
        """Test NPV calculation with zero discount rate."""
        cash_flows = [-1000, 400, 400, 400]
        result = npv(0.0, cash_flows)
        self.assertEqual(result, 700.0)

    def test_npv_with_all_negative(self):
        """Test NPV with all negative cash flows."""
        cash_flows = [-1000, -500, -200]
        result = npv(0.1, cash_flows)
        self.assertLess(result, 0)

    def test_npv_with_all_positive(self):
        """Test NPV with all positive cash flows."""
        cash_flows = [100, 200, 300]
        result = npv(0.1, cash_flows)
        self.assertGreater(result, 0)

    def test_irr_undefined_no_negative(self):
        """Test IRR when there are no negative cash flows."""
        cash_flows = [100, 200, 300]
        result = irr(cash_flows)
        self.assertTrue(math.isnan(result))

    def test_irr_undefined_no_positive(self):
        """Test IRR when there are no positive cash flows."""
        cash_flows = [-100, -200, -300]
        result = irr(cash_flows)
        self.assertTrue(math.isnan(result))

    def test_irr_convergence(self):
        """Test IRR convergence for typical investment."""
        # Typical investment: -1000 initial, positive returns
        cash_flows = [-1000, 400, 400, 400, 400]
        result = irr(cash_flows)
        # IRR should be around 0.347 (34.7%)
        self.assertGreater(result, 0.3)
        self.assertLess(result, 0.4)

    def test_payback_immediate(self):
        """Test payback with immediate return."""
        cash_flows = [-100, 200, 100]
        result = payback_period(cash_flows)
        self.assertEqual(result, 0.0)

    def test_payback_never(self):
        """Test payback when it never pays back."""
        cash_flows = [-1000, 100, 100, 100]
        result = payback_period(cash_flows)
        self.assertEqual(result, 999.0)  # Large number for never

    def test_payback_exact(self):
        """Test payback at exact year boundary."""
        cash_flows = [-1000, 0, 0, 1200]
        result = payback_period(cash_flows)
        self.assertAlmostEqual(result, 3.0, places=1)


class TestCapacityEdgeCases(unittest.TestCase):
    """Test edge cases in capacity calculations."""

    def test_zero_target_tpa(self):
        """Test scenario with zero target TPA."""
        scenario = ScenarioInput(
            name="Zero Target Test",
            target_tpa=0.0,
            strains=[
                {
                    "name": "Test Strain",
                    "fermentation_time_h": 24.0,
                    "turnaround_time_h": 9.0,
                    "downstream_time_h": 4.0,
                    "yield_g_per_L": 10.0,
                    "media_cost_usd": 100.0,
                    "cryo_cost_usd": 50.0,
                    "utility_rate_ferm_kw": 300,
                    "utility_rate_cent_kw": 15,
                    "utility_rate_lyo_kw": 1.5,
                    "utility_cost_steam": 0.0228,
                    "licensing_fixed_cost_usd": 0,
                    "licensing_royalty_pct": 0,
                    "cv_ferm": 0.1,
                    "cv_turn": 0.1,
                    "cv_down": 0.1,
                }
            ],
            equipment={"reactors_total": 1, "ds_lines_total": 1},
            volumes={"base_fermenter_vol_l": 1000},
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
        )

        # Should not raise an exception
        result = run_scenario(scenario, optimize=False)
        self.assertIsNotNone(result)

    def test_single_fermenter(self):
        """Test with single fermenter."""
        scenario = ScenarioInput(
            name="Single Fermenter Test",
            target_tpa=1.0,
            strains=[
                {
                    "name": "Test Strain",
                    "fermentation_time_h": 48.0,
                    "turnaround_time_h": 12.0,
                    "downstream_time_h": 6.0,
                    "yield_g_per_L": 5.0,
                    "media_cost_usd": 100.0,
                    "cryo_cost_usd": 50.0,
                    "utility_rate_ferm_kw": 200,
                    "utility_rate_cent_kw": 10,
                    "utility_rate_lyo_kw": 1.0,
                    "utility_cost_steam": 0.0228,
                    "licensing_fixed_cost_usd": 0,
                    "licensing_royalty_pct": 0,
                    "cv_ferm": 0.1,
                    "cv_turn": 0.1,
                    "cv_down": 0.1,
                }
            ],
            equipment={"reactors_total": 1, "ds_lines_total": 1},
            volumes={"base_fermenter_vol_l": 500},
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
        )

        result = run_scenario(scenario, optimize=False)
        self.assertIsNotNone(result)
        self.assertGreater(result.kpis.get("tpa", 0), 0)

    def test_very_large_target(self):
        """Test with very large target TPA."""
        scenario = ScenarioInput(
            name="Large Target Test",
            target_tpa=1000.0,
            strains=[
                {
                    "name": "Test Strain",
                    "fermentation_time_h": 24.0,
                    "turnaround_time_h": 9.0,
                    "downstream_time_h": 4.0,
                    "yield_g_per_L": 10.0,
                    "media_cost_usd": 100.0,
                    "cryo_cost_usd": 50.0,
                    "utility_rate_ferm_kw": 300,
                    "utility_rate_cent_kw": 15,
                    "utility_rate_lyo_kw": 1.5,
                    "utility_cost_steam": 0.0228,
                    "licensing_fixed_cost_usd": 0,
                    "licensing_royalty_pct": 0,
                    "cv_ferm": 0.1,
                    "cv_turn": 0.1,
                    "cv_down": 0.1,
                }
            ],
            equipment={"reactors_total": 20, "ds_lines_total": 10},
            volumes={"base_fermenter_vol_l": 20000},
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
        )

        result = run_scenario(scenario, optimize=False)
        self.assertIsNotNone(result)


class TestSizingEdgeCases(unittest.TestCase):
    """Test edge cases in equipment sizing."""

    def test_zero_fermenters(self):
        """Test sizing with zero fermenters."""
        total_capex, breakdown = calculate_capex_estimate_original(
            target_tpa=10.0,
            fermenters=0,
            ds_lines=1,
            fermenter_volume_l=2000,
        )
        # Should handle gracefully
        self.assertGreaterEqual(total_capex, 0)

    def test_zero_volume(self):
        """Test sizing with zero volume."""
        total_capex, breakdown = calculate_capex_estimate_original(
            target_tpa=10.0,
            fermenters=4,
            ds_lines=2,
            fermenter_volume_l=0,
        )
        # Should handle gracefully
        self.assertGreaterEqual(total_capex, 0)

    def test_large_scale(self):
        """Test sizing with large scale."""
        total_capex, breakdown = calculate_capex_estimate_original(
            target_tpa=1000.0,
            fermenters=50,
            ds_lines=20,
            fermenter_volume_l=50000,
        )
        # Should produce reasonable results
        self.assertGreater(total_capex, 0)
        self.assertIn("equip", breakdown)


class TestValidationEdgeCases(unittest.TestCase):
    """Test edge cases in input validation."""

    def test_very_long_name(self):
        """Test scenario with very long name."""
        long_name = "A" * 500  # 500 character name
        scenario = ScenarioInput(
            name=long_name,
            target_tpa=10.0,
            strains=[
                {
                    "name": "Test Strain",
                    "fermentation_time_h": 24.0,
                    "turnaround_time_h": 9.0,
                    "downstream_time_h": 4.0,
                    "yield_g_per_L": 10.0,
                    "media_cost_usd": 100.0,
                    "cryo_cost_usd": 50.0,
                    "utility_rate_ferm_kw": 300,
                    "utility_rate_cent_kw": 15,
                    "utility_rate_lyo_kw": 1.5,
                    "utility_cost_steam": 0.0228,
                    "licensing_fixed_cost_usd": 0,
                    "licensing_royalty_pct": 0,
                    "cv_ferm": 0.1,
                    "cv_turn": 0.1,
                    "cv_down": 0.1,
                }
            ],
            equipment={"reactors_total": 4, "ds_lines_total": 2},
            volumes={"base_fermenter_vol_l": 2000},
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
        )

        # Should handle gracefully (Pydantic will truncate)
        self.assertLessEqual(len(scenario.name), 200)

    def test_special_characters_in_strain_name(self):
        """Test with special characters in strain name."""
        scenario = ScenarioInput(
            name="Special Characters Test",
            target_tpa=10.0,
            strains=[
                {
                    "name": "Test_Strain-Variant.1",
                    "fermentation_time_h": 24.0,
                    "turnaround_time_h": 9.0,
                    "downstream_time_h": 4.0,
                    "yield_g_per_L": 10.0,
                    "media_cost_usd": 100.0,
                    "cryo_cost_usd": 50.0,
                    "utility_rate_ferm_kw": 300,
                    "utility_rate_cent_kw": 15,
                    "utility_rate_lyo_kw": 1.5,
                    "utility_cost_steam": 0.0228,
                    "licensing_fixed_cost_usd": 0,
                    "licensing_royalty_pct": 0,
                    "cv_ferm": 0.1,
                    "cv_turn": 0.1,
                    "cv_down": 0.1,
                }
            ],
            equipment={"reactors_total": 4, "ds_lines_total": 2},
            volumes={"base_fermenter_vol_l": 2000},
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
        )

        result = run_scenario(scenario, optimize=False)
        self.assertIsNotNone(result)


class TestOptimizationEdgeCases(unittest.TestCase):
    """Test edge cases in optimization."""

    def test_impossible_target(self):
        """Test optimization with impossible target."""
        scenario = ScenarioInput(
            name="Impossible Target Test",
            target_tpa=10000.0,  # Very high target
            strains=[
                {
                    "name": "Test Strain",
                    "fermentation_time_h": 48.0,
                    "turnaround_time_h": 24.0,
                    "downstream_time_h": 12.0,
                    "yield_g_per_L": 2.0,  # Low yield
                    "media_cost_usd": 100.0,
                    "cryo_cost_usd": 50.0,
                    "utility_rate_ferm_kw": 100,
                    "utility_rate_cent_kw": 5,
                    "utility_rate_lyo_kw": 0.5,
                    "utility_cost_steam": 0.0228,
                    "licensing_fixed_cost_usd": 0,
                    "licensing_royalty_pct": 0,
                    "cv_ferm": 0.1,
                    "cv_turn": 0.1,
                    "cv_down": 0.1,
                }
            ],
            equipment={"reactors_total": 2, "ds_lines_total": 1},
            volumes={"base_fermenter_vol_l": 500},
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
            optimize_equipment=True,
        )

        # Should return a result (best effort) rather than crash
        result = run_scenario(scenario, optimize=True)
        self.assertIsNotNone(result)
        # Should have a warning about target not reachable
        self.assertTrue(
            any("warning" in str(w).lower() or "target" in str(w).lower()
                for w in result.warnings)
            or result.errors
        )


if __name__ == "__main__":
    unittest.main()
