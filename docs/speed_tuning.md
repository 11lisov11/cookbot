# Speed Tuning for the Installed RAMPS/A4988 Controller

This document maps generic vendor advice to the hardware actually observed on
CookBot. It does not authorize real motion or a supply-voltage change.

## What applies

| Generic recommendation | CookBot result |
| --- | --- |
| Increase a global host speed percentage | No global percentage control was recovered from AXIS4UI or RA Pendant. They send per-command `F` values in the range `5..150`, and the missing vendor controller performs the coordinate conversion. |
| Reduce `delayMicroseconds()` | Applicable to raw commissioning motion, but only up to the first repeatable no-skip threshold under load. |
| Increase maximum speed and acceleration | Applicable after microsteps, current limit, limits, and position repeatability are measured. |
| Add S-curve acceleration | Implemented as the explicit `s_curve` commissioning profile. The verified legacy default remains `trapezoid`. |
| Set speed per MOV/JOG command | Applicable. `move_axis` and `seek_limit` accept bounded timing and ramp fields. |
| Change TB6600/DM542 DIP switches | Not applicable. The observed controller is RAMPS with red A4988 stepstick modules, not external black DIP-switch drivers. |
| Reduce microstep subdivision | Potentially applicable, but RAMPS uses physical MS1/MS2/MS3 jumpers under each A4988. Power must be removed and all steps-per-unit calibration repeated afterward. |
| Increase driver current | Only by measuring Rsense and Vref for the exact A4988 module and staying within motor/driver thermal limits. The bench-supply current setting is not phase current; see the manufacturer references in `docs/reference_links.md`. |
| Replace 12 V with 24/36 V | Not approved from the available evidence. Every RAMPS component, A4988 clone, capacitor, fan, vacuum output, and shared load must be rated and rewired appropriately first. |
| Fit closed-loop motors | A possible hardware redesign, not a guaranteed percentage speed increase and not a software-only fix. |

## Motion profiles

`trapezoid` preserves the commissioned linear period interpolation. `s_curve`
uses cubic smoothstep interpolation in fixed-point arithmetic, giving zero
slope at the start and end of each ramp. It smooths the raw STEP period; it is
not yet a calibrated Cartesian jerk planner or synchronized multi-axis inverse
kinematics implementation.

Preview a profile without opening a serial port:

```powershell
python scripts/hardware_tooling.py mega-ramp-preview --steps 1200 --pulse-us 3 --start-delay-us 5000 --min-delay-us 3500 --accel-steps 300 --decel-steps 300 --motion-profile s_curve --json
```

Generate, but do not transmit, an explicit commissioning command:

```powershell
python scripts/hardware_tooling.py mega-ramps14-move --port DRY_RUN_PORT --axis A --direction 1 --steps 1200 --start-delay-us 5000 --min-delay-us 3500 --accel-steps 300 --decel-steps 300 --motion-profile s_curve --dry-run
```

The default is intentionally still `trapezoid`. Selecting `s_curve` does not
raise the maximum STEP frequency by itself; it only changes how the requested
rate is approached and left.

## Safe tuning order

1. Record the motor model, winding pairs, A4988 Rsense, Vref, and RAMPS
   microstep jumpers for the selected axis.
2. Support or remove the load and verify ESTOP plus the relevant limit switch.
3. Preview a bounded profile offline.
4. Start from a previously repeatable delay and increase rate in small steps.
5. Repeat both directions at least three times and compare measured position.
6. Stop at the first click, stall, lost position, voltage sag, or thermal fault.
7. Set the operational limit below that threshold and repeat with the real
   load.

Do not find an edge by driving until the motor stalls. Without an encoder,
current sensor, or a second limit input, firmware cannot distinguish a hard
stop from missed steps.
