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

// Placeholder only. Do not use these as real pins.
#ifndef COOKBOT_AXIS_COUNT
#define COOKBOT_AXIS_COUNT 0
#endif

#ifndef COOKBOT_LIMIT_SWITCH_COUNT
#define COOKBOT_LIMIT_SWITCH_COUNT 0
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
