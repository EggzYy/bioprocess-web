"""
Unit tests for bioprocess modules
"""

import unittest
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from bioprocess.models import (
    StrainInput,
    ScenarioInput,
    EquipmentConfig,
    VolumePlan,
    CapexConfig,
    OpexConfig,
    LaborConfig,
    PriceTables,
    EconomicAssumptions,
    OptimizationConfig,
    SensitivityConfig,
)
from bioprocess.capacity import (
    calculate_capacity_deterministic,
    calculate_capacity_monte_carlo,
)
from bioprocess.econ import (
    npv,
    irr,
    payback_period,
    calculate_depreciation,
    calculate_labor_cost,
)
from bioprocess.orchestrator import run_scenario


class TestStrainModels(unittest.TestCase):
    """Test strain input models and validation"""

    def setUp(self):
        self.valid_strain = StrainInput(
            name="Test Strain",
            fermentation_time_h=24.0,
            turnaround_time_h=9.0,
            downstream_time_h=4.0,
            yield_g_per_L=10.0,
            media_cost_usd=100.0,
            cryo_cost_usd=50.0,
            utility_rate_ferm_kw=300,
            utility_rate_cent_kw=15,
            utility_rate_lyo_kw=1.5,
            utility_cost_steam=0.0228,
            licensing_fixed_cost_usd=0,
            licensing_royalty_pct=0,
            cv_ferm=0.1,
            cv_turn=0.1,
            cv_down=0.1,
        )

    def test_strain_creation(self):
        """Test creating a valid strain"""
        self.assertEqual(self.valid_strain.name, "Test Strain")
        self.assertEqual(self.valid_strain.fermentation_time_h, 24.0)
        self.assertIsNotNone(self.valid_strain)

    def test_strain_validation(self):
        """Test strain validation rules"""
        # Test negative values should fail
        with self.assertRaises(Exception):
            StrainInput(
                name="Bad Strain",
                fermentation_time_h=-1,  # Invalid negative time
                turnaround_time_h=9.0,
                downstream_time_h=4.0,
                yield_g_per_L=10.0,
                media_cost_usd=100.0,
                cryo_cost_usd=50.0,
                utility_rate_ferm_kw=300,
                utility_rate_cent_kw=15,
                utility_rate_lyo_kw=1.5,
                utility_cost_steam=0.0228,
            )


class TestCapacityCalculations(unittest.TestCase):
    """Test capacity calculation functions"""

    def setUp(self):
        self.strains = [
            StrainInput(
                name="Strain1",
                fermentation_time_h=24.0,
                turnaround_time_h=9.0,
                downstream_time_h=4.0,
                yield_g_per_L=10.0,
                media_cost_usd=100.0,
                cryo_cost_usd=50.0,
                utility_rate_ferm_kw=300,
                utility_rate_cent_kw=15,
                utility_rate_lyo_kw=1.5,
                utility_cost_steam=0.0228,
            ),
            StrainInput(
                name="Strain2",
                fermentation_time_h=12.0,
                turnaround_time_h=6.0,
                downstream_time_h=3.0,
                yield_g_per_L=15.0,
                media_cost_usd=80.0,
                cryo_cost_usd=40.0,
                utility_rate_ferm_kw=200,
                utility_rate_cent_kw=10,
                utility_rate_lyo_kw=1.0,
                utility_cost_steam=0.02,
            ),
        ]

        self.equipment = EquipmentConfig(reactors_total=4, ds_lines_total=2)

    def test_deterministic_capacity(self):
        """Test deterministic capacity calculation"""
        batch_df, utilization_df, capacity_result = calculate_capacity_deterministic(
            self.strains, self.equipment, fermenter_volume_l=2000
        )

        self.assertIsNotNone(capacity_result)
        self.assertGreater(capacity_result.total_feasible_batches, 0)
        self.assertGreater(capacity_result.total_annual_kg, 0)
        self.assertIn(
            capacity_result.bottleneck, ["upstream", "downstream", "balanced"]
        )

    def test_monte_carlo_capacity(self):
        """Test Monte Carlo capacity calculation"""
        batch_df, stats_df, capacity_result = calculate_capacity_monte_carlo(
            self.strains,
            self.equipment,
            fermenter_volume_l=2000,
            n_samples=100,  # Small sample for testing
        )

        self.assertIsNotNone(capacity_result)
        self.assertIsNotNone(capacity_result.kg_p10)
        self.assertIsNotNone(capacity_result.kg_p50)
        self.assertIsNotNone(capacity_result.kg_p90)

        # Check that P10 <= P50 <= P90
        self.assertLessEqual(capacity_result.kg_p10, capacity_result.kg_p50)
        self.assertLessEqual(capacity_result.kg_p50, capacity_result.kg_p90)

    def test_capacity_with_zero_reactors(self):
        """Test capacity calculation with edge case"""
        # Pydantic validation prevents creating config with 0 reactors
        with self.assertRaises(Exception):
            equipment_zero = EquipmentConfig(
                reactors_total=0,  # This should fail validation
                ds_lines_total=1,
            )


class TestEconomicCalculations(unittest.TestCase):
    """Test economic calculation functions"""

    def test_npv_calculation(self):
        """Test NPV calculation"""
        cash_flows = [-1000000, 200000, 300000, 400000, 500000]
        discount_rate = 0.1

        npv_result = npv(discount_rate, cash_flows)

        # Manual calculation for verification
        expected = (
            -1000000 + 200000 / 1.1 + 300000 / 1.21 + 400000 / 1.331 + 500000 / 1.4641
        )
        self.assertAlmostEqual(npv_result, expected, places=2)

    def test_irr_calculation(self):
        """Test IRR calculation"""
        cash_flows = [-1000000, 300000, 400000, 500000, 600000]

        irr_result = irr(cash_flows)

        self.assertIsNotNone(irr_result)
        self.assertGreater(irr_result, 0)
        self.assertLess(irr_result, 1)  # IRR should be between 0 and 100%

        # Verify IRR makes NPV = 0
        npv_at_irr = npv(irr_result, cash_flows)
        self.assertAlmostEqual(npv_at_irr, 0, places=0)

    def test_payback_period(self):
        """Test payback period calculation"""
        cash_flows = [-1000000, 300000, 400000, 500000, 600000]

        payback = payback_period(cash_flows)

        self.assertIsNotNone(payback)
        self.assertGreater(payback, 0)
        self.assertLess(payback, len(cash_flows))

        # In this case, payback should be between year 2 and 3
        self.assertGreater(payback, 2)
        self.assertLess(payback, 3)

    def test_depreciation_straight_line(self):
        """Test straight-line depreciation"""
        initial_value = 1000000
        years = 10

        depreciation = calculate_depreciation(
            initial_value, years, method="straight_line"
        )

        self.assertEqual(len(depreciation), years)
        self.assertAlmostEqual(depreciation[0], initial_value / years)
        self.assertAlmostEqual(sum(depreciation), initial_value)

    def test_labor_cost_calculation(self):
        """Test labor cost calculation"""
        from bioprocess.models import LaborConfig

        labor_config = LaborConfig()
        target_tpa = 10.0

        total_cost, fte_count = calculate_labor_cost(labor_config, target_tpa)

        self.assertGreater(total_cost, 0)
        self.assertGreater(fte_count, 0)
        self.assertIsInstance(fte_count, int)


class TestScenarioOrchestration(unittest.TestCase):
    """Test end-to-end scenario orchestration"""

    def setUp(self):
        """Create a complete test scenario"""
        self.scenario = ScenarioInput(
            name="Test Scenario",
            target_tpa=10.0,
            strains=[
                StrainInput(
                    name="Test Strain",
                    fermentation_time_h=24.0,
                    turnaround_time_h=9.0,
                    downstream_time_h=4.0,
                    yield_g_per_L=10.0,
                    media_cost_usd=100.0,
                    cryo_cost_usd=50.0,
                    utility_rate_ferm_kw=300,
                    utility_rate_cent_kw=15,
                    utility_rate_lyo_kw=1.5,
                    utility_cost_steam=0.0228,
                )
            ],
            equipment=EquipmentConfig(reactors_total=4, ds_lines_total=2),
            volumes=VolumePlan(base_fermenter_vol_l=2000),
            capex=CapexConfig(),
            opex=OpexConfig(),
            labor=LaborConfig(),
            prices=PriceTables(
                raw_prices={"Glucose": 0.5}, product_prices={"default": 400}
            ),
            assumptions=EconomicAssumptions(),
            optimization=OptimizationConfig(enabled=False),
            sensitivity=SensitivityConfig(enabled=False),
            optimize_equipment=False,
        )

    def test_run_scenario(self):
        """Test running a complete scenario"""
        result = run_scenario(self.scenario)

        self.assertIsNotNone(result)
        self.assertEqual(result.scenario_name, "Test Scenario")
        self.assertIsNotNone(result.kpis)
        self.assertIsNotNone(result.capacity)
        self.assertIsNotNone(result.economics)
        self.assertIsNotNone(result.equipment)

        # Check KPIs
        self.assertIn("npv", result.kpis)
        self.assertIn("irr", result.kpis)
        self.assertIn("payback_years", result.kpis)
        self.assertIn("tpa", result.kpis)

        # Verify capacity meets minimum requirements
        self.assertGreater(result.capacity.total_annual_kg, 0)

        # Check for errors
        self.assertEqual(len(result.errors), 0)

    def test_scenario_with_multiple_strains(self):
        """Test scenario with multiple strains"""
        self.scenario.strains.append(
            StrainInput(
                name="Second Strain",
                fermentation_time_h=12.0,
                turnaround_time_h=6.0,
                downstream_time_h=3.0,
                yield_g_per_L=15.0,
                media_cost_usd=80.0,
                cryo_cost_usd=40.0,
                utility_rate_ferm_kw=200,
                utility_rate_cent_kw=10,
                utility_rate_lyo_kw=1.0,
                utility_cost_steam=0.02,
            )
        )

        result = run_scenario(self.scenario)

        self.assertIsNotNone(result)
        self.assertEqual(len(result.capacity.per_strain), 2)

        # Check that both strains have production
        for strain_result in result.capacity.per_strain:
            # Check for either annual_kg or annual_kg_good key
            annual_kg = strain_result.get(
                "annual_kg_good", strain_result.get("annual_kg", 0)
            )
            self.assertGreater(annual_kg, 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_negative_cash_flows_only(self):
        """Test IRR with only negative cash flows"""
        cash_flows = [-1000, -500, -300, -200]
        irr_result = irr(cash_flows)
        # Should return None or a special value for no positive return
        self.assertTrue(
            irr_result is None or irr_result < -0.99 or not np.isfinite(irr_result)
        )

    def test_zero_discount_rate(self):
        """Test NPV with zero discount rate"""
        cash_flows = [-1000, 500, 500, 500]
        npv_result = npv(0, cash_flows)
        self.assertEqual(npv_result, sum(cash_flows))

    def test_very_high_utilization(self):
        """Test capacity with very high utilization"""
        strains = [
            StrainInput(
                name="Fast Strain",
                fermentation_time_h=1.0,  # Very fast
                turnaround_time_h=0.5,
                downstream_time_h=0.5,
                yield_g_per_L=100.0,  # Very high yield
                media_cost_usd=10.0,
                cryo_cost_usd=5.0,
                utility_rate_ferm_kw=50,
                utility_rate_cent_kw=5,
                utility_rate_lyo_kw=0.5,
                utility_cost_steam=0.01,
            )
        ]

        equipment = EquipmentConfig(
            reactors_total=1,  # Minimal equipment
            ds_lines_total=1,
        )

        batch_df, utilization_df, capacity_result = calculate_capacity_deterministic(
            strains,
            equipment,
            fermenter_volume_l=10000,  # Large volume
        )

        # Should still work but show high utilization
        self.assertIsNotNone(capacity_result)
        self.assertGreaterEqual(capacity_result.weighted_up_utilization, 0.9)


class TestDataValidation(unittest.TestCase):
    """Test data validation and type checking"""

    def test_price_tables_validation(self):
        """Test price table validation"""
        # Empty raw prices should fail
        with self.assertRaises(Exception):
            PriceTables(
                raw_prices={},  # Empty dict should fail validation
                product_prices={"test": 100},
            )

        # Negative prices should fail
        with self.assertRaises(Exception):
            PriceTables(
                raw_prices={"Glucose": -1},  # Negative price
                product_prices={"test": 100},
            )

    def test_equipment_config_validation(self):
        """Test equipment configuration validation"""
        # Valid configuration
        config = EquipmentConfig(
            reactors_total=4,
            ds_lines_total=2,
            upstream_availability=0.92,
            downstream_availability=0.90,
        )
        self.assertEqual(config.reactors_total, 4)

        # Invalid availability > 1
        with self.assertRaises(Exception):
            EquipmentConfig(
                reactors_total=4,
                ds_lines_total=2,
                upstream_availability=1.5,  # Invalid > 1
            )


if __name__ == "__main__":
    unittest.main()
