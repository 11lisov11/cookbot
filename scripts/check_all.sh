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
else
  echo "WARNING: arduino-cli not found; skipping firmware compile"
fi

echo "CookBot: all checks passed"

