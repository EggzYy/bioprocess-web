"""
Integration tests for Excel export functionality.
"""

import unittest
import io
from pathlib import Path

# Import the bioprocess modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bioprocess.orchestrator import run_scenario, generate_excel_report
from bioprocess.models import ScenarioInput


class TestExcelExport(unittest.TestCase):
    """Test Excel export functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal scenario for testing
        self.test_scenario = ScenarioInput(
            name="Excel Export Test",
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

    def test_excel_export_creates_valid_file(self):
        """Test that Excel export creates a valid file."""
        # Run the scenario
        result = run_scenario(self.test_scenario, optimize=False)

        # Generate Excel report
        excel_bytes = generate_excel_report(result, self.test_scenario)

        # Check that we got bytes back
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)

        # Check that it's a valid ZIP file (XLSX is a ZIP)
        # ZIP file signature is 0x50 0x4B (PK)
        self.assertEqual(excel_bytes[0:2], b'PK')

    def test_excel_export_with_empty_result(self):
        """Test Excel export with minimal/empty result."""
        from bioprocess.models import (
            ScenarioResult,
            CapacityResult,
            EquipmentResult,
            EconomicsResult,
        )

        # Create minimal result
        result = ScenarioResult(
            scenario_name="Empty Test",
            timestamp="2024-01-01T00:00:00",
            kpis={},
            capacity=CapacityResult(
                per_strain=[],
                total_feasible_batches=0,
                total_good_batches=0,
                total_annual_kg=0,
                weighted_up_utilization=0,
                weighted_ds_utilization=0,
                bottleneck="balanced",
            ),
            equipment=EquipmentResult(
                counts={},
                specifications={},
                equipment_cost=0,
                installation_cost=0,
                utilities_cost=0,
                total_installed_cost=0,
            ),
            economics=EconomicsResult(
                annual_revenue=0,
                raw_materials_cost=0,
                utilities_cost=0,
                labor_cost=0,
                maintenance_cost=0,
                ga_other_cost=0,
                total_opex=0,
                land_cost=0,
                building_cost=0,
                equipment_cost=0,
                contingency=0,
                working_capital=0,
                total_capex=0,
                npv=0,
                irr=0,
                payback_years=float("inf"),
                ebitda_margin=0,
                cash_flows=[],
                licensing_fixed=0,
                licensing_royalty_rate=0,
            ),
            warnings=[],
            errors=[],
            calculation_time_s=0,
        )

        # Generate Excel - should not raise an exception
        excel_bytes = generate_excel_report(result)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)

    def test_excel_export_with_optimization(self):
        """Test Excel export with optimization enabled."""
        # Enable optimization
        scenario = ScenarioInput(
            name="Optimization Test",
            target_tpa=50.0,
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
            volumes={
                "base_fermenter_vol_l": 2000,
                "volume_options_l": [1000, 2000, 5000],
            },
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
            optimize_equipment=True,
        )

        result = run_scenario(scenario, optimize=True)
        excel_bytes = generate_excel_report(result, scenario)

        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)


class TestExcelExportEdgeCases(unittest.TestCase):
    """Test edge cases for Excel export."""

    def test_large_scenario(self):
        """Test Excel export with many strains."""
        strains = []
        for i in range(10):
            strains.append({
                "name": f"Strain {i}",
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
            })

        scenario = ScenarioInput(
            name="Multi-Strain Test",
            target_tpa=100.0,
            strains=strains,
            equipment={"reactors_total": 8, "ds_lines_total": 4},
            volumes={"base_fermenter_vol_l": 5000},
            prices={
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
        )

        result = run_scenario(scenario, optimize=False)
        excel_bytes = generate_excel_report(result, scenario)

        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)

    def test_zero_production(self):
        """Test with zero production scenario."""
        scenario = ScenarioInput(
            name="Zero Production Test",
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

        result = run_scenario(scenario, optimize=False)
        excel_bytes = generate_excel_report(result, scenario)

        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)


if __name__ == "__main__":
    unittest.main()
