# CookBot Safety

CookBot safety rules for the MVP:

- Real motion is blocked by default.
- Mega must not move until `enable_motion` and `home_all`.
- ESTOP clears the command queue and disables motion.
- Clearing ESTOP requires re-home.
- AI cannot call raw Mega commands.
- Heating, knives, relays, and arbitrary code execution are forbidden.
- Limit checks run in the UNO Q safety layer and must also run on Mega firmware before real motion is enabled.

The no-hardware simulator enforces the same high-level state transitions so tests can catch unsafe paths early.

Fault injection is available only for simulator/fake Mega testing:

- `POST /simulator/faults`
- `DELETE /simulator/faults`

Injected faults disable motion, clear queue depth, set `last_error`, and require re-home after clearing.

Real-motion readiness is exposed by:

- `GET /hardware/readiness`
- `GET /hardware/gate/report`
- `config/hardware_readiness.yaml`

`/hardware/gate/report` is stricter than the readiness file alone. It keeps real motion blocked unless the backend is in hardware mode, the Mega transport is serial, `COOKBOT_HARDWARE_CONFIGURED=true`, every readiness item is verified, and every verified item has evidence.

The default is `ready_for_real_motion=false`. Do not change this until pin map, drivers, switch polarity, power, ESTOP, limits, homing direction, and low-power motion tests are verified.
