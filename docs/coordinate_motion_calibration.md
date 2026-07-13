# Coordinate Motion Calibration

This procedure produces the parameters that the vendor called "coordinate
settings". It does not unlock real motion automatically.

## Required source data

Record one row per installed motor/driver in
`config/motion_calibration.yaml`:

1. Exact motor model, step angle, rated phase current, and winding pairs.
2. A4988 module Rsense marking and measured Vref.
3. RAMPS MS1/MS2/MS3 jumper state: full, 1/2, 1/4, 1/8, or 1/16 step.
4. Gearbox ratio. `FLE 42-010` is currently treated as likely `10:1`, not as a
   final manufacturer-verified value.
5. Slider screw lead or belt travel in millimeters per output revolution.
6. Arm link center-to-center dimensions, joint zero references, and safe
   angular limits.

Do not measure resistance or move jumpers with motor power energized. Do not
turn an A4988 potentiometer without identifying Rsense and the motor's rated
phase current. The bench supply's total current setting is not the driver's
per-coil current limit.

## Where each value comes from

| Parameter | Source |
| --- | --- |
| Motor full steps/revolution and rated phase current | Exact motor datasheet or label; a `1.8 degree` motor normally has 200 full steps/revolution |
| A4988 microstep value | Physical MS1/MS2/MS3 jumpers under that driver; software cannot detect passive RAMPS jumpers |
| A4988 current limit | Rsense marking plus measured Vref and the formula for that exact A4988 module |
| Gearbox ratio | Manufacturer datasheet or confirmed input/output turn count; `FLE 42-010` is only a likely 10:1 interpretation until verified |
| Slider travel/revolution | Screw lead from its datasheet or measured carriage travel for one manually rotated screw revolution |
| Steps/mm or steps/degree | A bounded commanded step count divided by independently measured travel |
| Joint zero and limits | Repeatable switch/reference location plus measured safe mechanical travel |
| Link lengths | Center-to-center physical measurement of each arm link |
| Maximum rate and acceleration | Loaded repeatability tests below the first missed-step/stall threshold |

The original factory values, if they still exist, can only come from the
vendor controller's firmware/EEPROM, a service parameter export, or a vendor
calibration document. Ask the supplier specifically for the controller
firmware, EEPROM/parameter backup, steps-per-unit table, arm geometry, and the
documented meaning of `G2696`. The supplied EXE/APK contains none of them.

## Calculations

```text
steps_per_motor_rev  = full_steps_per_rev * microsteps
steps_per_output_rev = steps_per_motor_rev * gearbox_ratio
output_rpm           = step_frequency_hz * 60 / steps_per_output_rev
slider_steps_per_mm  = steps_per_output_rev / travel_per_output_rev_mm
joint_steps_per_deg  = steps_per_output_rev / 360
```

The API calculator is available at `POST /motion/estimate`. Example for the
current A timing under an unverified `1/16` assumption:

```json
{
  "motor_full_steps_per_revolution": 200,
  "microsteps": 16,
  "gearbox_ratio": 10,
  "step_delay_us": 3500,
  "pulse_us": 3
}
```

It yields approximately `285.47 STEP/s`, `5.35 motor RPM`, and `0.535 output
RPM`. Full-step mode at the same pulse rate would be 16 times faster in shaft
revolutions, but it changes smoothness, resonance, torque behavior, and
calibration. It must be selected physically on RAMPS and then recalibrated.

## Measurement sequence

1. Remove or support the load so a failed step cannot drop the arm.
2. Verify ESTOP and one known home switch before travel tests.
3. Mark the motor and output shafts. Confirm that one commanded direction is
   repeatable and that the coupler/gearbox does not slip.
4. Use a finite, slow, bounded move. Measure actual joint angle or slider
   distance with an independent tool.
5. Submit commanded steps and measured travel to `POST /motion/calibrate`.
6. Repeat at least three times in both directions. Record backlash separately;
   do not average lost steps into the conversion constant.
7. Increase STEP rate using an acceleration ramp. Stop at the first skipped
   step, click, stall, driver overtemperature, or inconsistent return count.
8. Set the operational maximum below the repeatable threshold and repeat with
   the real load.
9. Measure link geometry and implement inverse kinematics only after every
   joint has stable steps-per-degree and both travel limits are known.

`POST /motion/calibrate` returns arithmetic only and always reports
`verified_for_real_motion=false`. Evidence and hardware-gate records must be
updated separately after supervised measurements.

## Data still needed now

- Photograph of the three RAMPS microstep jumpers below each A4988.
- Close photograph of each A4988 Rsense resistor marking.
- Vref measurement for A, B, C, and E with the exact installed motor noted.
- Exact placement of `17HS3401S` and `42INPR40-A-24DN` after the motor swap.
- Slider screw lead or pulley/belt pitch.
- A/B/C joint output angle for a known finite number of successful steps.
- Center-to-center arm link dimensions.

Without these measurements, neither `F100` nor a faster Arduino pulse loop can
produce a trustworthy Cartesian speed.
