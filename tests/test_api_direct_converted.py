from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_api_run_scenario_returns_non_zero_capacity():
    payload = {
        "scenario": {
            "name": "2-strain sanity",
            "strains": [
                {"name": "A", "titer_g_per_l": 90, "price_per_kg": 12.0},
                {"name": "B", "titer_g_per_l": 40, "price_per_kg": 17.0},
            ],
            "volumes": {"base_fermenter_vol_l": 10000, "working_volume_fraction": 0.8},
            "equipment": {"reactors_total": 4, "ds_lines_total": 2},
            "target_tpa": 1000,
            "optimize_equipment": False,
        },
        "async_mode": False,
    }
    res = client.post("/api/scenarios/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["result"]["capacity"]["total_annual_kg"] > 0
    assert data["result"]["kpis"]["tpa"] > 0


def test_websocket_run_scenario_streams_real_progress_and_result():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "connection", "client_id": "test"})
        ws.receive_json()
        payload = {
            "type": "run_scenario",
            "scenario": {
                "name": "ws-2-strain",
                "strains": [
                    {"name": "A", "titer_g_per_l": 90, "price_per_kg": 12.0},
                    {"name": "B", "titer_g_per_l": 40, "price_per_kg": 17.0},
                ],
                "volumes": {
                    "base_fermenter_vol_l": 10000,
                    "working_volume_fraction": 0.8,
                },
                "equipment": {"reactors_total": 4, "ds_lines_total": 2},
                "target_tpa": 800,
                "optimize_equipment": False,
            },
        }
        ws.send_json(payload)
        started = ws.receive_json()
        assert started["type"] == "job_started"
        saw_progress = False
        result = None
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "progress":
                saw_progress = True
            if msg["type"] == "result":
                result = msg
                break
        assert saw_progress
        assert result is not None
        assert result["result"]["kpis"]["tpa"] > 0
        assert result["result"]["kpis"]["npv"] is not None
