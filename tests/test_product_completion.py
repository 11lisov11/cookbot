from pathlib import Path

from fastapi.testclient import TestClient

from unoq_backend.app import create_app
from unoq_backend.config import Settings


def test_version_backup_restore_and_product_readiness(client):
    version = client.get("/version")
    assert version.status_code == 200
    assert version.json()["app"] == "CookBot"
    assert version.json()["api_schema_version"] == "1"
    assert version.json()["hardware_configured"] is False

    backup = client.get("/backup")
    assert backup.status_code == 200
    backup_body = backup.json()
    assert backup_body["kind"] == "cookbot_backup"
    assert backup_body["hardware_readiness"]["ready_for_real_motion"] is False

    validation = client.post("/restore/validate", json=backup_body)
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    assert "workspace" in validation.json()["accepted_sections"]

    malformed = client.post("/restore/validate", json={"project": "CookBot"})
    assert malformed.status_code == 200
    assert malformed.json()["valid"] is False
    assert malformed.json()["accepted_sections"] == []

    hardware_bundle = backup_body.copy()
    hardware_bundle["hardware_readiness"] = {
        **hardware_bundle["hardware_readiness"],
        "ready_for_real_motion": True,
    }
    blocked = client.post("/restore/validate", json=hardware_bundle)
    assert blocked.status_code == 200
    assert blocked.json()["valid"] is False
    assert "real_motion_settings_not_applied_by_restore" in blocked.json()["reasons"]

    readiness = client.get("/product/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["ok"] is True
    assert readiness.json()["status"] == "no_hardware_product_ready"


def test_new_demo_recipes_preflight_and_run(client):
    listed = client.get("/recipes")
    recipe_ids = {recipe["id"] for recipe in listed.json()}
    assert {
        "dry_run_pick_place_demo",
        "camera_inspection_demo",
        "gripper_cycle_demo",
    } <= recipe_ids

    camera_preflight = client.post("/recipes/camera_inspection_demo/preflight")
    assert camera_preflight.status_code == 200
    assert camera_preflight.json()["ok"] is True
    camera_run = client.post("/recipes/camera_inspection_demo/run")
    assert camera_run.status_code == 200
    assert camera_run.json()["accepted"] is True

    before_home = client.post("/recipes/dry_run_pick_place_demo/preflight")
    assert before_home.status_code == 200
    assert "not_homed" in before_home.json()["reasons"]

    assert client.post("/home").status_code == 200
    for recipe_id in ("dry_run_pick_place_demo", "gripper_cycle_demo"):
        preflight = client.post(f"/recipes/{recipe_id}/preflight")
        assert preflight.status_code == 200
        assert preflight.json()["ok"] is True
        run = client.post(f"/recipes/{recipe_id}/run")
        assert run.status_code == 200
        assert run.json()["accepted"] is True


def test_optional_api_token_protects_product_endpoints(tmp_path: Path):
    settings = Settings(
        log_path=tmp_path / "cookbot.jsonl",
        recipes_dir=Path("recipes"),
        calibration_path=tmp_path / "calibration.json",
        api_token="secret",
    )
    client = TestClient(create_app(settings))

    assert client.get("/health").status_code == 200
    assert client.get("/settings").status_code == 200
    assert client.get("/version").status_code == 401
    assert client.get("/backup").status_code == 401
    assert client.get("/product/readiness").status_code == 401
    assert client.post("/restore/validate", json={}).status_code == 401

    headers = {"X-CookBot-Token": "secret"}
    assert client.get("/version", headers=headers).status_code == 200
    assert client.get("/backup", headers=headers).status_code == 200
    assert client.get("/product/readiness", headers=headers).status_code == 200
    restore = client.post("/restore/validate", json={}, headers=headers)
    assert restore.status_code == 200
    assert restore.json()["valid"] is False
