def test_calibration_wizard_runs_no_hardware_flow(client):
    started = client.post("/calibration/wizard/start")
    assert started.status_code == 200
    assert started.json()["active"] is True
    assert started.json()["current_step_id"] == "confirm_estop"

    status = started.json()
    for _ in range(status["total_steps"]):
        response = client.post("/calibration/wizard/advance")
        assert response.status_code == 200
        status = response.json()

    assert status["completed"] is True
    assert status["active"] is False
    assert "save_profile" in status["completed_steps"]

    calibration = client.get("/calibration/status")
    assert calibration.status_code == 200
    assert calibration.json()["loaded"] is True


def test_acceptance_report_is_green_for_no_hardware(client):
    response = client.get("/acceptance")
    assert response.status_code == 200
    body = response.json()
    assert body["project"] == "CookBot"
    assert body["ok"] is True
    assert any(item["id"] == "real_motion_locked" and item["ok"] for item in body["items"])


def test_recipe_preflight_returns_checklist(client):
    preflight = client.post("/recipes/dry_run_stir_demo/preflight")
    assert preflight.status_code == 200
    body = preflight.json()
    assert body["ok"] is False
    assert "not_homed" in body["reasons"]
    assert any(check["id"] == "homed" and not check["ok"] for check in body["checks"])
