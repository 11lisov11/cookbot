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

## 9. RAMPS 1.4 Micro-Jog Commissioning

If the connected shield is physically verified as RAMPS 1.4-style hardware, a
temporary jog-only firmware can be built and uploaded:

```powershell
python -m platformio run -e cookbot_mega2560_ramps14_commissioning
python scripts\hardware_tooling.py mega-platformio-upload --env cookbot_mega2560_ramps14_commissioning --port COM6
```

The jog command is deliberately tiny and manual. It does not home, queue motion,
run recipes, or keep drivers enabled after the pulse:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\mega_ramps14_jog.ps1 --port COM6 --axis B --steps 8 --return-to-start
```

For real axis learning, use the firmware-side bounded commands instead of many
small serial jogs:

```powershell
python scripts\hardware_tooling.py mega-ramps14-move --port COM6 --axis A --direction 1 --steps 1200
python scripts\hardware_tooling.py mega-ramps14-seek-limit --port COM6 --axis A --limit A_MIN --direction 0 --max-steps 2500 --min-delay-us 1850
```

`mega-ramps14-move` uses the learned rapid profile only for `--axis A`.
Other axes keep conservative timing until they are commissioned.

Observed on the first CookBot A-axis commissioning pass:

- `A` home direction toward `A_MIN`: `0`
- `A` away direction: `1`
- `A` smooth reliable setting with acceleration: `start_delay_us=7000`, `min_delay_us=1850`, `accel_steps=500`
- `A` sharp reliable setting, matching the draw-bot style of sending one motion command to the controller: `start_delay_us=1850`, `min_delay_us=1850`, `accel_steps=0`
- `A` sharp repeatability check: after a `1200` step away move, three consecutive seeks returned `1264` steps at `1850us`
- `A` sharp `1750us` was not repeatable: observed `1263`, `1264`, and `1265`, so do not use it as a learned default
- `A` fast move-away setting: `start_delay_us=1850`, `min_delay_us=1000`, `accel_steps=250`; after each `1200` step away move, stable `1850us` seeks returned `1264`, `1264`, `1263`
- `A` fast `900us` move-away was not stable enough: observed return spread of `42` steps
- `A` fast seek toward the limit at `1600us` was not stable enough: observed `1264`, `1262`, `1265`; keep `seek_limit` default at `1850us`
- `A` rapid CLI default after direct-port/trapezoid firmware update: `pulse_us=3`, `start_delay_us=1850`, `min_delay_us=250`, `accel_steps=0`, `decel_steps=0`
- `A` rapid default timing: `1200` away steps completed in `0.383s`; three slow seeks returned `1264`, `1264`, `1264`
- `A` smoother rapid fallback: `pulse_us=3`, `min_delay_us=250`, `accel_steps=50`, `decel_steps=50`; `1200` away steps completed in `0.475s`, seeks returned `1264`, `1264`, `1264`
- `A` CLI-default confirmation: a plain `mega-ramps14-move --axis A --direction 1 --steps 1200` returned to `A_MIN` in `1264` seek steps
- `B` home direction toward `B_MIN`: `0`; a bounded `4000us` seek hit `B_MIN` in `2052` steps.
- `C` home direction toward `C_MIN`: `0`; a bounded `4000us` seek hit `C_MIN` in `3521` steps.
- After drivers are disabled, some axes may mechanically relax off the switch; rely on the `seek_limit` `limit_hit=true` result for the homing event and re-check latching separately if holding at the switch matters.
- A supervised all-axis sweep has passed on `A`, `B`, `C`, and `E0` using `mega-ramps14-axis-sweep`; this verifies command delivery and basic short motion, not absolute homing or calibration.
- Bounded edge-scan results at `8000us`, chunked `500` steps:
  - `A`: `A_MIN` was already active, moved away `5000` steps, returned to `A_MIN` in `8055` seek steps.
  - `C`: homed to `C_MIN` in `5146` steps, moved away `5000` steps, returned to `C_MIN` in `5047` seek steps.
  - `B`: failed to reach `B_MIN` in `12000` home steps, so away-edge movement was blocked by the tool. Inspect B driver, coil pairs, wiring, switch reach, and mechanics before any larger B scan.

The reference draw-bot implementation in `C:\tchmp` sends FluidNC `G0`/`G1`
commands with a feed rate and lets the controller execute the motion. CookBot's
RAMPS commissioning commands now follow the same shape: one bounded command is
sent to Mega, then Mega clocks the motor and checks the limit input internally.
The commissioning firmware now uses direct port writes for STEP pulses and
supports `decel_steps` for fixed moves; limit seeks still use the slower
`1850us` profile for repeatability.
For `SLIDER`/`E0`, long `move_axis` commands default to `step_backend=digital`,
which intentionally matches the original `jog_axis` `digitalWrite` pulse path.
Use `--step-backend direct` only when that axis has been proven reliable.

Use `mega-motion-calc` before judging whether an axis is "slow". Output speed is:

```text
output_rpm = step_rate_hz * 60 / (motor_steps_per_rev * microstep * gear_ratio)
```

For example, `1000` STEP/s with a `200` step motor, `1/16` microstepping, and a
`50:1` gearbox is only `0.375` output RPM. The helper prints the same math:

```powershell
python scripts\hardware_tooling.py mega-motion-calc --delay-us 1000 --pulse-us 8 --microstep 16 --gear-ratio 50 --json
```

Current user-inspected gearbox notes:

- `A` and `B` lift-arm motors: `P/N FLE 42-010`, `S/N H202600130`; likely `10:1`.
- `C` motor: `P/N FLE 42-010`, `S/N H202600230`; likely `10:1`.
- `E0` slider: no external gearbox; use `gear_ratio=1` for motor-shaft RPM, then convert to linear travel from the measured screw or belt pitch.

With `1/16` microstepping and an inferred `10:1` gearbox, the A rapid profile
(`pulse_us=3`, `min_delay_us=250`) is about `7.4` output RPM. The `4000us` limit
seek profile is about `0.47` output RPM. That is expected: homing is intentionally
slow and torque-friendly.

For a short all-axis supervised check:

```powershell
python scripts\hardware_tooling.py mega-ramps14-axis-sweep --port COM6 --axes A,B,C,E0 --steps 300 --slider-steps 300
```

For a bounded "edge-to-edge" style check without a second/max limit switch, use
`mega-ramps14-edge-scan`. It first requires a successful `*_MIN` seek, then moves
away in chunks for a fixed step budget, then returns to `*_MIN`.

```powershell
python scripts\hardware_tooling.py mega-ramps14-edge-scan --port COM6 --axis A --away-steps 5000 --chunk-steps 1000
```

Do not implement "move until the motor stalls" with the current RAMPS/A4988-style
commissioning setup. The firmware has no encoder, current sensor, TMC StallGuard,
or max-limit input, so it cannot distinguish a mechanical stop from normal
movement. A stall-based edge finder would keep emitting STEP pulses into a hard
stop and can overheat the driver, skip position, or damage the gearbox.

Axis mapping for this temporary commissioning mode:

- `B`/`X`: STEP 54, DIR 55, ENABLE 38
- `A`/`Y`: STEP 60, DIR 61, ENABLE 56
- `C`/`Z`: STEP 46, DIR 48, ENABLE 62
- `SLIDER`/`E0`: STEP 26, DIR 28, ENABLE 24. This is the verified slider channel on the connected controller.
- `E1`: STEP 36, DIR 34, ENABLE 30. This remains available by explicit name only.

Stepper torque notes:

- Stepper current is set physically on the stepstick driver's trim potentiometer; the firmware cannot raise current on A4988/DRV8825-style plug-in drivers.
- Use slower timing for more usable torque while moving, for example `--start-delay-us 6000 --min-delay-us 2500 --accel-steps 600 --decel-steps 600`.
- The verified `E0` slider uses `step_backend=digital` so long moves match the original `jog_axis` pulse path. The current learned profile is a flat `12000us` step interval: `pulse_us=8`, `start_delay_us=12000`, `min_delay_us=12000`, `accel_steps=0`, `decel_steps=0`.
- Observed slider behavior: four back-and-forth cycles of `600` steps moved on the learned flat `12000us` profile; a larger `6250` step ramped profile with `min_delay_us=5000` did not move reliably. For long tests, repeat short verified chunks instead of sending one large unverified ramp.
- The commissioning firmware accepts very slow timing up to `start_delay_us=250000` and `min_delay_us=200000`; the PC tool raises the serial timeout from the requested step count so the command can finish normally.
- Use `--hold` on `mega-ramps14-move`, or `mega-ramps14-enable --enabled 1`, to keep a driver energized after a move. Disable it after supervised testing to avoid heating.

RAMPS MOSFET output checks:

```powershell
python scripts\hardware_tooling.py mega-ramps14-output --port COM6 --output D9 --pwm 255
python scripts\hardware_tooling.py mega-ramps14-output --port COM6 --output D9 --pwm 0
```

The connected controller's fan is verified on `D9`. The RAMPS commissioning
firmware automatically turns `D9` on before every supervised motor movement
(`jog_axis`, `move_axis`, or `seek_limit`) and leaves it on for driver cooling.
Use `mega-ramps14-output --output D9 --pwm 0` to turn it off after testing.
`D8` and `D10` remain available for supervised commissioning, but must not be
treated as heaters or autonomous cooking outputs.

Do not treat this mode as production motion control. Return to the locked default
firmware after the bench check unless you are actively supervising the robot.
