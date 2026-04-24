import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_backend() -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            request("/health")
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.4)
    raise SystemExit("CookBot backend did not become ready")


def main() -> None:
    wait_for_backend()
    health = request("/health")
    assert health["app"] == "CookBot"
    settings = request("/settings")
    assert settings["app"] == "CookBot"
    version = request("/version")
    assert version["app"] == "CookBot"
    assert version["api_schema_version"] == "1"
    diagnostics = request("/diagnostics")
    assert diagnostics["ok"] is True
    state = request("/state")
    assert state["mode"] == "simulator"
    workspace = request("/workspace")
    assert workspace["project"] == "CookBot"
    readiness = request("/hardware/readiness")
    assert readiness["ready_for_real_motion"] is False
    schemas = request("/schemas")
    assert "SystemState" in schemas
    assert "BackupBundle" in schemas
    acceptance = request("/acceptance")
    assert acceptance["ok"] is True
    readiness_report = request("/product/readiness")
    assert readiness_report["status"] == "no_hardware_product_ready"
    bundle = request("/export")
    assert bundle["project"] == "CookBot"
    backup = request("/backup")
    assert backup["kind"] == "cookbot_backup"
    restore = request("/restore/validate", "POST", backup)
    assert restore["valid"] is True
    snapshot = request("/camera/snapshot")
    assert snapshot["data_url"].startswith("data:image/svg+xml;base64,")
    calibration = request("/calibration/status")
    assert calibration["path"]
    accepted = request("/ai/command", "POST", {"command": "look at the workspace"})
    assert accepted["accepted"] is True
    forbidden = request("/ai/command", "POST", {"command": "cook scrambled eggs"})
    assert forbidden["accepted"] is False
    print("CookBot backend smoke passed")


if __name__ == "__main__":
    main()
