def test_diagnostics_endpoint_reports_core_checks(client):
    response = client.get("/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    names = {check["name"] for check in body["checks"]}
    assert {
        "backend",
        "mega_hello",
        "mega_ping",
        "mega_state",
        "mega_capabilities",
        "camera",
        "hardware_readiness",
        "release_bundle",
    } <= names


def test_simulator_fault_endpoint_fails_closed(client):
    assert client.post("/home").status_code == 200
    injected = client.post(
        "/simulator/faults",
        json={"code": "limit_switch_stuck_min", "joint_id": "joint_1", "message": "test fault"},
    )
    assert injected.status_code == 200
    assert injected.json()["last_error"] == "limit_switch_stuck_min"
    assert injected.json()["motion_enabled"] is False

    blocked = client.post("/joints/joint_1/move", json={"position": 1.0})
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "motion_not_enabled"

    cleared = client.delete("/simulator/faults")
    assert cleared.status_code == 200
    assert cleared.json()["last_error"] == "faults_cleared_rehome_required"
