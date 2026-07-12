import argparse
import base64
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(prog="cookbot-hardware-tooling")
    subcommands = parser.add_subparsers(dest="command", required=True)

    adb_check = subcommands.add_parser("unoq-adb-check")
    adb_check.add_argument("--dry-run", action="store_true")
    adb_check.add_argument("--json", action="store_true")
    adb_check.set_defaults(fn=cmd_unoq_adb_check)

    adb_deploy = subcommands.add_parser("unoq-adb-deploy")
    adb_deploy.add_argument("--target", default="/home/arduino/cookbot")
    adb_deploy.add_argument(
        "--mega-transport",
        choices=["fake", "serial", "bluetooth_rfcomm"],
        default="fake",
    )
    adb_deploy.add_argument("--bluetooth-address")
    adb_deploy.add_argument("--bluetooth-channel", type=int, default=1)
    adb_deploy.add_argument("--bind", default="127.0.0.1")
    adb_deploy.add_argument("--dry-run", action="store_true")
    adb_deploy.set_defaults(fn=cmd_unoq_adb_deploy)

    adb_logs = subcommands.add_parser("unoq-adb-logs")
    adb_logs.add_argument("--dry-run", action="store_true")
    adb_logs.set_defaults(fn=cmd_unoq_adb_logs)

    bluetooth_check = subcommands.add_parser("unoq-bluetooth-check")
    bluetooth_check.add_argument("--address")
    bluetooth_check.add_argument("--dry-run", action="store_true")
    bluetooth_check.add_argument("--json", action="store_true")
    bluetooth_check.set_defaults(fn=cmd_unoq_bluetooth_check)

    bluetooth_pair = subcommands.add_parser("unoq-bluetooth-pair")
    bluetooth_pair.add_argument("--address")
    bluetooth_pair.add_argument("--pin", default="1234")
    bluetooth_pair.add_argument("--dry-run", action="store_true")
    bluetooth_pair.set_defaults(fn=cmd_unoq_bluetooth_pair)

    bluetooth_probe = subcommands.add_parser("unoq-bluetooth-probe")
    bluetooth_probe.add_argument("--address")
    bluetooth_probe.add_argument("--channel", type=int, default=1)
    bluetooth_probe.add_argument("--target", default="/home/arduino/cookbot")
    bluetooth_probe.add_argument("--dry-run", action="store_true")
    bluetooth_probe.set_defaults(fn=cmd_unoq_bluetooth_probe)

    pio_build = subcommands.add_parser("mega-platformio-build")
    pio_build.add_argument("--env", default="cookbot_mega2560")
    pio_build.add_argument("--dry-run", action="store_true")
    pio_build.add_argument("--simulate-missing-platformio", action="store_true")
    pio_build.set_defaults(fn=cmd_mega_platformio_build)

    pio_upload = subcommands.add_parser("mega-platformio-upload")
    pio_upload.add_argument("--env", default="cookbot_mega2560")
    pio_upload.add_argument("--port")
    pio_upload.add_argument("--dry-run", action="store_true")
    pio_upload.set_defaults(fn=cmd_mega_platformio_upload)

    serial_probe = subcommands.add_parser("mega-serial-probe")
    serial_probe.add_argument("--port")
    serial_probe.add_argument("--baud", type=int, default=115200)
    serial_probe.add_argument("--dry-run", action="store_true")
    serial_probe.set_defaults(fn=cmd_mega_serial_probe)

    motion_calc = subcommands.add_parser("mega-motion-calc")
    motion_calc.add_argument("--delay-us", type=float, required=True)
    motion_calc.add_argument("--pulse-us", type=float, default=8.0)
    motion_calc.add_argument("--steps-per-rev", type=float, default=200.0)
    motion_calc.add_argument("--microstep", type=float, default=16.0)
    motion_calc.add_argument("--gear-ratio", type=float, default=1.0)
    motion_calc.add_argument("--json", action="store_true")
    motion_calc.set_defaults(fn=cmd_mega_motion_calc)

    a4988_calc = subcommands.add_parser("a4988-current-calc")
    a4988_calc.add_argument("--rsense-ohm", type=float, required=True)
    a4988_target = a4988_calc.add_mutually_exclusive_group(required=True)
    a4988_target.add_argument("--current-a", type=float)
    a4988_target.add_argument("--vref-v", type=float)
    a4988_calc.add_argument("--json", action="store_true")
    a4988_calc.set_defaults(fn=cmd_a4988_current_calc)

    ramps14_jog = subcommands.add_parser("mega-ramps14-jog")
    ramps14_jog.add_argument("--port")
    ramps14_jog.add_argument("--baud", type=int, default=115200)
    ramps14_jog.add_argument("--axis", choices=["A", "B", "C", "SLIDER", "X", "Y", "Z", "E0", "E1"], required=True)
    ramps14_jog.add_argument("--steps", type=int, default=8)
    ramps14_jog.add_argument("--direction", type=int, choices=[0, 1], default=1)
    ramps14_jog.add_argument("--return-to-start", action="store_true")
    ramps14_jog.add_argument("--dry-run", action="store_true")
    ramps14_jog.set_defaults(fn=cmd_mega_ramps14_jog)

    ramps14_move = subcommands.add_parser("mega-ramps14-move")
    _add_ramps14_motion_args(ramps14_move)
    ramps14_move.add_argument("--direction", type=int, choices=[0, 1], required=True)
    ramps14_move.add_argument("--steps", type=int, default=1200)
    ramps14_move.add_argument("--hold", action="store_true")
    ramps14_move.set_defaults(fn=cmd_mega_ramps14_move)

    ramps14_seek = subcommands.add_parser("mega-ramps14-seek-limit")
    _add_ramps14_motion_args(ramps14_seek)
    ramps14_seek.add_argument("--direction", type=int, choices=[0, 1], required=True)
    ramps14_seek.add_argument("--limit", choices=["A_MIN", "B_MIN", "C_MIN"], required=True)
    ramps14_seek.add_argument("--max-steps", type=int, default=2500)
    ramps14_seek.set_defaults(fn=cmd_mega_ramps14_seek_limit)

    ramps14_output = subcommands.add_parser("mega-ramps14-output")
    ramps14_output.add_argument("--port")
    ramps14_output.add_argument("--baud", type=int, default=115200)
    ramps14_output.add_argument("--output", choices=["D8", "D9", "D10"], required=True)
    ramps14_output.add_argument("--pwm", type=int, required=True)
    ramps14_output.add_argument("--duration-ms", type=int, default=0)
    ramps14_output.add_argument("--dry-run", action="store_true")
    ramps14_output.set_defaults(fn=cmd_mega_ramps14_output)

    ramps14_enable = subcommands.add_parser("mega-ramps14-enable")
    ramps14_enable.add_argument("--port")
    ramps14_enable.add_argument("--baud", type=int, default=115200)
    ramps14_enable.add_argument("--axis", choices=["A", "B", "C", "SLIDER", "X", "Y", "Z", "E0", "E1"], required=True)
    ramps14_enable.add_argument("--enabled", type=int, choices=[0, 1], required=True)
    ramps14_enable.add_argument("--dry-run", action="store_true")
    ramps14_enable.set_defaults(fn=cmd_mega_ramps14_enable)

    ramps14_sweep = subcommands.add_parser("mega-ramps14-axis-sweep")
    ramps14_sweep.add_argument("--port")
    ramps14_sweep.add_argument("--baud", type=int, default=115200)
    ramps14_sweep.add_argument("--axes", default="A,B,C,E0")
    ramps14_sweep.add_argument("--steps", type=int, default=300)
    ramps14_sweep.add_argument("--slider-steps", type=int, default=300)
    ramps14_sweep.add_argument("--delay-us", type=int, default=8000)
    ramps14_sweep.add_argument("--slider-delay-us", type=int, default=30000)
    ramps14_sweep.add_argument("--pulse-us", type=int, default=8)
    ramps14_sweep.add_argument("--slider-pulse-us", type=int, default=12)
    ramps14_sweep.add_argument("--dry-run", action="store_true")
    ramps14_sweep.set_defaults(fn=cmd_mega_ramps14_axis_sweep)

    ramps14_edge_scan = subcommands.add_parser("mega-ramps14-edge-scan")
    ramps14_edge_scan.add_argument("--port")
    ramps14_edge_scan.add_argument("--baud", type=int, default=115200)
    ramps14_edge_scan.add_argument("--axis", choices=["A", "B", "C"], required=True)
    ramps14_edge_scan.add_argument("--home-direction", type=int, choices=[0, 1], default=0)
    ramps14_edge_scan.add_argument("--away-direction", type=int, choices=[0, 1], default=1)
    ramps14_edge_scan.add_argument("--home-max-steps", type=int, default=10000)
    ramps14_edge_scan.add_argument("--away-steps", type=int, default=5000)
    ramps14_edge_scan.add_argument("--chunk-steps", type=int, default=1000)
    ramps14_edge_scan.add_argument("--home-delay-us", type=int, default=8000)
    ramps14_edge_scan.add_argument("--away-delay-us", type=int, default=8000)
    ramps14_edge_scan.add_argument("--away-start-delay-us", type=int)
    ramps14_edge_scan.add_argument("--away-accel-steps", type=int, default=0)
    ramps14_edge_scan.add_argument("--away-decel-steps", type=int, default=0)
    ramps14_edge_scan.add_argument("--pulse-us", type=int, default=8)
    ramps14_edge_scan.add_argument("--step-backend", choices=["direct", "digital"], default="direct")
    ramps14_edge_scan.add_argument("--dry-run", action="store_true")
    ramps14_edge_scan.set_defaults(fn=cmd_mega_ramps14_edge_scan)

    commissioning = subcommands.add_parser("commissioning-check")
    commissioning.add_argument("--mega-port")
    commissioning.add_argument("--skip-adb-deploy", action="store_true")
    commissioning.add_argument("--dry-run", action="store_true")
    commissioning.set_defaults(fn=cmd_commissioning_check)

    doctor = subcommands.add_parser("hardware-doctor")
    doctor.add_argument("--backend-url", default=None)
    doctor.add_argument("--dry-run", action="store_true")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--strict", action="store_true")
    doctor.set_defaults(fn=cmd_hardware_doctor)

    args = parser.parse_args()
    return int(args.fn(args))


def _add_ramps14_motion_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--axis", choices=["A", "B", "C", "SLIDER", "X", "Y", "Z", "E0", "E1"], required=True)
    parser.add_argument("--pulse-us", type=int)
    parser.add_argument("--start-delay-us", type=int)
    parser.add_argument("--min-delay-us", type=int)
    parser.add_argument("--accel-steps", type=int)
    parser.add_argument("--decel-steps", type=int)
    parser.add_argument("--step-backend", choices=["direct", "digital"])
    parser.add_argument("--dry-run", action="store_true")


def cmd_unoq_adb_check(args: argparse.Namespace) -> int:
    if args.dry_run:
        devices = _mock_devices()
        result = {
            "adb": "dry_run",
            "devices": devices,
            "ready": bool(devices),
            "message": "ADB dry run",
        }
        if not devices:
            return _fail("adb_no_devices", args.json, result, 3)
        _emit(result, args.json)
        return 0

    adb = shutil.which("adb")
    if not adb:
        return _fail("adb_not_found", args.json, {"ready": False}, 2)

    devices = _adb_devices(adb)
    if not devices:
        return _fail("adb_no_devices", args.json, {"adb": adb, "ready": False}, 3)

    uid = _run_capture([adb, "shell", "id", "-u"], check=False).strip()
    if uid == "0":
        return _fail(
            "unoq_old_image_root_adb_update_required",
            args.json,
            {"adb": adb, "devices": devices, "ready": False},
            4,
        )

    details = {
        "adb": adb,
        "devices": devices,
        "uid": uid,
        "uname": _run_capture([adb, "shell", "uname", "-a"], check=False).strip(),
        "os_release": _run_capture([adb, "shell", "cat", "/etc/os-release"], check=False).strip(),
        "python3": _remote_command_exists(adb, "python3"),
        "node": _remote_command_exists(adb, "node"),
        "npm": _remote_command_exists(adb, "npm"),
        "arduino_cli": _remote_command_exists(adb, "arduino-cli"),
        "ready": True,
    }
    _emit(details, args.json)
    return 0


def cmd_unoq_adb_deploy(args: argparse.Namespace) -> int:
    if args.mega_transport == "bluetooth_rfcomm":
        if not args.bluetooth_address:
            return _fail("bluetooth_address_required", False, {}, 2)
        if not _valid_bluetooth_address(args.bluetooth_address):
            return _fail("bluetooth_address_invalid", False, {}, 2)
        if not 1 <= args.bluetooth_channel <= 30:
            return _fail("bluetooth_channel_invalid", False, {}, 2)
    if args.dry_run:
        print(f"DRY RUN: would deploy tracked CookBot files to UNO Q at {args.target}")
        print(
            "DRY RUN: would install dependencies, write a private environment file, "
            "install user systemd units, and restart backend"
        )
        print(f"DRY RUN: Mega transport={args.mega_transport} bind={args.bind}")
        return 0

    check = argparse.Namespace(dry_run=False, json=False)
    if cmd_unoq_adb_check(check) != 0:
        return 1
    adb = shutil.which("adb")
    assert adb

    with tempfile.TemporaryDirectory(prefix="cookbot-adb-") as temp_dir:
        temp = Path(temp_dir)
        files = _git_files()
        for rel in files:
            source = ROOT / rel
            if source.is_file():
                dest = temp / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
        _run([adb, "shell", "mkdir", "-p", args.target])
        _run([adb, "push", f"{temp}{os.sep}.", args.target])

    environment = {
        "COOKBOT_MODE": "hardware" if args.mega_transport != "fake" else "simulator",
        "COOKBOT_MEGA_TRANSPORT": args.mega_transport,
        "COOKBOT_CAMERA": "mock",
        "COOKBOT_AI": "mock",
        "COOKBOT_BIND": args.bind,
        "COOKBOT_PORT": "8000",
        "COOKBOT_HARDWARE_CONFIGURED": "false",
        "COOKBOT_BLUETOOTH_ADDRESS": (args.bluetooth_address or "").upper(),
        "COOKBOT_BLUETOOTH_CHANNEL": str(args.bluetooth_channel),
        "COOKBOT_BLUETOOTH_TIMEOUT_S": "3",
        "COOKBOT_API_TOKEN": os.environ.get("COOKBOT_API_TOKEN", ""),
    }
    encoded_environment = base64.b64encode(
        "".join(f"{key}={value}\n" for key, value in environment.items()).encode("utf-8")
    ).decode("ascii")

    remote = (
        f"cd {args.target} && "
        "python3 -m pip install --user -r requirements.txt && "
        "if command -v npm >/dev/null 2>&1; then cd web && npm install && npm run build && cd ..; fi && "
        "mkdir -p ~/.config/systemd/user ~/.config/cookbot && "
        f"printf %s {encoded_environment} | base64 -d > ~/.config/cookbot/cookbot.env && "
        "chmod 600 ~/.config/cookbot/cookbot.env && "
        "cp deploy/systemd/cookbot-backend.user.service ~/.config/systemd/user/cookbot-backend.service && "
        "systemctl --user daemon-reload && "
        "systemctl --user restart cookbot-backend.service"
    )
    _run([adb, "shell", remote])
    return 0


def cmd_unoq_adb_logs(args: argparse.Namespace) -> int:
    if args.dry_run:
        print("DRY RUN: would print ADB devices, user service status, journal logs, and serial device list")
        return 0
    adb = shutil.which("adb")
    if not adb:
        return _fail("adb_not_found", False, {}, 2)
    _run([adb, "devices"])
    _run([adb, "shell", "systemctl --user status cookbot-backend.service --no-pager || true"])
    _run([adb, "shell", "journalctl --user -u cookbot-backend.service -n 80 --no-pager || true"])
    _run([adb, "shell", "ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true"])
    return 0


def cmd_unoq_bluetooth_check(args: argparse.Namespace) -> int:
    if args.address and not _valid_bluetooth_address(args.address):
        return _fail("bluetooth_address_invalid", args.json, {}, 2)
    if args.dry_run:
        result = {
            "ready": bool(args.address),
            "address": args.address or "not_selected",
            "adapter": "dry_run",
            "paired": False,
        }
        _emit(result, args.json)
        return 0

    if cmd_unoq_adb_check(argparse.Namespace(dry_run=False, json=False)) != 0:
        return 1
    adb = shutil.which("adb")
    assert adb
    capability_script = ROOT / "scripts" / "unoq_bluetooth_capabilities.sh"
    if not capability_script.exists():
        return _fail("bluetooth_capability_script_missing", args.json, {}, 3)
    pushed = subprocess.run(
        [adb, "push", str(capability_script), "/tmp/cookbot-bt-capabilities.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if pushed.returncode != 0:
        return _fail(
            "bluetooth_capability_script_push_failed",
            args.json,
            {"detail": (pushed.stderr or pushed.stdout).strip()},
            3,
        )
    capability_command = "chmod +x /tmp/cookbot-bt-capabilities.sh && /tmp/cookbot-bt-capabilities.sh"
    if args.address:
        capability_command += f" --address {args.address.upper()}"
    capability = subprocess.run(
        [adb, "shell", capability_command],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    capability_output = "\n".join(
        part.strip() for part in (capability.stdout, capability.stderr) if part.strip()
    )
    if capability.returncode != 0:
        return _fail(
            "unoq_bluetooth_rfcomm_unavailable",
            args.json,
            {"detail": capability_output},
            3,
        )
    adapter = _run_capture([adb, "shell", "bluetoothctl", "show"], check=False).strip()
    if not adapter:
        return _fail("unoq_bluetooth_adapter_unavailable", args.json, {}, 3)
    info = ""
    if args.address:
        info = _run_capture(
            [adb, "shell", "bluetoothctl", "info", args.address.upper()], check=False
        ).strip()
    result = {
        "ready": True,
        "address": args.address.upper() if args.address else "not_selected",
        "adapter": adapter,
        "capabilities": capability_output,
        "device_info": info,
        "paired": "Paired: yes" in info,
        "trusted": "Trusted: yes" in info,
    }
    _emit(result, args.json)
    return 0


def cmd_unoq_bluetooth_pair(args: argparse.Namespace) -> int:
    if not args.address:
        return _fail("bluetooth_address_required", False, {}, 2)
    if not _valid_bluetooth_address(args.address):
        return _fail("bluetooth_address_invalid", False, {}, 2)
    if not re.fullmatch(r"[0-9]{4,16}", args.pin):
        return _fail("bluetooth_pin_invalid", False, {}, 2)
    if args.dry_run:
        print(f"DRY RUN: would pair and trust {args.address.upper()} on UNO Q; PIN is not printed")
        return 0

    if cmd_unoq_adb_check(argparse.Namespace(dry_run=False, json=False)) != 0:
        return 1
    adb = shutil.which("adb")
    assert adb
    remote_script = ROOT / "scripts" / "unoq_bluetooth_pair_remote.sh"
    if not remote_script.exists():
        return _fail("bluetooth_pair_script_missing", False, {}, 3)
    if subprocess.run([adb, "push", str(remote_script), "/tmp/cookbot-bt-pair.sh"]).returncode != 0:
        return _fail("bluetooth_pair_script_push_failed", False, {}, 3)
    remote = (
        "chmod +x /tmp/cookbot-bt-pair.sh && "
        f"/tmp/cookbot-bt-pair.sh --address {args.address.upper()} --pin {args.pin}"
    )
    result = subprocess.run([adb, "shell", remote])
    return result.returncode


def cmd_unoq_bluetooth_probe(args: argparse.Namespace) -> int:
    if not args.address:
        return _fail("bluetooth_address_required", False, {}, 2)
    if not _valid_bluetooth_address(args.address):
        return _fail("bluetooth_address_invalid", False, {}, 2)
    if not 1 <= args.channel <= 30:
        return _fail("bluetooth_channel_invalid", False, {}, 2)
    command = (
        f"cd {args.target} && python3 scripts/bluetooth_rfcomm_probe.py "
        f"--address {args.address.upper()} --channel {args.channel}"
    )
    if args.dry_run:
        print("DRY RUN: adb shell", command)
        return 0
    if cmd_unoq_adb_check(argparse.Namespace(dry_run=False, json=False)) != 0:
        return 1
    adb = shutil.which("adb")
    assert adb
    return _run([adb, "shell", command])


def cmd_mega_platformio_build(args: argparse.Namespace) -> int:
    if args.simulate_missing_platformio:
        return _fail("platformio_not_found", False, {}, 2)
    pio = _platformio_command()
    if not pio:
        return _fail("platformio_not_found", False, {}, 2)
    command = [*pio, "run", "-e", args.env]
    if args.dry_run:
        print("DRY RUN:", " ".join(command))
        return 0
    return _run(command)


def cmd_mega_platformio_upload(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    command = ["pio", "run", "-e", args.env, "-t", "upload", "--upload-port", args.port]
    if args.dry_run:
        print("DRY RUN:", " ".join(command))
        return 0
    pio = _platformio_command()
    if not pio:
        return _fail("platformio_not_found", False, {}, 3)
    command = [*pio, "run", "-e", args.env, "-t", "upload", "--upload-port", args.port]
    return _run(command)


def cmd_mega_serial_probe(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    if args.dry_run:
        print(f"DRY RUN: would probe Mega JSON protocol on {args.port} at {args.baud}")
        return 0
    try:
        import serial  # type: ignore
    except ImportError:
        return _fail("pyserial_not_installed", False, {}, 3)

    from unoq_backend.mega_protocol import build_request, decode_response, encode_request

    try:
        handle = serial.Serial(args.port, args.baud, timeout=2.0)
    except Exception as exc:
        return _fail(f"serial_open_failed:{args.port}:{exc}", False, {}, 3)

    with handle:
        time.sleep(2.0)
        handle.reset_input_buffer()
        for command in ("hello", "get_firmware_status", "self_test", "read_inputs"):
            request = build_request(command)
            handle.write(encode_request(request))
            response = None
            bad_line = None
            for _ in range(5):
                line = handle.readline()
                if not line:
                    continue
                try:
                    candidate = decode_response(line)
                except Exception:
                    if _is_async_mega_event(line):
                        continue
                    bad_line = line[:80]
                    continue
                if candidate.id != request.id:
                    continue
                response = candidate
                break
            if response is None:
                if bad_line:
                    return _fail(f"bad_response:{command}:{bad_line!r}", False, {}, 5)
                return _fail(f"no_response:{command}", False, {}, 4)
            if not response.ok:
                return _fail(f"mega_error:{command}:{response.error}", False, {}, 5)
            print(json.dumps(response.model_dump(mode="json"), indent=2))
    return 0


def cmd_mega_motion_calc(args: argparse.Namespace) -> int:
    if args.delay_us <= 0 or args.pulse_us <= 0:
        return _fail("invalid_timing", args.json, {}, 2)
    if args.steps_per_rev <= 0 or args.microstep <= 0 or args.gear_ratio <= 0:
        return _fail("invalid_motion_geometry", args.json, {}, 2)

    step_period_us = args.delay_us + args.pulse_us
    step_rate_hz = 1_000_000.0 / step_period_us
    motor_rpm = (step_rate_hz * 60.0) / (args.steps_per_rev * args.microstep)
    output_rpm = motor_rpm / args.gear_ratio
    pulses_per_motor_rev = args.steps_per_rev * args.microstep
    pulses_per_output_rev = pulses_per_motor_rev * args.gear_ratio
    result = {
        "delay_us": args.delay_us,
        "pulse_us": args.pulse_us,
        "step_period_us": step_period_us,
        "step_rate_hz": step_rate_hz,
        "steps_per_rev": args.steps_per_rev,
        "microstep": args.microstep,
        "gear_ratio": args.gear_ratio,
        "pulses_per_motor_rev": pulses_per_motor_rev,
        "pulses_per_output_rev": pulses_per_output_rev,
        "motor_rpm": motor_rpm,
        "output_rpm": output_rpm,
        "output_rev_per_hour": output_rpm * 60.0,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"step_rate_hz={step_rate_hz:.2f}")
        print(f"motor_rpm={motor_rpm:.4f}")
        print(f"output_rpm={output_rpm:.4f}")
        print(f"pulses_per_output_rev={pulses_per_output_rev:.0f}")
    return 0


def cmd_a4988_current_calc(args: argparse.Namespace) -> int:
    if args.rsense_ohm <= 0:
        return _fail("invalid_rsense", args.json, {}, 2)
    if args.current_a is not None and args.current_a <= 0:
        return _fail("invalid_current", args.json, {}, 2)
    if args.vref_v is not None and args.vref_v <= 0:
        return _fail("invalid_vref", args.json, {}, 2)

    if args.current_a is not None:
        current_a = args.current_a
        vref_v = current_a * 8.0 * args.rsense_ohm
    else:
        vref_v = args.vref_v
        current_a = vref_v / (8.0 * args.rsense_ohm)

    result = {
        "driver": "A4988",
        "formula": "I_tripmax = Vref / (8 * Rsense)",
        "rsense_ohm": args.rsense_ohm,
        "current_a": current_a,
        "vref_v": vref_v,
        "note": "Verify the sense resistor marking on the exact red stepstick module before adjusting current.",
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "A4988 current limit: "
            f"Rsense={args.rsense_ohm:g} ohm, Vref={vref_v:.3f} V, "
            f"I_tripmax={current_a:.3f} A"
        )
        print("Formula: I_tripmax = Vref / (8 * Rsense)")
        print("Check the Rsense marking on the real red stepstick before changing the potentiometer.")
    return 0


def cmd_mega_ramps14_jog(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    if args.steps < 1 or args.steps > 25:
        return _fail("invalid_jog_steps:max_25", False, {}, 2)
    commands = [
        {
            "id": f"{args.axis}_jog",
            "command": "jog_axis",
            "axis": args.axis,
            "steps": args.steps,
            "direction": args.direction,
            "pulse_us": 4,
            "step_delay_us": 3000,
        }
    ]
    if args.return_to_start:
        commands.append({**commands[0], "id": f"{args.axis}_return", "direction": 0 if args.direction else 1})
    if args.dry_run:
        print("DRY RUN:", json.dumps({"port": args.port, "baud": args.baud, "commands": commands}, indent=2), flush=True)
        return 0

    try:
        import serial  # type: ignore
    except ImportError:
        return _fail("pyserial_not_installed", False, {}, 3)

    try:
        handle = serial.Serial(args.port, args.baud, timeout=1.0)
    except Exception as exc:
        return _fail(f"serial_open_failed:{args.port}:{exc}", False, {}, 3)

    with handle:
        time.sleep(2.0)
        handle.reset_input_buffer()
        status = _send_raw_mega_json(handle, {"id": "jog_status", "command": "get_firmware_status"})
        if not status.get("ok"):
            return _fail(f"status_failed:{status}", False, {}, 4)
        firmware_status = status.get("data", {}).get("firmware_status", {})
        if not firmware_status.get("ramps14_commissioning"):
            return _fail("ramps14_commissioning_not_enabled", False, firmware_status, 5)
        for command in commands:
            response = _send_raw_mega_json(handle, command)
            print(json.dumps(response, indent=2), flush=True)
            if not response.get("ok"):
                return _fail(f"jog_failed:{response.get('error')}", False, response, 6)
            time.sleep(0.25)
    return 0


def cmd_mega_ramps14_move(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    if args.steps < 1 or args.steps > 30000:
        return _fail("invalid_move_steps", False, {}, 2)
    timing = _resolve_ramps14_timing(args, "move")
    command = {
        "id": f"{args.axis}_move",
        "command": "move_axis",
        "axis": args.axis,
        "direction": args.direction,
        "steps": args.steps,
        "hold": 1 if args.hold else 0,
        "step_backend": _resolve_ramps14_step_backend(args),
        **timing,
    }
    return _send_ramps14_motion_command(args, command)


def cmd_mega_ramps14_seek_limit(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    if args.max_steps < 1 or args.max_steps > 40000:
        return _fail("invalid_seek_steps", False, {}, 2)
    timing = _resolve_ramps14_timing(args, "seek")
    command = {
        "id": f"{args.axis}_{args.limit}_seek",
        "command": "seek_limit",
        "axis": args.axis,
        "limit": args.limit,
        "direction": args.direction,
        "max_steps": args.max_steps,
        "step_backend": _resolve_ramps14_step_backend(args),
        **timing,
    }
    return _send_ramps14_motion_command(args, command)


def cmd_mega_ramps14_output(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    if args.pwm < 0 or args.pwm > 255:
        return _fail("invalid_output_pwm", False, {}, 2)
    if args.duration_ms < 0 or args.duration_ms > 60000:
        return _fail("invalid_output_duration", False, {}, 2)
    command = {
        "id": f"{args.output}_output",
        "command": "set_output",
        "output": args.output,
        "pwm": args.pwm,
        "duration_ms": args.duration_ms,
    }
    return _send_ramps14_motion_command(args, command)


def cmd_mega_ramps14_enable(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    command = {
        "id": f"{args.axis}_enable",
        "command": "set_axis_enabled",
        "axis": args.axis,
        "enabled": args.enabled,
    }
    return _send_ramps14_motion_command(args, command)


def cmd_mega_ramps14_axis_sweep(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    axes = _parse_ramps14_axes(args.axes)
    if not axes:
        return _fail("axis_list_empty", False, {}, 2)
    if args.steps < 1 or args.steps > 30000 or args.slider_steps < 1 or args.slider_steps > 30000:
        return _fail("invalid_sweep_steps", False, {}, 2)
    if args.delay_us < 250 or args.delay_us > 200000 or args.slider_delay_us < 250 or args.slider_delay_us > 200000:
        return _fail("invalid_sweep_timing", False, {}, 2)
    if args.pulse_us < 2 or args.pulse_us > 20 or args.slider_pulse_us < 2 or args.slider_pulse_us > 20:
        return _fail("invalid_sweep_pulse", False, {}, 2)

    output_args = argparse.Namespace(port=args.port, baud=args.baud, dry_run=args.dry_run)
    session_handle = None
    if not args.dry_run:
        open_result, session_handle = _open_ramps14_motion_session(output_args)
        if open_result != 0 or session_handle is None:
            return open_result
        output_args._serial_handle = session_handle

    try:
        for axis in axes:
            is_slider = axis in {"SLIDER", "E0"}
            steps = args.slider_steps if is_slider else args.steps
            delay_us = args.slider_delay_us if is_slider else args.delay_us
            pulse_us = args.slider_pulse_us if is_slider else args.pulse_us
            command_base = {
                "command": "move_axis",
                "axis": axis,
                "steps": steps,
                "pulse_us": pulse_us,
                "start_delay_us": delay_us,
                "min_delay_us": delay_us,
                "accel_steps": 0,
                "decel_steps": 0,
                "step_backend": "digital" if is_slider else "direct",
            }
            for direction in (1, 0):
                command = {
                    **command_base,
                    "id": f"{axis}_sweep_{direction}",
                    "direction": direction,
                    "hold": 1 if direction == 1 else 0,
                }
                if not args.dry_run:
                    print(f"SWEEP axis={axis} direction={direction} steps={steps} delay_us={delay_us}", flush=True)
                result = _send_ramps14_motion_command(output_args, command)
                if result != 0:
                    return result

            disable = {"id": f"{axis}_enable", "command": "set_axis_enabled", "axis": axis, "enabled": 0}
            result = _send_ramps14_motion_command(output_args, disable)
            if result != 0:
                return result
        return 0
    finally:
        if session_handle is not None:
            for axis in axes:
                try:
                    _send_raw_mega_json(
                        session_handle,
                        {"id": f"{axis}_sweep_final_disable", "command": "set_axis_enabled", "axis": axis, "enabled": 0},
                        timeout=5.0,
                    )
                except Exception:
                    pass
            session_handle.close()


def cmd_mega_ramps14_edge_scan(args: argparse.Namespace) -> int:
    if not args.port:
        return _fail("serial_port_required", False, {}, 2)
    if args.home_direction == args.away_direction:
        return _fail("edge_scan_directions_must_differ", False, {}, 2)
    if args.home_max_steps < 1 or args.home_max_steps > 40000:
        return _fail("invalid_edge_home_steps", False, {}, 2)
    if args.away_steps < 1 or args.away_steps > 30000 or args.chunk_steps < 1 or args.chunk_steps > args.away_steps:
        return _fail("invalid_edge_away_steps", False, {}, 2)
    if args.home_delay_us < 250 or args.home_delay_us > 200000 or args.away_delay_us < 250 or args.away_delay_us > 200000:
        return _fail("invalid_edge_timing", False, {}, 2)
    away_start_delay_us = args.away_start_delay_us or args.away_delay_us
    if away_start_delay_us < args.away_delay_us or away_start_delay_us > 250000:
        return _fail("invalid_edge_start_timing", False, {}, 2)
    if args.away_accel_steps < 0 or args.away_accel_steps > 10000 or args.away_decel_steps < 0 or args.away_decel_steps > 10000:
        return _fail("invalid_edge_acceleration", False, {}, 2)
    if args.pulse_us < 2 or args.pulse_us > 20:
        return _fail("invalid_edge_pulse", False, {}, 2)

    transport_args = argparse.Namespace(port=args.port, baud=args.baud, dry_run=args.dry_run)
    limit = f"{args.axis}_MIN"

    home_command = {
        "id": f"{args.axis}_{limit}_edge_home",
        "command": "seek_limit",
        "axis": args.axis,
        "limit": limit,
        "direction": args.home_direction,
        "max_steps": args.home_max_steps,
        "pulse_us": args.pulse_us,
        "start_delay_us": args.home_delay_us,
        "min_delay_us": args.home_delay_us,
        "accel_steps": 0,
        "decel_steps": 0,
        "step_backend": args.step_backend,
    }
    session_handle = None
    if not args.dry_run:
        open_result, session_handle = _open_ramps14_motion_session(transport_args)
        if open_result != 0 or session_handle is None:
            return open_result
        transport_args._serial_handle = session_handle

    try:
        return _run_ramps14_edge_scan(
            args,
            transport_args,
            limit,
            home_command,
            away_start_delay_us,
        )
    finally:
        if session_handle is not None:
            try:
                _send_raw_mega_json(
                    session_handle,
                    {
                        "id": f"{args.axis}_edge_final_disable",
                        "command": "set_axis_enabled",
                        "axis": args.axis,
                        "enabled": 0,
                    },
                    timeout=5.0,
                )
            except Exception:
                pass
            session_handle.close()


def _run_ramps14_edge_scan(
    args: argparse.Namespace,
    transport_args: argparse.Namespace,
    limit: str,
    home_command: dict,
    away_start_delay_us: int,
) -> int:
    print(f"EDGE-SCAN axis={args.axis} phase=home limit={limit} max_steps={args.home_max_steps}", flush=True)
    result, home_response = _exchange_ramps14_motion_command(transport_args, home_command)
    if result != 0:
        return result
    if not args.dry_run and not home_response.get("data", {}).get("limit_hit"):
        _send_ramps14_motion_command(
            transport_args,
            {"id": f"{args.axis}_enable", "command": "set_axis_enabled", "axis": args.axis, "enabled": 0},
        )
        return _fail("edge_home_limit_not_hit", False, home_response, 7)

    remaining = args.away_steps
    completed = 0
    chunk_index = 1
    while remaining > 0:
        chunk_steps = min(args.chunk_steps, remaining)
        completed += chunk_steps
        command = {
            "id": f"{args.axis}_edge_away_{chunk_index}",
            "command": "move_axis",
            "axis": args.axis,
            "direction": args.away_direction,
            "steps": chunk_steps,
            "pulse_us": args.pulse_us,
            "start_delay_us": away_start_delay_us,
            "min_delay_us": args.away_delay_us,
            "accel_steps": args.away_accel_steps,
            "decel_steps": args.away_decel_steps,
            "hold": 1,
            "step_backend": args.step_backend,
        }
        print(f"EDGE-SCAN axis={args.axis} phase=away chunk={chunk_index} steps={chunk_steps} completed={completed}/{args.away_steps}", flush=True)
        result, _ = _exchange_ramps14_motion_command(transport_args, command)
        if result != 0:
            return result
        remaining -= chunk_steps
        chunk_index += 1

    print(f"EDGE-SCAN axis={args.axis} phase=return-home limit={limit} max_steps={args.home_max_steps + args.away_steps}", flush=True)
    return_home_command = {**home_command, "id": f"{args.axis}_{limit}_edge_return", "max_steps": args.home_max_steps + args.away_steps}
    result, return_response = _exchange_ramps14_motion_command(transport_args, return_home_command)
    if result != 0:
        return result

    disable_result = _send_ramps14_motion_command(
        transport_args,
        {"id": f"{args.axis}_enable", "command": "set_axis_enabled", "axis": args.axis, "enabled": 0},
    )
    if disable_result != 0:
        return disable_result
    if not args.dry_run and not return_response.get("data", {}).get("limit_hit"):
        return _fail("edge_return_limit_not_hit", False, return_response, 8)
    return 0


def _resolve_ramps14_timing(args: argparse.Namespace, purpose: str) -> dict[str, int]:
    if purpose == "seek":
        defaults = {
            "pulse_us": 4,
            "start_delay_us": 1850,
            "min_delay_us": 1850,
            "accel_steps": 0,
            "decel_steps": 0,
        }
    elif args.axis == "A":
        # Learned on the connected CookBot A axis on COM6. Other axes keep
        # conservative defaults until their limits and loads are commissioned.
        defaults = {
            "pulse_us": 3,
            "start_delay_us": 1850,
            "min_delay_us": 250,
            "accel_steps": 0,
            "decel_steps": 0,
        }
    elif args.axis in {"SLIDER", "E0"}:
        # Learned on the connected CookBot slider on COM6. The E0 worm-drive
        # axis stalled with very slow 200 ms timing and with faster ramped
        # profiles, but moved repeatably in 600-step cycles at a flat 12 ms
        # step interval through the digitalWrite pulse path.
        defaults = {
            "pulse_us": 8,
            "start_delay_us": 12000,
            "min_delay_us": 12000,
            "accel_steps": 0,
            "decel_steps": 0,
        }
    else:
        defaults = {
            "pulse_us": 4,
            "start_delay_us": 1850,
            "min_delay_us": 1000,
            "accel_steps": 250,
            "decel_steps": 250,
        }

    return {
        "pulse_us": args.pulse_us if args.pulse_us is not None else defaults["pulse_us"],
        "start_delay_us": args.start_delay_us if args.start_delay_us is not None else defaults["start_delay_us"],
        "min_delay_us": args.min_delay_us if args.min_delay_us is not None else defaults["min_delay_us"],
        "accel_steps": args.accel_steps if args.accel_steps is not None else defaults["accel_steps"],
        "decel_steps": args.decel_steps if args.decel_steps is not None else defaults["decel_steps"],
    }


def _resolve_ramps14_step_backend(args: argparse.Namespace) -> str:
    if args.step_backend:
        return args.step_backend
    if args.axis in {"SLIDER", "E0"}:
        return "digital"
    return "direct"


def _parse_ramps14_axes(raw_axes: str) -> list[str]:
    allowed = {"A", "B", "C", "SLIDER", "X", "Y", "Z", "E0", "E1"}
    axes = [axis.strip().upper() for axis in raw_axes.split(",") if axis.strip()]
    invalid = [axis for axis in axes if axis not in allowed]
    if invalid:
        return []
    return axes


def _send_ramps14_motion_command(args: argparse.Namespace, command: dict) -> int:
    result, _ = _exchange_ramps14_motion_command(args, command)
    return result


def _exchange_ramps14_motion_command(args: argparse.Namespace, command: dict) -> tuple[int, dict]:
    if args.dry_run:
        print("DRY RUN:", json.dumps({"port": args.port, "baud": args.baud, "command": command}, indent=2), flush=True)
        return 0, {"ok": True, "data": {}, "error": None}

    existing_handle = getattr(args, "_serial_handle", None)
    if existing_handle is not None:
        return _exchange_ramps14_on_open_handle(existing_handle, command)

    open_result, handle = _open_ramps14_motion_session(args)
    if open_result != 0 or handle is None:
        return open_result, {}

    with handle:
        return _exchange_ramps14_on_open_handle(handle, command)


def _open_ramps14_motion_session(args: argparse.Namespace):
    """Open and verify one Mega session for a complete bounded motion sequence."""

    try:
        import serial  # type: ignore
    except ImportError:
        return _fail("pyserial_not_installed", False, {}, 3), None

    try:
        handle = serial.Serial(args.port, args.baud, timeout=1.0)
    except Exception as exc:
        return _fail(f"serial_open_failed:{args.port}:{exc}", False, {}, 3), None

    time.sleep(2.0)
    handle.reset_input_buffer()
    status = _send_raw_mega_json(
        handle,
        {"id": "motion_status", "command": "get_firmware_status"},
        timeout=5.0,
    )
    if not status.get("ok"):
        handle.close()
        return _fail(f"status_failed:{status}", False, {}, 4), None
    firmware_status = status.get("data", {}).get("firmware_status", {})
    if not firmware_status.get("ramps14_commissioning"):
        handle.close()
        return _fail("ramps14_commissioning_not_enabled", False, firmware_status, 5), None
    return 0, handle


def _exchange_ramps14_on_open_handle(handle, command: dict) -> tuple[int, dict]:
    response = _send_raw_mega_json(
        handle,
        command,
        timeout=_ramps14_command_timeout_seconds(command),
    )
    print(json.dumps(response, indent=2), flush=True)
    if not response.get("ok"):
        return _fail(f"motion_failed:{response.get('error')}", False, response, 6), response
    return 0, response


def _ramps14_command_timeout_seconds(command: dict) -> float:
    motion_command = command.get("command")
    if motion_command not in {"move_axis", "seek_limit"}:
        return 90.0

    step_count = int(command.get("steps") or command.get("max_steps") or 0)
    pulse_us = int(command.get("pulse_us") or 0)
    start_delay_us = int(command.get("start_delay_us") or 0)
    min_delay_us = int(command.get("min_delay_us") or 0)
    worst_step_us = max(start_delay_us, min_delay_us) + pulse_us
    estimated_seconds = (step_count * worst_step_us) / 1_000_000.0
    return max(90.0, min(3600.0, estimated_seconds + 45.0))


def cmd_commissioning_check(args: argparse.Namespace) -> int:
    if args.dry_run:
        print("DRY RUN: commissioning sequence")
        print(" - ADB check")
        if not args.skip_adb_deploy:
            print(" - ADB deploy")
        print(" - PlatformIO build")
        if args.mega_port:
            print(f" - Mega serial probe on {args.mega_port}")
        else:
            print(" - Mega serial probe skipped because --mega-port is not set")
        print(" - backend /product/readiness check remains no_hardware_product_ready")
        return 0

    if cmd_unoq_adb_check(argparse.Namespace(dry_run=False, json=False)) != 0:
        return 1
    if not args.skip_adb_deploy and cmd_unoq_adb_deploy(
        argparse.Namespace(
            target="/home/arduino/cookbot",
            mega_transport="fake",
            bluetooth_address=None,
            bluetooth_channel=1,
            bind="127.0.0.1",
            dry_run=False,
        )
    ) != 0:
        return 2
    if cmd_mega_platformio_build(argparse.Namespace(env="cookbot_mega2560", dry_run=False, simulate_missing_platformio=False)) != 0:
        return 3
    if args.mega_port and cmd_mega_serial_probe(argparse.Namespace(port=args.mega_port, baud=115200, dry_run=False)) != 0:
        return 4
    return 0


def cmd_hardware_doctor(args: argparse.Namespace) -> int:
    report = _hardware_doctor_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_hardware_doctor_report(report)
    if args.strict and not report["toolchain_ready"]:
        return 2
    return 0


def _git_files() -> list[str]:
    output = _run_capture(["git", "ls-files"], check=True)
    return [line.strip() for line in output.splitlines() if line.strip()]


def _hardware_doctor_report(args: argparse.Namespace) -> dict:
    checks: list[dict] = []

    def add_check(name: str, ok: bool, detail: str, *, required: bool = False) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "required": required})

    python_detail = f"{sys.executable} ({platform.python_version()})"
    add_check("python", True, python_detail, required=True)

    git = _tool_status(["git"], ["--version"])
    add_check("git", git["ok"], git["detail"], required=True)
    commit = _run_capture(["git", "rev-parse", "--short", "HEAD"], check=False).strip() if git["ok"] else "unknown"

    node = _tool_status(["node"], ["--version"])
    npm = _tool_status(["npm"], ["--version"])
    arduino = _tool_status(["arduino-cli"], ["version"])
    adb = _tool_status(["adb"], ["version"])
    pio = _platformio_status()

    add_check("node", node["ok"], node["detail"], required=False)
    add_check("npm", npm["ok"], npm["detail"], required=False)
    add_check("arduino_cli", arduino["ok"], arduino["detail"], required=False)
    add_check("platformio", pio["ok"], pio["detail"], required=False)
    add_check("adb", adb["ok"], adb["detail"], required=False)

    project_files = [
        "platformio.ini",
        "mega_firmware/cookbot_mega_firmware/cookbot_mega_firmware.ino",
        "mega_firmware/cookbot_mega_firmware/hardware_config.h",
        "docs/mega_protocol.md",
        "docs/hardware_automation.md",
        "docs/commissioning_runbook.md",
        "docs/release_bundle.md",
        "scripts/hardware_doctor.ps1",
        "scripts/hardware_doctor.sh",
        "scripts/mega_ramps14_jog.ps1",
        "scripts/mega_ramps14_jog.sh",
        "scripts/build_release.ps1",
        "scripts/build_release.sh",
        "scripts/validate_release.ps1",
        "scripts/validate_release.sh",
        "scripts/commissioning_check.ps1",
        "scripts/commissioning_check.sh",
    ]
    missing_project_files = [path for path in project_files if not (ROOT / path).exists()]
    add_check(
        "project_artifacts",
        not missing_project_files,
        "ok" if not missing_project_files else ",".join(missing_project_files),
        required=True,
    )

    adb_devices = _doctor_adb_devices(args.dry_run, adb["path"])
    serial_ports = _doctor_serial_ports(args.dry_run)
    board_list = _doctor_arduino_boards(args.dry_run, arduino["path"])

    add_check(
        "adb_devices",
        bool(adb_devices),
        ",".join(adb_devices) if adb_devices else "no_adb_devices_connected",
        required=False,
    )
    add_check(
        "serial_ports",
        bool(serial_ports),
        ",".join(serial_ports) if serial_ports else "no_serial_ports_detected",
        required=False,
    )
    add_check(
        "arduino_boards",
        bool(board_list),
        "\n".join(board_list[:8]) if board_list else "no_arduino_boards_detected",
        required=False,
    )

    backend = None
    if args.backend_url:
        backend = _doctor_backend(args.backend_url)
        add_check("backend_health", backend.get("health_ok", False), backend.get("health_detail", "not_checked"))
        add_check(
            "backend_product_readiness",
            backend.get("readiness_ok", False),
            backend.get("readiness_detail", "not_checked"),
        )

    required_missing = [check["name"] for check in checks if check["required"] and not check["ok"]]
    recommended_missing = [
        check["name"]
        for check in checks
        if check["name"] in {"arduino_cli", "platformio", "adb", "node", "npm"} and not check["ok"]
    ]
    physical_missing = [name for name, values in {"adb_devices": adb_devices, "serial_ports": serial_ports}.items() if not values]

    return {
        "project": "CookBot",
        "ok": not required_missing,
        "toolchain_ready": not required_missing and not recommended_missing,
        "ready_for_real_motion": False,
        "real_motion_locked": True,
        "dry_run": bool(args.dry_run),
        "platform": platform.platform(),
        "git_commit": commit,
        "checks": checks,
        "required_missing": required_missing,
        "recommended_missing": recommended_missing,
        "physical_connections_missing": physical_missing,
        "adb_devices": adb_devices,
        "serial_ports": serial_ports,
        "arduino_boards": board_list,
        "backend": backend,
        "next_steps": [
            "Connect UNO Q with USB ADB, then run scripts/unoq_adb_check.ps1 or .sh.",
            "Connect Arduino Mega over USB and choose an explicit serial port before upload.",
            "Run locked firmware builds before any upload: scripts/mega_platformio_build.ps1 or .sh.",
            "Use bench firmware only for isolated diagnostic pin pulses; never connect bench pins to motor drivers.",
        ],
    }


def _print_hardware_doctor_report(report: dict) -> None:
    print("CookBot Hardware Doctor")
    print(f"git_commit: {report['git_commit']}")
    print(f"real_motion_locked: {report['real_motion_locked']}")
    print(f"toolchain_ready: {report['toolchain_ready']}")
    for check in report["checks"]:
        state = "ok" if check["ok"] else "missing"
        marker = "required" if check["required"] else "optional"
        print(f"- {check['name']}: {state} ({marker}) - {check['detail']}")
    if report["physical_connections_missing"]:
        print("physical_connections_missing:", ", ".join(report["physical_connections_missing"]))
    if report["next_steps"]:
        print("next_steps:")
        for step in report["next_steps"]:
            print(f"- {step}")


def _tool_status(names: list[str], version_args: list[str]) -> dict:
    for name in names:
        path = shutil.which(name)
        if not path:
            continue
        output = _run_capture([path, *version_args], check=False).strip()
        first_line = output.splitlines()[0] if output.splitlines() else path
        return {"ok": True, "path": path, "detail": first_line}
    return {"ok": False, "path": None, "detail": f"{'/'.join(names)}_not_found"}


def _platformio_status() -> dict:
    command = _platformio_command()
    if not command:
        return {"ok": False, "path": None, "detail": "platformio_not_found"}
    output = _run_capture([*command, "--version"], check=False).strip()
    first_line = output.splitlines()[0] if output.splitlines() else "PlatformIO available"
    return {"ok": True, "path": command[0], "detail": first_line}


def _doctor_adb_devices(dry_run: bool, adb_path: str | None) -> list[str]:
    if dry_run:
        return _mock_devices()
    if not adb_path:
        return []
    return _adb_devices(adb_path)


def _doctor_arduino_boards(dry_run: bool, arduino_path: str | None) -> list[str]:
    if dry_run:
        raw = os.environ.get("COOKBOT_DRY_ARDUINO_BOARDS", "")
        return [item.strip() for item in raw.split(",") if item.strip()]
    if not arduino_path:
        return []
    output = _run_capture([arduino_path, "board", "list"], check=False)
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if len(lines) == 1 and not any(marker in lines[0] for marker in ("COM", "/dev/", "usb", "serial")):
        return []
    return lines


def _doctor_serial_ports(dry_run: bool) -> list[str]:
    if dry_run:
        raw = os.environ.get("COOKBOT_DRY_SERIAL_PORTS", "")
        return [item.strip() for item in raw.split(",") if item.strip()]
    try:
        from serial.tools import list_ports  # type: ignore

        return [port.device for port in list_ports.comports()]
    except Exception:
        if os.name == "nt":
            return sorted(glob.glob("COM*"))
        return sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))


def _doctor_backend(base_url: str) -> dict:
    base = base_url.rstrip("/")
    health = _http_json(f"{base}/health")
    readiness = _http_json(f"{base}/product/readiness")
    return {
        "url": base,
        "health_ok": bool(health.get("ok")),
        "health_detail": health.get("detail", "ok" if health.get("ok") else health.get("error", "unknown")),
        "readiness_ok": bool(readiness.get("ok") and readiness.get("body", {}).get("status") == "no_hardware_product_ready"),
        "readiness_detail": readiness.get("body", {}).get("status") or readiness.get("error", "unknown"),
    }


def _http_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return {"ok": True, "body": json.loads(response.read().decode("utf-8"))}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def _mock_devices() -> list[str]:
    raw = os.environ.get("COOKBOT_DRY_ADB_DEVICES", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _valid_bluetooth_address(value: str) -> bool:
    return bool(re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", value.strip()))


def _is_async_mega_event(line: bytes) -> bool:
    try:
        payload = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and "event" in payload and "ok" not in payload


def _send_raw_mega_json(handle, payload: dict, timeout: float = 3.0) -> dict:
    handle.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
    deadline = time.time() + timeout
    bad_line: bytes | None = None
    while time.time() < deadline:
        line = handle.readline()
        if not line:
            continue
        try:
            response = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            if _is_async_mega_event(line):
                continue
            bad_line = line[:80]
            continue
        if response.get("id") == payload.get("id"):
            return response
    if bad_line:
        return {"ok": False, "error": f"bad_response:{bad_line!r}", "data": {}}
    return {"ok": False, "error": "no_response", "data": {}}


def _adb_devices(adb: str) -> list[str]:
    output = _run_capture([adb, "devices"], check=True)
    devices: list[str] = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def _remote_command_exists(adb: str, command: str) -> bool:
    result = subprocess.run([adb, "shell", "command", "-v", command], capture_output=True, text=True)
    return result.returncode == 0


def _platformio_command() -> list[str] | None:
    direct = shutil.which("pio") or shutil.which("platformio")
    if direct:
        return [direct]
    result = subprocess.run(
        [sys.executable, "-m", "platformio", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return [sys.executable, "-m", "platformio"]
    return None


def _run(command: list[str]) -> int:
    print("+", " ".join(command))
    return subprocess.run(command, cwd=ROOT).returncode


def _run_capture(command: list[str], check: bool) -> str:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=check)
    return result.stdout


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def _fail(message: str, as_json: bool, payload: dict, code: int) -> int:
    payload = {**payload, "ok": False, "error": message}
    _emit(payload, as_json)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
