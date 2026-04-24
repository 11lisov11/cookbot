from pathlib import Path

from fastapi.testclient import TestClient

from unoq_backend.app import create_app
from unoq_backend.config import Settings


def test_settings_and_export_are_available_without_auth_by_default(client):
    settings = client.get("/settings")
    assert settings.status_code == 200
    assert settings.json()["app"] == "CookBot"
    assert settings.json()["api_auth_required"] is False

    export = client.get("/export")
    assert export.status_code == 200
    assert export.json()["project"] == "CookBot"
    assert export.json()["acceptance"]["ok"] is True


def test_optional_api_token_protects_dynamic_api(tmp_path: Path):
    settings = Settings(
        log_path=tmp_path / "cookbot.jsonl",
        recipes_dir=Path("recipes"),
        calibration_path=tmp_path / "calibration.json",
        api_token="secret",
    )
    client = TestClient(create_app(settings))

    assert client.get("/health").status_code == 200
    public_settings = client.get("/settings")
    assert public_settings.status_code == 200
    assert public_settings.json()["api_auth_required"] is True

    denied = client.get("/state")
    assert denied.status_code == 401
    assert denied.json()["detail"] == "cookbot_token_required"

    allowed = client.get("/state", headers={"X-CookBot-Token": "secret"})
    assert allowed.status_code == 200

    stream = client.get("/camera/stream?frames=1&cookbot_token=secret")
    assert stream.status_code == 200
    assert b"CookBot mock camera" in stream.content
