import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "hardware_tooling.py"


def run_tool(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        env=merged_env,
        capture_output=True,
        text=True,
    )


def test_adb_check_dry_run_reports_missing_device():
    result = run_tool("unoq-adb-check", "--dry-run", "--json", env={"COOKBOT_DRY_ADB_DEVICES": ""})
    assert result.returncode == 3
    assert "adb_no_devices" in result.stdout


def test_platformio_missing_dry_run_path_is_explicit():
    result = run_tool("mega-platformio-build", "--simulate-missing-platformio")
    assert result.returncode == 2
    assert "platformio_not_found" in result.stdout


def test_upload_and_serial_probe_require_explicit_port():
    upload = run_tool("mega-platformio-upload", "--dry-run")
    assert upload.returncode == 2
    assert "serial_port_required" in upload.stdout

    probe = run_tool("mega-serial-probe", "--dry-run")
    assert probe.returncode == 2
    assert "serial_port_required" in probe.stdout


def test_commissioning_and_deploy_dry_runs_do_not_touch_hardware():
    deploy = run_tool("unoq-adb-deploy", "--dry-run")
    assert deploy.returncode == 0
    assert "DRY RUN" in deploy.stdout

    commissioning = run_tool("commissioning-check", "--dry-run")
    assert commissioning.returncode == 0
    assert "commissioning sequence" in commissioning.stdout
