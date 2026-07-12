# Supervised Commissioning Evidence - 2026-07-12

## Connected controller

- Port: `COM6`
- USB serial adapter: CH340
- Initial firmware reported by the board: `cookbot_mega_firmware 0.1.0`
- Final flashed firmware: `cookbot_mega_firmware 0.2.0`, PlatformIO profile
  `cookbot_mega2560_ramps14_bluetooth`; avrdude flash verification passed
- Protocol: newline-delimited JSON, version 1
- RAMPS commissioning mode: enabled
- Hardware ESTOP input: not configured (`estop_pin=-1`)
- Feedback: `A_MIN`, `B_MIN`, and `C_MIN` only; no encoders and no MAX limits

Every test used a finite step budget. Drivers were explicitly disabled after
each sequence. No stall-to-stop or unbounded movement was used.

## Axis results

### A / RAMPS Y

- Pin map: STEP 60, DIR 61, ENABLE 56, `A_MIN` pin 14.
- Flat `4000us`, 600 steps away: return counts `600`, `599`, `600`.
- Ramp `5000us -> 3500us`, 600 steps away: return counts `600`, `600`, `600`.
- Ramp reaching `3000us`: return count `462`; rejected.
- Repeated ramp reaching `500us`: return count `417`; rejected.
- Current accepted bounded-test profile: `pulse=3us`, start `5000us`, minimum
  `3500us`, acceleration 300 steps, deceleration 100 steps.
- Post-flash v0.2 validation moved 300 steps away, confirmed `A_MIN=false`, and
  returned to `A_MIN` in 299 steps.
- After firmware defaults were hardened, a raw `move_axis` with no timing fields
  selected `5000us -> 3500us` itself, released `A_MIN`, and returned exactly
  300 steps using the raw default `4000us` seek profile.

### B / RAMPS X

- Pin map: STEP 54, DIR 55, ENABLE 38, `B_MIN` pin 3.
- `B_MIN` remained inactive.
- Earlier direction-0 searches up to 10000 steps did not find the switch.
- A direction-1 search was limited to 500 steps and also did not find it; 500
  commanded direction-0 steps followed to restore the commanded displacement.
- B is blocked from long travel until the switch, direction, coil pairs, driver,
  and mechanics are inspected.

### C / RAMPS Z

- Pin map: STEP 46, DIR 48, ENABLE 62, `C_MIN` pin 18.
- Identical 600-step away commands produced return counts `844`, `563`, `577`,
  `356`, `540`, and `453` across conservative flat and ramped profiles.
- One flat `12000us` 600-step away command did not release `C_MIN`.
- C is blocked from positioning. The data is consistent with lost steps,
  coupler/gearbox slip, switch travel, or another mechanical/electrical fault.

### E0 slider

- Pin map: STEP 26, DIR 28, ENABLE 24.
- Symmetric 600-step commands completed at flat `5000us` and `3000us` timings.
- A `10000us -> 2000us` ramp completed 600 commanded steps each direction.
- There is no limit or encoder, so command completion does not prove physical
  travel or repeatability.

## Cooling

The D9 fan was observed through one persistent serial session after a 100-step
E0 out-and-back motion:

- active at 120.6 seconds, 751 ms reported remaining;
- inactive at 125.0 seconds, 0 ms reported remaining.

The configured 120-second post-motion cooldown passed. A commissioning tool
that closes the CH340 serial port can reset Mega and must not be used to measure
the full cooldown interval.

## Backend transport

The USB backend transport was changed from one COM open per request to one
persistent connection. A direct test sent `hello`, `get_firmware_status`, and
`read_inputs` through one handle. A hardware-mode backend on
`http://127.0.0.1:8001` then passed `/health` and all `/diagnostics` Mega checks.
Application shutdown closed the transport cleanly. `/product/readiness`
remained `not_ready` and the real-motion gate remained locked.

Firmware v0.2 also reported Bluetooth UART enabled on Serial2, RX 17, TX 16,
9600 baud. The physical RF link to UNO Q remains unverified.

## Current conclusion

The USB protocol, bounded command execution, A limit repeatability, driver
disable path, and fan cooldown are verified. The robot is not ready for full
travel or unattended motion: B homing is unresolved, C positioning fails,
E0 has no feedback, MAX limits and hardware ESTOP are absent, and A4988 Vref,
Rsense, and microstep jumper states are not recorded.
