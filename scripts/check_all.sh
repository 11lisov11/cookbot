#!/usr/bin/env bash
set -euo pipefail

echo "CookBot: pytest"
python -m pytest tests/

echo "CookBot: compileall"
python -m compileall unoq_backend

echo "CookBot: backend smoke"
export COOKBOT_MODE=simulator
export COOKBOT_MEGA_TRANSPORT=fake
export COOKBOT_CAMERA=mock
export COOKBOT_AI=mock
PORT=8766
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port "$PORT" >/tmp/cookbot-backend.log 2>&1 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" >/dev/null 2>&1 || true' EXIT
python scripts/smoke_backend.py "http://127.0.0.1:$PORT"
kill "$BACKEND_PID" >/dev/null 2>&1 || true
trap - EXIT

echo "CookBot: fake Mega smoke"
python scripts/smoke_fake_mega.py

echo "CookBot: web build"
(cd web && npm install && npm run build)

echo "CookBot: Arduino Mega compile"
if command -v arduino-cli >/dev/null 2>&1; then
  arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware
  arduino-cli compile --fqbn arduino:avr:mega --build-property "build.extra_flags=-DCOOKBOT_BENCH_OUTPUTS_ENABLED=1" mega_firmware/cookbot_mega_firmware
else
  echo "WARNING: arduino-cli not found; skipping firmware compile"
fi

echo "CookBot: PlatformIO Mega build"
if command -v pio >/dev/null 2>&1; then
  pio run -e cookbot_mega2560
  pio run -e cookbot_mega2560_bench
elif python -c "import platformio" >/dev/null 2>&1; then
  python -m platformio run -e cookbot_mega2560
  python -m platformio run -e cookbot_mega2560_bench
else
  echo "WARNING: PlatformIO pio not found; skipping PlatformIO compile"
fi

echo "CookBot: hardware automation dry-runs"
python scripts/hardware_tooling.py hardware-doctor --dry-run --json
python scripts/hardware_tooling.py unoq-adb-deploy --dry-run
python scripts/hardware_tooling.py unoq-adb-logs --dry-run
python scripts/hardware_tooling.py mega-platformio-upload --dry-run --port DRY_RUN_PORT
python scripts/hardware_tooling.py mega-serial-probe --dry-run --port DRY_RUN_PORT
python scripts/hardware_tooling.py commissioning-check --dry-run

echo "CookBot: release bundle"
python scripts/release_tooling.py build --output dist/release --json
python scripts/release_tooling.py validate --latest --output dist/release --json

echo "CookBot: all checks passed"
