import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


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

    jog = run_tool("mega-ramps14-jog", "--axis", "B", "--dry-run")
    assert jog.returncode == 2
    assert "serial_port_required" in jog.stdout

    move = run_tool("mega-ramps14-move", "--axis", "A", "--direction", "1", "--dry-run")
    assert move.returncode == 2
    assert "serial_port_required" in move.stdout

    seek = run_tool("mega-ramps14-seek-limit", "--axis", "A", "--limit", "A_MIN", "--direction", "0", "--dry-run")
    assert seek.returncode == 2
    assert "serial_port_required" in seek.stdout


def test_ramps14_jog_dry_run_is_bounded_and_explicit():
    result = run_tool(
        "mega-ramps14-jog",
        "--port",
        "COM5",
        "--axis",
        "B",
        "--steps",
        "8",
        "--return-to-start",
        "--dry-run",
    )
    assert result.returncode == 0
    assert "jog_axis" in result.stdout
    assert "B_return" in result.stdout

    too_large = run_tool("mega-ramps14-jog", "--port", "COM5", "--axis", "B", "--steps", "200", "--dry-run")
    assert too_large.returncode == 2
    assert "invalid_jog_steps" in too_large.stdout


def test_ramps14_move_and_seek_dry_run_are_explicit():
    move = run_tool(
        "mega-ramps14-move",
        "--port",
        "COM5",
        "--axis",
        "A",
        "--direction",
        "1",
        "--steps",
        "1200",
        "--min-delay-us",
        "1850",
        "--dry-run",
    )
    assert move.returncode == 0
    assert "move_axis" in move.stdout
    assert "1850" in move.stdout

    seek = run_tool(
        "mega-ramps14-seek-limit",
        "--port",
        "COM5",
        "--axis",
        "A",
        "--limit",
        "A_MIN",
        "--direction",
        "0",
        "--max-steps",
        "2500",
        "--min-delay-us",
        "1850",
        "--dry-run",
    )
    assert seek.returncode == 0
    assert "seek_limit" in seek.stdout
    assert "A_MIN" in seek.stdout


def test_commissioning_and_deploy_dry_runs_do_not_touch_hardware():
    deploy = run_tool("unoq-adb-deploy", "--dry-run")
    assert deploy.returncode == 0
    assert "DRY RUN" in deploy.stdout

    commissioning = run_tool("commissioning-check", "--dry-run")
    assert commissioning.returncode == 0
    assert "commissioning sequence" in commissioning.stdout


def test_hardware_doctor_dry_run_reports_lock_and_mock_connections():
    result = run_tool(
        "hardware-doctor",
        "--dry-run",
        "--json",
        env={
            "COOKBOT_DRY_ADB_DEVICES": "unoq-dry-run",
            "COOKBOT_DRY_SERIAL_PORTS": "COM5",
            "COOKBOT_DRY_ARDUINO_BOARDS": "Arduino Mega",
        },
    )
    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body["real_motion_locked"] is True
    assert body["ready_for_real_motion"] is False
    assert "unoq-dry-run" in body["adb_devices"]
    assert "COM5" in body["serial_ports"]


def test_hardware_doctor_wrapper_dry_run_is_non_destructive():
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is not available")
    result = subprocess.run(
        [
            powershell,
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "hardware_doctor.ps1"),
            "--dry-run",
            "--json",
        ],
        cwd=ROOT,
        env={**os.environ.copy(), "COOKBOT_DRY_ADB_DEVICES": ""},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "real_motion_locked" in result.stdout
