import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "release_tooling.py"


def run_release_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_release_plan_keeps_motion_locked():
    result = run_release_tool("plan", "--json")
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["project"] == "CookBot"
    assert body["real_motion_locked"] is True
    assert body["ready_for_real_motion"] is False
    assert body["file_count"] > 0
    assert any(item["path"] == "README.md" for item in body["files"])


def test_release_bundle_build_and_validate(tmp_path: Path):
    build = run_release_tool("build", "--output", str(tmp_path), "--skip-generated", "--json")
    assert build.returncode == 0
    build_body = json.loads(build.stdout)
    bundle = Path(build_body["bundle"])
    assert bundle.exists()
    assert build_body["real_motion_locked"] is True
    assert build_body["ready_for_real_motion"] is False
    assert build_body["file_count"] > 0

    validate = run_release_tool("validate", str(bundle), "--json")
    assert validate.returncode == 0
    validate_body = json.loads(validate.stdout)
    assert validate_body["ok"] is True
    assert validate_body["real_motion_locked"] is True
    assert validate_body["ready_for_real_motion"] is False


def test_release_validate_latest_requires_built_bundle(tmp_path: Path):
    result = run_release_tool("validate", "--latest", "--output", str(tmp_path), "--json")
    assert result.returncode == 2
    assert "release_bundle_required" in result.stdout
