#ifndef COOKBOT_HARDWARE_CONFIG_H
#define COOKBOT_HARDWARE_CONFIG_H

// Keep this disabled until the real CookBot arm has been inspected and
// documented in docs/vendor_robot_notes.md and config/hardware_readiness.yaml.
#ifndef COOKBOT_HARDWARE_CONFIGURED
#define COOKBOT_HARDWARE_CONFIGURED 0
#endif

// Bench output tests are compile-time locked and off by default. They are for
// short diagnostic pin pulses only, not motor motion.
#ifndef COOKBOT_BENCH_OUTPUTS_ENABLED
#define COOKBOT_BENCH_OUTPUTS_ENABLED 0
#endif

// Temporary commissioning mode for RAMPS 1.4-style Mega shields. It is not a
// production motion controller: it only permits tiny manual jog pulses and must
// stay off in normal builds.
#ifndef COOKBOT_RAMPS14_COMMISSIONING
#define COOKBOT_RAMPS14_COMMISSIONING 0
#endif

// In RAMPS 1.4 commissioning mode the D9 cooling fan is turned on before any
// supervised motor movement and remains on after the last step for this long.
#ifndef COOKBOT_RAMPS14_MOTION_FAN_COOLDOWN_MS
#define COOKBOT_RAMPS14_MOTION_FAN_COOLDOWN_MS 120000UL
#endif

// Placeholder only. Do not use these as real pins.
#ifndef COOKBOT_AXIS_COUNT
#if COOKBOT_RAMPS14_COMMISSIONING
#define COOKBOT_AXIS_COUNT 4
#else
#define COOKBOT_AXIS_COUNT 0
#endif
#endif

#ifndef COOKBOT_LIMIT_SWITCH_COUNT
#if COOKBOT_RAMPS14_COMMISSIONING
#define COOKBOT_LIMIT_SWITCH_COUNT 3
#else
#define COOKBOT_LIMIT_SWITCH_COUNT 0
#endif
#endif

// Hardware placeholders. Replace only after physical inspection, continuity
// checks, limit switch verification, driver current checks, and documented
// evidence in config/hardware_readiness.yaml.
#ifndef COOKBOT_ESTOP_PIN
#define COOKBOT_ESTOP_PIN -1
#endif

#ifndef COOKBOT_GRIPPER_PIN
#define COOKBOT_GRIPPER_PIN -1
#endif

// Axis pin placeholders. Real projects should define one verified entry per
// axis with step, direction, enable, min limit, max limit, and travel bounds.
// This skeleton deliberately keeps the list empty.
#ifndef COOKBOT_AXIS_PIN_CONFIGURED
#define COOKBOT_AXIS_PIN_CONFIGURED 0
#endif

#ifndef COOKBOT_BENCH_MAX_PULSE_MS
#define COOKBOT_BENCH_MAX_PULSE_MS 250
#endif

#endif
