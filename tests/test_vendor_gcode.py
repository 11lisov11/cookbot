import asyncio
import json
import math
import subprocess
import sys

import pytest

from unoq_backend.models import (
    CoordinateCalibrationRequest,
    StepperMotionEstimateRequest,
)
from unoq_backend.motion_math import calibrate_steps_per_unit, estimate_stepper_motion
from unoq_backend.vendor_gcode import VendorControllerEmulator, parse_vendor_gcode
from scripts.vendor_axis4ui_emulator import handle_tcp_client


def test_vendor_parser_accepts_observed_compact_and_spaced_commands():
    compact = parse_vendor_gcode("G1X10Y205Z135E-500F100\r")
    assert compact.name == "linear_move"
    assert compact.parameters == {"X": 10.0, "Y": 205.0, "Z": 135.0, "E": -500.0, "F": 100.0}
    assert compact.normalized == "G1 X10 Y205 Z135 E-500 F100"

    assert parse_vendor_gcode("G4 S1.5\r").name == "dwell"
    assert parse_vendor_gcode("G90").name == "absolute_mode"
    assert parse_vendor_gcode("G91").name == "relative_mode"
    assert parse_vendor_gcode("G92 X0 Y100 Z0").name == "set_position"
    assert parse_vendor_gcode("G2696").name == "vendor_calibration_reset"
    assert parse_vendor_gcode("M6216").name == "driver_enable_on"
    assert parse_vendor_gcode("M212").name == "cooling_fan_off"


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("", "empty_command"),
        ("G0 X1", "unsupported_g_code"),
        ("G1 F100", "linear_move_requires_axis"),
        ("G1 X1 F151", "feed_out_of_vendor_range"),
        ("G1 X1 X2", "duplicate_parameter"),
        ("G1 X1 ; unsafe", "comments_not_supported"),
        ("M211 P9", "m_code_parameters_not_supported"),
        ("M999", "unsupported_m_code"),
    ],
)
def test_vendor_parser_rejects_unobserved_or_malformed_commands(line: str, reason: str):
    with pytest.raises(ValueError, match=reason):
        parse_vendor_gcode(line)


def test_vendor_emulator_tracks_absolute_relative_and_outputs_without_hardware():
    emulator = VendorControllerEmulator()
    emulator.execute("G1 X10 F100")
    emulator.execute("G91")
    result = emulator.execute("G1 X-2 E5")
    assert result.state.coordinates["X"] == 8.0
    assert result.state.coordinates["E"] == -495.0
    assert result.response_line == "ok X8 Y205 Z135 E-495.\n"

    assert emulator.execute("M211").state.outputs["fan"] is True
    assert emulator.execute("M212").state.outputs["fan"] is False
    assert emulator.execute("G2696").state.calibration_requested is True
    assert emulator.state.coordinates["X"] == 8.0


def test_stepper_motion_math_explains_current_a_axis_speed():
    estimate = estimate_stepper_motion(
        StepperMotionEstimateRequest(
            motor_full_steps_per_revolution=200,
            microsteps=16,
            gearbox_ratio=10,
            step_delay_us=3500,
            pulse_us=3,
        )
    )
    assert math.isclose(estimate.step_frequency_hz, 285.4696, rel_tol=1e-4)
    assert math.isclose(estimate.motor_rpm, 5.35255, rel_tol=1e-4)
    assert math.isclose(estimate.output_rpm, 0.535255, rel_tol=1e-4)
    assert estimate.steps_per_output_revolution == 32000


def test_coordinate_calibration_computes_steps_per_unit_without_unlocking_motion():
    result = calibrate_steps_per_unit(
        CoordinateCalibrationRequest(commanded_steps=4000, measured_units=25, unit="mm")
    )
    assert result.steps_per_unit == 160
    assert result.units_per_step == 0.00625
    assert result.verified_for_real_motion is False


def test_vendor_profile_validation_and_motion_api(client):
    profile = client.get("/vendor/profile")
    assert profile.status_code == 200
    assert profile.json()["direct_execution_enabled"] is False
    assert "steps_per_degree_for_a_b_c" in profile.json()["missing_controller_parameters"]

    valid = client.post("/vendor/gcode/validate", json={"line": "G1 X0 Y205 Z100 F100"})
    assert valid.status_code == 200
    assert valid.json()["accepted"] is True
    assert valid.json()["direct_execution_enabled"] is False

    rejected = client.post("/vendor/gcode/validate", json={"line": "M999"})
    assert rejected.status_code == 200
    assert rejected.json()["rejected_reason"] == "unsupported_m_code"

    estimate = client.post(
        "/motion/estimate",
        json={
            "motor_full_steps_per_revolution": 200,
            "microsteps": 16,
            "gearbox_ratio": 10,
            "step_delay_us": 3500,
            "pulse_us": 3,
        },
    )
    assert estimate.status_code == 200
    assert estimate.json()["output_rpm"] < 1

    calibration = client.post(
        "/motion/calibrate",
        json={"commanded_steps": 4000, "measured_units": 25, "unit": "mm"},
    )
    assert calibration.status_code == 200
    assert calibration.json()["steps_per_unit"] == 160
    assert calibration.json()["verified_for_real_motion"] is False


def test_emulator_cli_once_is_machine_readable():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/vendor_axis4ui_emulator.py",
            "--once",
            "G1 X1 F100",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["coordinates"]["X"] == 1


@pytest.mark.asyncio
async def test_emulator_tcp_accepts_carriage_return_framing():
    server = await asyncio.start_server(handle_tcp_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"G1X2F100\r")
        await writer.drain()
        response = await asyncio.wait_for(reader.readline(), timeout=1)
        assert response == b"ok X2 Y205 Z135 E-500.\n"
        writer.close()
        await writer.wait_closed()
    finally:
        server.close()
        await server.wait_closed()
