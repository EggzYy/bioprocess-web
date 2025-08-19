"""
WebSocket Integration Tests
"""

import unittest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from api.main import app


class TestWebSocketConnections(unittest.TestCase):
    """Test WebSocket connections and messaging"""

    def setUp(self):
        self.client = TestClient(app)
        self.test_scenario = {
            "name": "WebSocket Test",
            "target_tpa": 10.0,
            "strains": [
                "S. thermophilus",
                "L. delbrueckii subsp. bulgaricus",
                "L. acidophilus",
                "B. animalis subsp. lactis",
            ],
            "equipment": {"reactors_total": 4, "ds_lines_total": 2},
            "volumes": {
                "base_fermenter_vol_l": 2000,
                "working_volume_fraction": 0.8,
                "volume_options_l": [500, 1000, 1500, 2000, 3000, 4000, 5000],
            },
            "prices": {
                "raw_prices": {"Glucose": 0.22},
                "product_prices": {"default": 400},
            },
            "optimize_equipment": True,
            "use_multiobjective": True,
            "optimization": {
                "enabled": True,
                "simulation_type": "deterministic",
                "objectives": ["irr"],
            },
        }

    def test_websocket_connection(self):
        """Test establishing WebSocket connection"""
        with self.client.websocket_connect("/ws") as websocket:
            # Send initial connection message
            websocket.send_json({"type": "connection", "client_id": "test_client"})

            # Receive connection acknowledgment
            data = websocket.receive_json()
            self.assertEqual(data["type"], "connection_ack")
            self.assertIn("message", data)

    def test_websocket_scenario_execution(self):
        """Test scenario execution via WebSocket"""
        with self.client.websocket_connect("/ws") as websocket:
            # Send scenario execution request
            websocket.send_json(
                {
                    "type": "run_scenario",
                    "scenario": self.test_scenario,
                    "client_id": "test_client",
                }
            )

            # Receive progress updates
            received_messages = []
            for _ in range(50):
                try:
                    data = websocket.receive_json()
                    received_messages.append(data)

                    if data["type"] == "result":
                        # Scenario completed
                        self.assertIn("result", data)
                        self.assertIn("kpis", data["result"])
                        break
                    elif data["type"] == "progress":
                        # Progress update
                        self.assertIn("progress", data)
                        self.assertIn("message", data)
                    elif data["type"] == "error":
                        # Error occurred
                        self.fail(f"Error during execution: {data.get('message')}")
                except Exception:
                    break

            # Ensure we received at least one progress-like message
            progress_like = [
                m for m in received_messages if m["type"] in ("progress", "job_started")
            ]
            self.assertGreater(len(progress_like), 0)

    def test_websocket_job_cancellation(self):
        """Test job cancellation via WebSocket"""
        with self.client.websocket_connect("/ws") as websocket:
            # Start a job
            websocket.send_json(
                {
                    "type": "run_scenario",
                    "scenario": self.test_scenario,
                    "client_id": "test_client",
                }
            )

            # Wait for job to start
            data = websocket.receive_json()
            if "job_id" in data:
                job_id = data["job_id"]

                # Send cancellation request
                websocket.send_json(
                    {"type": "cancel_job", "job_id": job_id, "client_id": "test_client"}
                )

                # Receive cancellation confirmation
                cancel_data = websocket.receive_json()
                self.assertEqual(cancel_data["type"], "job_cancelled")
                self.assertEqual(cancel_data["job_id"], job_id)

    def test_websocket_multiple_clients(self):
        """Test multiple WebSocket clients"""
        clients = []
        client_ids = ["client_1", "client_2", "client_3"]

        try:
            # Connect multiple clients
            for client_id in client_ids:
                ws = self.client.websocket_connect("/ws").__enter__()
                ws.send_json({"type": "connection", "client_id": client_id})
                data = ws.receive_json()
                self.assertEqual(data["type"], "connection_ack")
                clients.append(ws)

            # Send scenario from first client
            clients[0].send_json(
                {
                    "type": "run_scenario",
                    "scenario": self.test_scenario,
                    "client_id": client_ids[0],
                }
            )

            # Check that only the sender receives updates
            data = clients[0].receive_json()
            self.assertIn(data["type"], ["progress", "result", "job_started"])

        finally:
            # Clean up connections
            for ws in clients:
                ws.__exit__(None, None, None)

    def test_websocket_error_handling(self):
        """Test WebSocket error handling"""
        with self.client.websocket_connect("/ws") as websocket:
            # Send invalid message
            websocket.send_json({"type": "invalid_type", "data": "test"})

            # Should receive error response
            data = websocket.receive_json()
            self.assertEqual(data["type"], "error")
            self.assertIn("message", data)

            # Send malformed scenario
            websocket.send_json(
                {
                    "type": "run_scenario",
                    "scenario": {"invalid": "data"},
                    "client_id": "test_client",
                }
            )

            # Should receive error response
            error_data = websocket.receive_json()
            self.assertEqual(error_data["type"], "error")
            self.assertIn("message", error_data)

    def test_websocket_batch_processing(self):
        """Test batch processing via WebSocket"""
        with self.client.websocket_connect("/ws") as websocket:
            # Send batch processing request
            scenarios = [self.test_scenario, self.test_scenario]
            websocket.send_json(
                {
                    "type": "run_batch",
                    "scenarios": scenarios,
                    "client_id": "test_client",
                }
            )

            # Receive batch progress updates
            batch_completed = False
            scenario_count = 0

            for _ in range(50):
                try:
                    data = websocket.receive_json()
                    if data["type"] == "batch_progress":
                        self.assertIn("completed", data)
                        self.assertIn("total", data)
                        scenario_count = data["completed"]
                    elif data["type"] == "batch_complete":
                        batch_completed = True
                        self.assertIn("results", data)
                        self.assertEqual(len(data["results"]), 2)
                        break
                    elif data["type"] == "error":
                        self.fail(
                            f"Error during batch processing: {data.get('message')}"
                        )
                except Exception:
                    break
            self.assertTrue(batch_completed)
            self.assertEqual(scenario_count, 2)

    def test_websocket_heartbeat(self):
        """Test WebSocket heartbeat/keepalive"""
        with self.client.websocket_connect("/ws") as websocket:
            # Send heartbeat
            websocket.send_json({"type": "ping", "client_id": "test_client"})

            # Receive pong response
            data = websocket.receive_json()
            self.assertEqual(data["type"], "pong")
            self.assertIn("timestamp", data)

    def test_websocket_sensitivity_analysis(self):
        """Test sensitivity analysis via WebSocket"""
        with self.client.websocket_connect("/ws") as websocket:
            # Send sensitivity analysis request
            websocket.send_json(
                {
                    "type": "run_sensitivity",
                    "scenario": self.test_scenario,
                    "parameters": ["discount_rate", "tax_rate"],
                    "delta_percentage": 0.1,
                    "client_id": "test_client",
                }
            )

            # Receive progress and results
            analysis_complete = False
            parameter_results = []

            for _ in range(50):
                try:
                    data = websocket.receive_json()
                    if data["type"] == "sensitivity_progress":
                        self.assertIn("parameter", data)
                        self.assertIn("progress", data)
                    elif data["type"] == "sensitivity_result":
                        analysis_complete = True
                        self.assertIn("results", data)
                        parameter_results = data["results"]
                        break
                    elif data["type"] == "error":
                        self.fail(
                            f"Error during sensitivity analysis: {data.get('message')}"
                        )
                except Exception:
                    break

            self.assertTrue(analysis_complete)
            self.assertGreater(len(parameter_results), 0)


class TestWebSocketReconnection(unittest.TestCase):
    """Test WebSocket reconnection and recovery"""

    def setUp(self):
        self.client = TestClient(app)

    def test_reconnection_after_disconnect(self):
        """Test reconnection after disconnection"""
        # First connection
        with self.client.websocket_connect("/ws") as ws1:
            ws1.send_json({"type": "connection", "client_id": "reconnect_test"})
            data1 = ws1.receive_json()
            self.assertEqual(data1["type"], "connection_ack")

        # Second connection with same client ID
        with self.client.websocket_connect("/ws") as ws2:
            ws2.send_json(
                {"type": "connection", "client_id": "reconnect_test", "reconnect": True}
            )
            data2 = ws2.receive_json()
            self.assertEqual(data2["type"], "connection_ack")

            # Check if any pending messages are delivered
            if "pending_messages" in data2:
                self.assertIsInstance(data2["pending_messages"], list)

    def test_job_recovery_after_reconnect(self):
        """Test job status recovery after reconnection"""
        job_id = None

        # Start a job and disconnect
        with self.client.websocket_connect("/ws") as ws1:
            ws1.send_json(
                {
                    "type": "run_scenario",
                    "scenario": {
                        "name": "Recovery Test",
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
                    },
                    "client_id": "recovery_test",
                    "async_mode": True,
                }
            )

            # Get job ID
            data = ws1.receive_json()
            if "job_id" in data:
                job_id = data["job_id"]

        if job_id:
            # Reconnect and query job status
            with self.client.websocket_connect("/ws") as ws2:
                ws2.send_json(
                    {
                        "type": "get_job_status",
                        "job_id": job_id,
                        "client_id": "recovery_test",
                    }
                )

                status_data = ws2.receive_json()
                self.assertIn("status", status_data)
                self.assertIn(
                    status_data["status"],
                    ["pending", "running", "completed", "failed", "cancelled"],
                )


if __name__ == "__main__":
    unittest.main()
