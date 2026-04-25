# CookBot

[![CookBot checks](https://github.com/11lisov11/cookbot/actions/workflows/check.yml/badge.svg)](https://github.com/11lisov11/cookbot/actions/workflows/check.yml)

CookBot Robot Cook Assistant is a no-hardware MVP for an Arduino UNO Q + Arduino Mega robot cook workflow. The UNO Q runs the FastAPI backend, PWA, camera/AI mocks, safety layer, and recipe engine. The Arduino Mega remains the low-level motion controller.

This repository starts safe by default: simulator mode, fake Mega, mock camera, and mock AI. It does not require real hardware, a camera, or an AI API key.

Current status: v0.1 is a finished no-hardware product. It is installable, testable, documented, demo-ready, and CI-backed. It is not ready for real motor movement or real cooking.

## Not Ready For Real Motion

Real motion remains locked. Do not connect motors expecting movement from this release. The firmware has no real pin map, the hardware readiness file has no verified evidence, and the backend treats real-motion readiness as a hardware-only blocker. Heating, knives, relays, raw Mega commands, arbitrary code execution, and direct autonomous cooking are rejected.

## Quick Start

```powershell
python -m pip install -r requirements-dev.txt
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/health` to confirm the backend is running.

For the PWA:

```powershell
cd web
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. To open from a phone on the same LAN, explicitly set a LAN bind address for backend/dev server and keep it on the local network.

## No-Hardware Mode

Defaults:

```text
COOKBOT_MODE=simulator
COOKBOT_MEGA_TRANSPORT=fake
COOKBOT_CAMERA=mock
COOKBOT_AI=mock
COOKBOT_BIND=127.0.0.1
```

Useful commands:

```powershell
python -m pytest tests/
python -m compileall unoq_backend
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
```

Linux/UNO Q:

```bash
bash scripts/check_all.sh
```

Detailed startup docs:

- `docs/first_run.md`
- `docs/implementation_report.md`
- `docs/real_mega_run.md`
- `docs/no_hardware_testing.md`
- `docs/mega_protocol.md`
- `docs/hardware_automation.md`
- `docs/commissioning_runbook.md`
- `docs/release_bundle.md`

## Fake Mega

Run the standalone TCP fake Mega:

```powershell
python -m unoq_backend.fake_mega
```

Use it from the backend:

```powershell
$env:COOKBOT_MEGA_TRANSPORT="fake_tcp"
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

The default backend uses an in-process fake Mega so the app starts with one command.

## Homing and Calibration

1. Press `Home` in the PWA or call `POST /home`.
2. For simulator-only testing, press `Calibrate` or call `POST /calibration/simulate`.
3. After `ESTOP` or `POST /estop/clear`, CookBot requires homing again.

The simulator exposes `joint_1`, `joint_2`, `joint_3`, and `gripper` as safe placeholders only. They do not claim to match the real AliExpress arm.

## API

- `GET /health`
- `GET /settings`
- `GET /version`
- `GET /diagnostics`
- `GET /state`
- `GET /camera/snapshot`
- `GET /camera/stream`
- `POST /estop`
- `POST /estop/clear`
- `POST /home`
- `GET /calibration/status`
- `POST /calibration/simulate`
- `POST /calibration/save`
- `POST /calibration/reset`
- `GET /calibration/wizard/status`
- `POST /calibration/wizard/start`
- `POST /calibration/wizard/advance`
- `POST /calibration/wizard/reset`
- `POST /joints/{id}/move`
- `POST /gripper`
- `POST /ai/command`
- `GET /recipes`
- `POST /recipes/{id}/preflight`
- `POST /recipes/{id}/run`
- `GET /recipes/runtime/status`
- `POST /recipes/runtime/pause`
- `POST /recipes/runtime/resume`
- `POST /recipes/runtime/abort`
- `GET /workspace`
- `GET /hardware/readiness`
- `GET /schemas`
- `GET /acceptance`
- `GET /product/readiness`
- `GET /commissioning/guide`
- `GET /export`
- `GET /backup`
- `POST /restore/validate`
- `GET /logs`
- `POST /simulator/faults`
- `DELETE /simulator/faults`
- `GET /ws/state`

## Firmware

Compile the Mega skeleton:

```powershell
arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware
```

PlatformIO/VS Code workflow:

```powershell
pio run -e cookbot_mega2560
pio run -e cookbot_mega2560_bench
```

The sketch intentionally rejects real motion until the pin map, drivers, limits, and hardware safety wiring are verified.

Before connecting boards, run the local hardware doctor:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/hardware_doctor.ps1 --backend-url http://127.0.0.1:8000
```

Upload through PlatformIO requires an explicit serial port:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mega_platformio_upload.ps1 --port COM5
```

UNO Q ADB deployment starts with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/unoq_adb_check.ps1
```

## Current Mock/Simulator Features

- Mega protocol is implemented by fake Mega.
- Fake Mega reports protocol capabilities and supports simulator fault injection.
- Fake Mega mirrors hardware prep commands such as `get_firmware_status`, `read_inputs`, `bench_unlock`, and `bench_test_output`.
- Camera is a generated SVG snapshot.
- Optional `COOKBOT_CAMERA=libcamera` captures snapshots through `libcamera-still` on Linux/UNO Q.
- The PWA includes a manifest and service worker for an installable local app shell.
- AI is a deterministic mock that lets CookBot safety reject forbidden cooking actions.
- Recipes are YAML files; `dry_run_stir_demo`, `dry_run_pick_place_demo`, `camera_inspection_demo`, and `gripper_cycle_demo` are no-heat demos. `supervised_scrambled_eggs` is locked.
- No heating, knife handling, relay control, cloud backend, ROS2, Docker, or internet dependency is used in the MVP.

## Diagnostics and Fault Injection

Run diagnostics:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/diagnostics
```

Inject a simulator fault:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/simulator/faults -Method Post -ContentType application/json -Body '{"code":"limit_switch_stuck_min","joint_id":"joint_1"}'
```

Clear simulator faults:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/simulator/faults -Method Delete
```

Hardware readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/hardware/readiness
```

Real motion remains locked until every readiness item in `config/hardware_readiness.yaml` is verified with evidence.

No-hardware acceptance report:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/acceptance
```

Product readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/product/readiness
```

Safe backup:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/backup
```

Optional local API token:

```powershell
$env:COOKBOT_API_TOKEN="change-me"
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

The PWA Settings panel stores this token in browser local storage and sends it as `X-CookBot-Token`.

## Release Bundle

After checks pass, build and validate a local handoff package:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release.ps1 --output dist/release --json
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1 --latest --output dist/release --json
```

The zip contains source/docs/config/scripts plus generated `web/dist` and PlatformIO Mega firmware artifacts when present. Its manifest keeps `real_motion_locked=true` and `ready_for_real_motion=false`.

## OpenAI-Compatible AI Boundary

The default is mock AI. To use an OpenAI-compatible API later:

```powershell
$env:COOKBOT_AI="openai_compatible"
$env:COOKBOT_AI_BASE_URL="https://api.openai.com/v1"
$env:COOKBOT_AI_API_KEY="..."
$env:COOKBOT_AI_MODEL="gpt-4o-mini"
```

CookBot still validates the returned strict JSON plan and rejects forbidden steps before any motion command.

## Systemd Templates

Templates are in `deploy/systemd/`:

- `cookbot-backend.service`
- `cookbot-fake-mega.service`

Copy them to `/etc/systemd/system/` on UNO Q only after choosing the final install path and bind address.

Optional installer for UNO Q:

```bash
sudo bash scripts/install_systemd.sh /opt/cookbot
```

Review `.env.example` and service bind addresses before exposing the UI on a LAN.
