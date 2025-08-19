"""
API Integration Tests
"""

import unittest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from api.main import app


class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints"""

    def setUp(self):
        self.client = TestClient(app)
        self.test_scenario = {
            "name": "API Test Scenario",
            "target_tpa": 10.0,
            "strains": [
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
                }
            ],
            "equipment": {"reactors_total": 4, "ds_lines_total": 2},
            "volumes": {"base_fermenter_vol_l": 2000},
            "prices": {
                "raw_prices": {"Glucose": 0.5},
                "product_prices": {"default": 400},
            },
        }

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("version", data)

    def test_get_defaults(self):
        """Test getting default assumptions"""
        response = self.client.get("/api/defaults")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("assumptions", data)
        self.assertIn("available_volumes", data)

    def test_get_strains(self):
        """Test getting strain database"""
        response = self.client.get("/api/strains")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("strains", data)
        self.assertIn("count", data)
        self.assertIsInstance(data["strains"], list)

    def test_run_scenario_sync(self):
        """Test running scenario synchronously"""
        response = self.client.post(
            "/api/scenarios/run",
            json={"scenario": self.test_scenario, "async_mode": False},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertIn("result", data)

        result = data["result"]
        self.assertIn("kpis", result)
        self.assertIn("capacity", result)
        self.assertIn("economics", result)

    def test_run_scenario_async(self):
        """Test running scenario asynchronously"""
        response = self.client.post(
            "/api/scenarios/run",
            json={"scenario": self.test_scenario, "async_mode": True},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "pending")
        self.assertIn("job_id", data)

        # Test getting job status
        job_id = data["job_id"]
        status_response = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.json()
        self.assertIn("status", status_data)
        self.assertIn("progress", status_data)

    def test_invalid_scenario(self):
        """Test with invalid scenario data"""
        invalid_scenario = {
            "name": "Invalid",
            "target_tpa": -10,  # Invalid negative value
            "strains": [],  # Empty strains
        }

        response = self.client.post(
            "/api/scenarios/run",
            json={"scenario": invalid_scenario, "async_mode": False},
        )
        # Should return error
        self.assertIn(response.status_code, [400, 422, 500])

    def test_config_save_and_load(self):
        """Test saving and loading configurations"""
        # Save configuration
        save_response = self.client.post(
            "/api/configs/save",
            json={
                "name": "test_config",
                "description": "Test configuration",
                "scenario": self.test_scenario,
                "overwrite": True,
            },
        )
        self.assertEqual(save_response.status_code, 200)
        save_data = save_response.json()
        self.assertEqual(save_data["name"], "test_config")

        # List configurations
        list_response = self.client.get("/api/configs")
        self.assertEqual(list_response.status_code, 200)
        list_data = list_response.json()
        self.assertIn("configs", list_data)
        self.assertGreater(list_data["count"], 0)

        # Load configuration
        load_response = self.client.get("/api/configs/test_config")
        self.assertEqual(load_response.status_code, 200)
        load_data = load_response.json()
        self.assertEqual(load_data["name"], "test_config")

        # Delete configuration
        delete_response = self.client.delete("/api/configs/test_config")
        self.assertEqual(delete_response.status_code, 200)

    def test_batch_scenarios(self):
        """Test batch scenario processing"""
        scenarios = [self.test_scenario, self.test_scenario]

        response = self.client.post(
            "/api/scenarios/batch", json={"scenarios": scenarios}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_scenarios"], 2)
        self.assertIn("job_id", data)

    def test_export_excel(self):
        """Test Excel export endpoint"""
        # First run a scenario to get results
        run_response = self.client.post(
            "/api/scenarios/run",
            json={"scenario": self.test_scenario, "async_mode": False},
        )
        self.assertEqual(run_response.status_code, 200)
        result = run_response.json()["result"]

        # Export to Excel - include the scenario input for proper validation
        export_response = self.client.post(
            "/api/export/excel",
            json={
                "scenario_name": "test_export",
                "result": result,
                "scenario_input": self.test_scenario,  # Include the full scenario
            },
        )
        self.assertEqual(export_response.status_code, 200)
        export_data = export_response.json()
        self.assertIn("filename", export_data)
        self.assertIn("download_url", export_data)

    def test_sensitivity_analysis(self):
        """Test sensitivity analysis endpoint"""
        response = self.client.post(
            "/api/sensitivity/run",
            json={
                "scenario": self.test_scenario,
                "base_configuration": {
                    "reactors": 4,
                    "ds_lines": 2,
                    "fermenter_volume_l": 2000,
                },
                "parameters": ["discount_rate", "tax_rate"],
                "delta_percentage": 0.1,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "pending")

    def test_job_cancellation(self):
        """Test job cancellation"""
        # Start an async job
        response = self.client.post(
            "/api/scenarios/run",
            json={"scenario": self.test_scenario, "async_mode": True},
        )
        job_id = response.json()["job_id"]

        # Try to cancel the job (it might already be completed)
        cancel_response = self.client.delete(f"/api/jobs/{job_id}")

        # Check job status
        status_response = self.client.get(f"/api/jobs/{job_id}")
        status_data = status_response.json()

        # Job should be either cancelled or already completed
        if cancel_response.status_code == 200:
            self.assertEqual(status_data["status"], "cancelled")
        else:
            # Job was already completed or failed
            self.assertIn(status_data["status"], ["completed", "failed"])


class TestAPIValidation(unittest.TestCase):
    """Test API input validation"""

    def setUp(self):
        self.client = TestClient(app)

    def test_strain_validation(self):
        """Test strain input validation"""
        invalid_strain = {
            "name": "Bad Strain",
            "fermentation_time_h": -1,  # Invalid
            "turnaround_time_h": 9.0,
            "downstream_time_h": 4.0,
            "yield_g_per_L": 10.0,
            "media_cost_usd": 100.0,
            "cryo_cost_usd": 50.0,
            "utility_rate_ferm_kw": 300,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "utility_cost_steam": 0.0228,
        }

        scenario = {
            "name": "Invalid Test",
            "target_tpa": 10.0,
            "strains": [invalid_strain],
            "equipment": {"reactors_total": 4, "ds_lines_total": 2},
            "volumes": {"base_fermenter_vol_l": 2000},
            "prices": {"raw_prices": {"G": 0.5}, "product_prices": {}},
        }

        response = self.client.post(
            "/api/scenarios/run", json={"scenario": scenario, "async_mode": False}
        )
        self.assertIn(response.status_code, [400, 422])

    def test_equipment_validation(self):
        """Test equipment configuration validation"""
        scenario = {
            "name": "Equipment Test",
            "target_tpa": 10.0,
            "strains": [
                {
                    "name": "Test",
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
                }
            ],
            "equipment": {
                "reactors_total": -1,  # Invalid negative
                "ds_lines_total": 2,
            },
            "volumes": {"base_fermenter_vol_l": 2000},
            "prices": {"raw_prices": {"G": 0.5}, "product_prices": {}},
        }

        response = self.client.post(
            "/api/scenarios/run", json={"scenario": scenario, "async_mode": False}
        )
        self.assertIn(response.status_code, [400, 422])


class TestAPIPerformance(unittest.TestCase):
    """Test API performance and limits"""

    def setUp(self):
        self.client = TestClient(app)

    def test_large_batch_processing(self):
        """Test processing large batch of scenarios"""
        base_scenario = {
            "name": "Batch Test",
            "target_tpa": 10.0,
            "strains": [
                {
                    "name": "Test",
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
                }
            ],
            "equipment": {"reactors_total": 4, "ds_lines_total": 2},
            "volumes": {"base_fermenter_vol_l": 2000},
            "prices": {"raw_prices": {"G": 0.5}, "product_prices": {}},
        }

        # Create 10 scenarios
        scenarios = [base_scenario.copy() for _ in range(10)]

        response = self.client.post(
            "/api/scenarios/batch", json={"scenarios": scenarios}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_scenarios"], 10)

    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        scenario = {
            "name": "Concurrent Test",
            "target_tpa": 10.0,
            "strains": [
                {
                    "name": "Test",
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
                }
            ],
            "equipment": {"reactors_total": 4, "ds_lines_total": 2},
            "volumes": {"base_fermenter_vol_l": 2000},
            "prices": {"raw_prices": {"G": 0.5}, "product_prices": {}},
        }

        # Send multiple concurrent requests
        job_ids = []
        for i in range(5):
            response = self.client.post(
                "/api/scenarios/run", json={"scenario": scenario, "async_mode": True}
            )
            self.assertEqual(response.status_code, 200)
            job_ids.append(response.json()["job_id"])

        # All job IDs should be unique
        self.assertEqual(len(job_ids), len(set(job_ids)))


if __name__ == "__main__":
    unittest.main()
