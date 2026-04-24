# CookBot Implementation Report

Generated for the current no-hardware software stage.

## Created Subsystems

- Python FastAPI backend in `unoq_backend/`.
- React/Vite mobile PWA in `web/`.
- Fake Mega TCP/in-process simulator.
- Arduino Mega firmware skeleton in `mega_firmware/cookbot_mega_firmware/`.
- YAML recipes in `recipes/`.
- Configuration files in `config/`.
- Documentation in `docs/`.
- Windows and Linux check scripts in `scripts/`.
- Systemd and WireGuard templates in `deploy/`.

## How to Run No-Hardware Mode

```powershell
python -m pip install -r requirements-dev.txt
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

## How to Run Fake Mega

The backend uses an in-process fake Mega by default. Standalone fake Mega:

```powershell
python -m unoq_backend.fake_mega
```

Then run backend with:

```powershell
$env:COOKBOT_MEGA_TRANSPORT="fake_tcp"
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

## How to Run Tests

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
```

Linux/UNO Q:

```bash
bash scripts/check_all.sh
```

Current passing checks:

- pytest suite;
- Python compileall;
- backend smoke;
- fake Mega smoke;
- web build;
- Arduino Mega compile.

## Mock/Simulator Features

- `COOKBOT_MEGA_TRANSPORT=fake` simulates Mega.
- `COOKBOT_CAMERA=mock` generates snapshots and stream frames.
- `COOKBOT_AI=mock` returns deterministic plans for safety tests.
- `dry_run_stir_demo` runs after homing.
- `supervised_scrambled_eggs` is locked.
- `/simulator/faults` injects no-hardware faults.

## Real Hardware Still Required

Real motion is intentionally locked until these are verified:

- Mega pin map;
- motor/servo driver types;
- limit switch polarity;
- external power and common ground;
- hardware ESTOP;
- real axis limits;
- safe homing direction;
- low-power motion test.

Track those in `config/hardware_readiness.yaml` and `docs/vendor_robot_notes.md`.

## Real Mega Path

Compile firmware:

```powershell
arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware
```

Real serial backend mode:

```powershell
$env:COOKBOT_MEGA_TRANSPORT="serial"
$env:COOKBOT_SERIAL_PORT="COMx"
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

The current firmware reports capabilities and state, but rejects real `set_joint` and `set_gripper` until `hardware_config.h` is completed from verified hardware data.

