# Hardware Automation

CookBot hardware automation is split into safe host-side scripts. Browser UI shows status and instructions only; it does not flash boards or run ADB.

## Hardware Doctor

Run this first to see local toolchain, ADB, serial ports, Arduino board list, project artifacts, and optional backend readiness:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/hardware_doctor.ps1 --backend-url http://127.0.0.1:8000
```

Linux/UNO Q:

```bash
bash scripts/hardware_doctor.sh --backend-url http://127.0.0.1:8000
```

The doctor reports missing physical devices without unlocking motion. `ready_for_real_motion` must remain `false`.

The backend also exposes a strict gate report:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/hardware/gate/report
```

This report remains blocked until hardware mode, serial Mega transport, `COOKBOT_HARDWARE_CONFIGURED=true`, verified checklist items, and evidence notes are all present.

## PlatformIO Mega Workflow

Build locked firmware:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mega_platformio_build.ps1
```

Build bench firmware:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mega_platformio_build.ps1 --env cookbot_mega2560_bench
```

Arduino CLI fallback for the same bench compile uses `build.extra_flags`:

```powershell
arduino-cli compile --fqbn arduino:avr:mega --build-property "build.extra_flags=-DCOOKBOT_BENCH_OUTPUTS_ENABLED=1" mega_firmware/cookbot_mega_firmware
```

Upload requires an explicit port:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/mega_platformio_upload.ps1 --port COM5
```

No upload script guesses the port automatically.

## UNO Q ADB Workflow

Check ADB:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/unoq_adb_check.ps1
```

Deploy to UNO Q Linux side:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/unoq_adb_deploy.ps1 --target /home/arduino/cookbot
```

Read logs:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/unoq_adb_logs.ps1
```

If ADB reports UID `0`, the script stops because older UNO Q images used root ADB behavior. Update the UNO Q image before deploying.

## Commissioning

Dry-run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/commissioning_check.ps1 --dry-run
```

With Mega probe:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/commissioning_check.ps1 --mega-port COM5
```

Commissioning keeps `/product/readiness` in `no_hardware_product_ready` unless hardware readiness evidence is completed.
