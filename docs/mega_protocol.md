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
- `estop_active`: ESTOP blocks the requested command.
- `active_fault`: simulated or firmware fault blocks motion.

## Safety States

Default release firmware has:

- `COOKBOT_HARDWARE_CONFIGURED=0`
- `COOKBOT_BENCH_OUTPUTS_ENABLED=0`
- `motion_commands_enabled=false`
- `set_joint` and `set_gripper` rejected on real Mega firmware

Only a separate hardware-enabling change may replace placeholders with verified pins, limits, driver types, and ESTOP wiring.
