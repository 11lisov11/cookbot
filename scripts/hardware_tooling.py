import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(prog="cookbot-hardware-tooling")
    subcommands = parser.add_subparsers(dest="command", required=True)

    adb_check = subcommands.add_parser("unoq-adb-check")
    adb_check.add_argument("--dry-run", action="store_true")
    adb_check.add_argument("--json", action="store_true")
    adb_check.set_defaults(fn=cmd_unoq_adb_check)

    adb_deploy = subcommands.add_parser("unoq-adb-deploy")
    adb_deploy.add_argument("--target", default="/home/arduino/cookbot")
    adb_deploy.add_argument("--dry-run", action="store_true")
    adb_deploy.set_defaults(fn=cmd_unoq_adb_deploy)

    adb_logs = subcommands.add_parser("unoq-adb-logs")
    adb_logs.add_argument("--dry-run", action="store_true")
    adb_logs.set_defaults(fn=cmd_unoq_adb_logs)

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

    commissioning = subcommands.add_parser("commissioning-check")
    commissioning.add_argument("--mega-port")
    commissioning.add_argument("--skip-adb-deploy", action="store_true")
    commissioning.add_argument("--dry-run", action="store_true")
    commissioning.set_defaults(fn=cmd_commissioning_check)

    args = parser.parse_args()
    return int(args.fn(args))


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
    if args.dry_run:
        print(f"DRY RUN: would deploy tracked CookBot files to UNO Q at {args.target}")
        print("DRY RUN: would install dependencies, install user systemd units, and restart backend")
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

    remote = (
        f"cd {args.target} && "
        "python3 -m pip install --user -r requirements.txt && "
        "if command -v npm >/dev/null 2>&1; then cd web && npm install && npm run build && cd ..; fi && "
        "mkdir -p ~/.config/systemd/user && "
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

    with serial.Serial(args.port, args.baud, timeout=2.0) as handle:
        for command in ("hello", "get_firmware_status", "self_test", "read_inputs"):
            handle.write(encode_request(build_request(command)))
            line = handle.readline()
            if not line:
                return _fail(f"no_response:{command}", False, {}, 4)
            response = decode_response(line)
            if not response.ok:
                return _fail(f"mega_error:{command}:{response.error}", False, {}, 5)
            print(json.dumps(response.model_dump(mode="json"), indent=2))
    return 0


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
    if not args.skip_adb_deploy and cmd_unoq_adb_deploy(argparse.Namespace(target="/home/arduino/cookbot", dry_run=False)) != 0:
        return 2
    if cmd_mega_platformio_build(argparse.Namespace(env="cookbot_mega2560", dry_run=False, simulate_missing_platformio=False)) != 0:
        return 3
    if args.mega_port and cmd_mega_serial_probe(argparse.Namespace(port=args.mega_port, baud=115200, dry_run=False)) != 0:
        return 4
    return 0


def _git_files() -> list[str]:
    output = _run_capture(["git", "ls-files"], check=True)
    return [line.strip() for line in output.splitlines() if line.strip()]


def _mock_devices() -> list[str]:
    raw = os.environ.get("COOKBOT_DRY_ADB_DEVICES", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


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
