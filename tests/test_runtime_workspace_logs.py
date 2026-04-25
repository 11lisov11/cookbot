def test_recipe_runtime_pause_resume_abort_and_logs(client):
    assert client.post("/home").status_code == 200

    status = client.get("/recipes/runtime/status")
    assert status.status_code == 200
    assert status.json()["running"] is False

    paused = client.post("/recipes/runtime/pause")
    assert paused.status_code == 200

    run = client.post("/recipes/dry_run_stir_demo/run")
    assert run.status_code == 200
    assert run.json()["accepted"] is True

    resumed = client.post("/recipes/runtime/resume")
    assert resumed.status_code == 200

    aborted = client.post("/recipes/runtime/abort")
    assert aborted.status_code == 200
    assert aborted.json()["aborted"] is True

    logs = client.get("/logs?limit=20")
    assert logs.status_code == 200
    assert any(entry["event"] in {"run_complete", "abort"} for entry in logs.json())


def test_workspace_model_is_available(client):
    response = client.get("/workspace")
    assert response.status_code == 200
    body = response.json()
    assert body["project"] == "CookBot"
    assert body["verified_for_real_motion"] is False
    assert any(zone["kind"] == "keepout" for zone in body["zones"])


def test_hardware_readiness_gate_is_not_ready_by_default(client):
    response = client.get("/hardware/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["project"] == "CookBot"
    assert body["ready_for_real_motion"] is False
    assert any(item["id"] == "estop" for item in body["items"])

    gate = client.get("/hardware/gate/report")
    assert gate.status_code == 200
    gate_body = gate.json()
    assert gate_body["ready_for_real_motion"] is False
    assert gate_body["real_motion_locked"] is True
    assert gate_body["hardware_configured"] is False
    blocker_ids = {item["id"] for item in gate_body["blockers"]}
    assert "hardware_configured_disabled" in blocker_ids
    assert "backend_not_hardware_mode" in blocker_ids
