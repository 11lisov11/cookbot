# Release Notes

## v0.3.0 Vendor Coordinate Analysis

- Recovered the AXIS4UI Python 3.9 command handlers and Qt defaults from the
  supplied PyInstaller bundle without running the unsigned executable.
- Decompiled the RA Pendant Android application and verified Bluetooth Classic
  SPP framing, jog behavior, command strings, and receive polling.
- Added a strict vendor G-code parser, safe TCP/stdio behavioral emulator, and
  API validation that never forwards vendor commands to Mega.
- Added STEP/RPM/linear-speed and steps-per-unit calculators plus an explicit
  incomplete motion-calibration record.
- Added `get_motion_profile` firmware diagnostics and independent microstep and
  coordinate-calibration verification locks.
- Documented why the current pulse profiles are slow and which physical A4988,
  motor, transmission, and kinematic measurements are still required.

## v0.2.0 Hardware Integration Kit

- Statically analyzed the supplied AXIS4UI desktop and Android controller bundle and recorded the evidenced G-code, speed range, coordinate model, output commands, framing, and Bluetooth SPP UUID without executing the unsigned vendor application.
- Added dual-transport Mega firmware: USB Serial remains available while the same bounded JSON protocol runs over a dedicated `Serial2` Bluetooth UART.
- Added a persistent Linux RFCOMM backend transport with reconnect, request matching, asynchronous-event filtering, bounded responses, diagnostics, and tests.
- Made the USB serial backend transport persistent as well, preventing Mega resets between API commands and closing the port cleanly at application shutdown.
- Added UNO Q ADB checks, Bluetooth capability/pair/probe commands, private systemd environment deployment, and protocol-only commissioning checks.
- Added a restricted Home Assistant package plus a deployable UNO Q Debian hub kit in `C:\\Умный дом`.
- Recorded physically observed RAMPS axis mappings and commissioning results while retaining explicit blockers for inconsistent B homing, slider calibration, hardware ESTOP, limit polarity, current/microstep settings, and the physical Bluetooth module.
- Added ramped symmetric sweep controls, mandatory MIN-switch release verification, and a full D9 cooldown observer; the connected fan passed the 120-second cooldown test.
- Flashed and verified firmware v0.2 on the connected Mega at COM6. A passed bounded repeatability testing; B and C remain explicitly blocked by current hardware results.
- Kept normal firmware and autonomous motion locked. The RAMPS builds remain supervised commissioning profiles, not production motion control.

## v0.1.0 No-Hardware Product

- FastAPI backend with simulator, fake Mega, mock camera, mock AI, recipe engine, safety validation, diagnostics, logs, schemas, acceptance, backup, restore validation, and product readiness endpoints.
- Mobile-first PWA with first-run setup, sticky ESTOP, tabbed Control/Recipes/Diagnostics/Calibration/Hardware Gate/Settings views, backup export, and restore validation.
- Fake Mega TCP/in-process protocol for no-hardware checks.
- Arduino Mega firmware skeleton that compiles while keeping hardware outputs disabled until verified configuration is added.
- Documentation for architecture, safety, calibration, no-hardware testing, mobile use, troubleshooting, and release checks.
- GitHub Actions CI for backend tests, compile checks, web build, smoke tests, and optional firmware compile.

Real cooking, heating, knife handling, relay control, and real motor movement are not enabled in this release.

## Hardware Integration Prep

- Added PlatformIO/VS Code workflow for Arduino Mega 2560 locked firmware and bench-only diagnostic builds.
- Added ADB scripts for UNO Q Linux-side check, deploy, logs, and commissioning dry-runs.
- Extended Mega protocol with firmware status, input readback, and compile-time-locked bench output commands.
- Added hardware doctor scripts plus backend/PWA commissioning guide for local toolchain, ADB, serial, PlatformIO, and backend readiness reporting.
- Added local release bundle builder/validator with SHA256 manifest and explicit real-motion lock fields.
- Added strict hardware gate report endpoint and PWA blockers list for future evidence-driven hardware readiness.
- Real motion remains blocked until verified hardware readiness evidence is complete.
