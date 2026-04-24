from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from unoq_backend.app import create_app
from unoq_backend.camera import LibcameraStillCamera
from unoq_backend.config import Settings


def test_mock_camera_stream_has_multipart_frame(client):
    with client.stream("GET", "/camera/stream?frames=1") as response:
        body = b"".join(response.iter_bytes())
    assert response.status_code == 200
    assert b"--frame" in body
    assert b"CookBot mock camera" in body


def test_calibration_profile_can_be_saved_and_reset(tmp_path: Path):
    settings = Settings(
        log_path=tmp_path / "cookbot.jsonl",
        recipes_dir=Path("recipes"),
        calibration_path=tmp_path / "calibration.json",
    )
    client = TestClient(create_app(settings))

    assert client.post("/home").status_code == 200
    assert client.post("/calibration/simulate").json()["calibrated"] is True

    saved = client.post("/calibration/save")
    assert saved.status_code == 200
    assert saved.json()["project"] == "CookBot"
    assert settings.calibration_path.exists()

    status = client.get("/calibration/status")
    assert status.status_code == 200
    assert status.json()["loaded"] is True

    reset = client.post("/calibration/reset")
    assert reset.status_code == 200
    assert reset.json()["loaded"] is False
    assert not settings.calibration_path.exists()


def test_disabled_camera_fails_closed(tmp_path: Path):
    settings = Settings(
        log_path=tmp_path / "cookbot.jsonl",
        recipes_dir=Path("recipes"),
        camera="disabled",
    )
    client = TestClient(create_app(settings))
    response = client.get("/camera/snapshot")
    assert response.status_code == 400
    assert response.json()["detail"] == "camera_disabled"


def test_libcamera_snapshot_uses_command_boundary(tmp_path: Path, monkeypatch):
    def fake_run(command, check, capture_output, timeout):
        output_path = Path(command[-1])
        output_path.write_bytes(b"fake-jpeg")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("subprocess.run", fake_run)
    snapshot = LibcameraStillCamera().snapshot()
    assert snapshot.mode == "libcamera"
    assert snapshot.media_type == "image/jpeg"
    assert snapshot.data_url.startswith("data:image/jpeg;base64,")
