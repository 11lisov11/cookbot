# CookBot Real Mega Run

The no-hardware MVP defaults to fake Mega. Use real Mega only after wiring, pin map, ESTOP, power, and limits are verified.

Backend serial mode:

```bash
export COOKBOT_MEGA_TRANSPORT=serial
export COOKBOT_SERIAL_PORT=/dev/ttyACM0
export COOKBOT_SERIAL_BAUD=115200
python3 -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

Firmware compile:

```bash
arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware
```

Firmware upload example:

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware
```

The current firmware sketch intentionally returns `hardware_not_configured` for `set_joint` and `set_gripper`. Replace that only after documenting verified hardware values in `docs/vendor_robot_notes.md`.

Before replacing the motion stubs, update `config/hardware_readiness.yaml` with evidence for every readiness item and confirm:

```bash
curl http://127.0.0.1:8000/hardware/readiness
```

Mega hardware compile-time settings live in:

```text
mega_firmware/cookbot_mega_firmware/hardware_config.h
```

Keep `COOKBOT_HARDWARE_CONFIGURED` set to `0` until the hardware readiness gate is complete.
