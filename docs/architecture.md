# CookBot Architecture

CookBot separates high-level orchestration from motion control.

- UNO Q Linux side: FastAPI backend, PWA serving, WebSocket state stream, mock/real camera boundary, AI client boundary, recipe engine, safety validation, structured logs, and Mega transport.
- Arduino Mega: low-level motion controller, limit switch handling, homing, ESTOP, watchdog, and final motion limits.
- Phone: local PWA client for camera, manual controls, homing, calibration, ESTOP, AI command review, and recipe execution.

AI never drives motors directly. It may only return a strict JSON plan, and CookBot validates the plan before any action.

The no-hardware MVP uses `CookBotSimulator` plus fake Mega to exercise backend, UI, recipe, and safety behavior without hardware.

Runtime observability:

- `/diagnostics` checks backend, Mega hello/ping/state/capabilities, camera, recipes, workspace, and calibration.
- `/logs` exposes sanitized structured JSONL events.
- `/schemas` exposes JSON schemas for the core CookBot API contracts.
- `/simulator/faults` lets tests exercise limit-switch and transport-like failure paths without real motors.
