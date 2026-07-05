# CookBot Mega Protocol

CookBot Mega uses newline-delimited JSON over USB Serial or TCP fake Mega.

Request:

```json
{"id":"client-generated-id","command":"ping","args":{}}
```

Response:

```json
{"id":"client-generated-id","ok":true,"data":{"pong":true},"error":null}
```

## Core Commands

- `hello`: firmware identity, protocol version, capabilities.
- `ping`: transport liveness.
- `get_state`: current `SystemState` payload.
- `get_capabilities`: supported command list and safety flags.
- `get_hardware_config`: verified hardware configuration or placeholder values.
- `get_limit_switches`: limit switch state.
- `self_test`: non-motion firmware self-test.
- `get_firmware_status`: firmware version, ESTOP, watchdog, and bench lock status.
- `read_inputs`: ESTOP/limit input snapshot.
- `estop`: immediately disables motion and bench unlock.
- `clear_estop`: clears ESTOP and requires re-home.
- `enable_motion`, `home_all`, `set_joint`, `set_gripper`: motion lifecycle commands. Real Mega firmware keeps real motion disabled until hardware readiness is verified.

## RAMPS 1.4 Commissioning Command

- `jog_axis`: temporary jog-only command available only when firmware is built with `COOKBOT_RAMPS14_COMMISSIONING=1`.
- Request fields are top-level JSON fields for the commissioning sketch: `axis`, `steps`, `direction`, `pulse_us`, and `step_delay_us`.
- Supported axes are `A`, `B`, `C`, `SLIDER`, and aliases `X`, `Y`, `Z`, `E0`, `E1`. `SLIDER` maps to RAMPS `E0` on the connected controller.
- `steps` is capped at 25 per command. Drivers are disabled immediately after each jog pulse.
- `move_axis`: bounded long move inside Mega with trapezoid profiling. Fields: `axis`, `direction`, `steps`, `pulse_us`, `start_delay_us`, `min_delay_us`, `accel_steps`, `decel_steps`.
- `seek_limit`: bounded limit seek inside Mega with acceleration and per-step limit checks. Fields: `axis`, `limit`, `direction`, `max_steps`, `pulse_us`, `start_delay_us`, `min_delay_us`, `accel_steps`, `decel_steps`.
- `set_axis_enabled`: enables or disables one RAMPS stepper driver. Fields: `axis`, `enabled` (`0` or `1`). ESTOP clears all driver enables.
- `move_axis` and `seek_limit` disable the driver at command completion.
- `set_output`: supervised RAMPS MOSFET output control for `D8`, `D9`, or `D10`. Fields: `output`, `pwm` (`0..255`), optional `duration_ms` (`0` latches until changed). ESTOP clears all RAMPS outputs.
- These commands are for supervised bench commissioning only. They are not autonomous motion control and must not be used by recipes or AI.

## Bench Commands

- `bench_unlock` requires `{"confirm":"BENCH_ONLY"}` and only works when `COOKBOT_BENCH_OUTPUTS_ENABLED=1`.
- `bench_test_output` requires `{"pin":2..53,"duration_ms":1..250}` and only works after `bench_unlock`.
- Bench output pulses are diagnostic pin tests only. They must not be wired to motor drivers during first bring-up.
- ESTOP clears the bench unlock.

## Error Codes

- `hardware_not_configured`: real hardware pin map is not configured.
- `bench_outputs_disabled`: firmware was compiled without bench outputs.
- `bench_confirm_required`: unlock confirmation is missing.
- `bench_locked`: a bench output was requested without unlock.
- `invalid_bench_pin`: pin is outside Mega digital pin range.
- `invalid_bench_duration`: pulse duration is outside the allowed short test window.
- `ramps14_commissioning_disabled`: `jog_axis` was sent to non-commissioning firmware.
- `invalid_jog_steps`: jog step count is outside the allowed 1..25 range.
- `invalid_jog_timing`: jog pulse timing is outside the allowed range.
- `invalid_move_steps`: `move_axis` step count is outside the allowed range.
- `invalid_move_timing`: `move_axis` timing parameters are outside the allowed range.
- `invalid_seek_steps`: `seek_limit` max step count is outside the allowed range.
- `invalid_seek_timing`: `seek_limit` timing parameters are outside the allowed range.
- `invalid_output_pwm`: `set_output` PWM is outside `0..255`.
- `invalid_output_duration`: `set_output` duration is outside the allowed range.
- `invalid_axis_enabled`: `set_axis_enabled` value is not `0` or `1`.
- `invalid_hold`: `move_axis` hold value is not `0` or `1`.
- `unknown_limit`: limit ID is not one of the RAMPS commissioning limit IDs.
- `unknown_axis`: jog axis is not one of the commissioning axis IDs.
- `unknown_output`: RAMPS output is not one of `D8`, `D9`, or `D10`.
- `estop_active`: ESTOP blocks the requested command.
- `active_fault`: simulated or firmware fault blocks motion.

## Safety States

Default release firmware has:

- `COOKBOT_HARDWARE_CONFIGURED=0`
- `COOKBOT_BENCH_OUTPUTS_ENABLED=0`
- `motion_commands_enabled=false`
- `set_joint` and `set_gripper` rejected on real Mega firmware

Only a separate hardware-enabling change may replace placeholders with verified pins, limits, driver types, and ESTOP wiring.
