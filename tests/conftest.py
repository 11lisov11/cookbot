from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from unoq_backend.app import create_app
from unoq_backend.config import Settings


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        log_path=tmp_path / "cookbot.jsonl",
        recipes_dir=Path("recipes"),
        calibration_path=tmp_path / "calibration.json",
    )
    return TestClient(create_app(settings))
