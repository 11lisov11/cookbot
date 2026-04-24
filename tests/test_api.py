def test_health_state_camera_and_manual_motion(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["app"] == "CookBot"

    initial = client.get("/state").json()
    assert initial["mode"] == "simulator"
    assert initial["homed"] is False
    assert initial["motion_enabled"] is False

    blocked = client.post("/joints/joint_1/move", json={"position": 5.0})
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "motion_not_enabled"

    snapshot = client.get("/camera/snapshot")
    assert snapshot.status_code == 200
    assert snapshot.json()["data_url"].startswith("data:image/svg+xml;base64,")

    homed = client.post("/home")
    assert homed.status_code == 200
    assert homed.json()["homed"] is True
    assert homed.json()["motion_enabled"] is True

    moved = client.post("/joints/joint_1/move", json={"position": 12.5, "speed": 0.5})
    assert moved.status_code == 200
    joint_1 = next(axis for axis in moved.json()["axes"] if axis["id"] == "joint_1")
    assert joint_1["commanded_position"] == 12.5


def test_estop_blocks_motion_and_requires_rehome(client):
    assert client.post("/home").status_code == 200
    estop = client.post("/estop")
    assert estop.status_code == 200
    assert estop.json()["estop"] is True
    assert estop.json()["queue_depth"] == 0

    blocked = client.post("/joints/joint_1/move", json={"position": 1.0})
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "estop_active"

    cleared = client.post("/estop/clear")
    assert cleared.status_code == 200
    assert cleared.json()["estop"] is False
    assert cleared.json()["homed"] is False


def test_calibration_endpoint_marks_simulated_defaults(client):
    assert client.post("/home").status_code == 200
    calibrated = client.post("/calibration/simulate")
    assert calibrated.status_code == 200
    assert calibrated.json()["calibrated"] is True

