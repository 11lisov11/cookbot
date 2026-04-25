# Commissioning Runbook

This runbook prepares CookBot for bench hardware work without enabling real motion. The default firmware keeps `COOKBOT_HARDWARE_CONFIGURED=0`; the backend must continue to report `ready_for_real_motion=false`.

## 1. Local Hardware Doctor

Run the doctor before connecting or flashing anything:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/hardware_doctor.ps1 --backend-url http://127.0.0.1:8000
```

Linux/UNO Q shell:

```bash
bash scripts/hardware_doctor.sh --backend-url http://127.0.0.1:8000
```

The report checks Python, Git, Arduino CLI, PlatformIO, ADB, Node/npm, project artifacts, ADB devices, serial ports, Arduino board list, and optional backend readiness. Missing physical devices are reported but do not unlock motion.

## 2. UNO Q ADB Check

Connect UNO Q over USB and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/unoq_adb_check.ps1
```

If the script reports root ADB behavior, stop and update the UNO Q image before deployment.

## 3. Deploy Backend To UNO Q

Only after ADB is healthy:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/unoq_adb_deploy.ps1 --target /home/arduino/cookbot
```

The script pushes tracked files, installs Python dependencies, builds the PWA when npm is available, installs the user systemd unit, and restarts the backend.

## 4. Build Locked Mega Firmware

Build the default Mega firmware first:

```powershell
python -m platformio run -e cookbot_mega2560
```

Arduino CLI fallback:

```powershell
arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware
```

This firmware must reject `set_joint` and `set_gripper` until verified pin map, driver type, limit polarity, axis limits, gripper wiring, and ESTOP evidence are filled.

## 5. Upload With Explicit Port

List ports with the doctor or Arduino CLI, then choose the port explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mega_platformio_upload.ps1 --port COM5
```

Do not use auto-upload or guessed ports.

## 6. Serial Protocol Self-Test

Probe only safe protocol commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mega_serial_probe.ps1 --port COM5
```

The probe sends `hello`, `get_firmware_status`, `self_test`, and `read_inputs`. It does not send motion commands.

## 7. Optional Bench Outputs

Bench outputs are for isolated pin pulses only. Never connect a bench test pin to a motor driver input, relay, heater, blade actuator, pump, or unknown circuit.

Build bench firmware:

```powershell
python -m platformio run -e cookbot_mega2560_bench
```

Bench pulse requirements:

- compile-time `COOKBOT_BENCH_OUTPUTS_ENABLED=1`
- ESTOP clear
- `bench_unlock` with `confirm="BENCH_ONLY"`
- explicit test pin
- duration at or below `COOKBOT_BENCH_MAX_PULSE_MS`

After one pulse the firmware locks bench mode again.

## 8. Final No-Hardware Readiness Check

Commissioning must still leave the product in no-hardware-ready state:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/product/readiness
```

Expected result:

- `status` is `no_hardware_product_ready`
- `ok` is `true`
- `hardware_readiness.ready_for_real_motion` is `false`
- `real_motion_locked` remains true in hardware doctor output
