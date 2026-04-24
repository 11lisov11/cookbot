#ifndef COOKBOT_HARDWARE_CONFIG_H
#define COOKBOT_HARDWARE_CONFIG_H

// Keep this disabled until the real CookBot arm has been inspected and
// documented in docs/vendor_robot_notes.md and config/hardware_readiness.yaml.
#define COOKBOT_HARDWARE_CONFIGURED 0

// Placeholder only. Do not use these as real pins.
#define COOKBOT_AXIS_COUNT 0
#define COOKBOT_LIMIT_SWITCH_COUNT 0

// Hardware placeholders. Replace only after physical inspection, continuity
// checks, limit switch verification, driver current checks, and documented
// evidence in config/hardware_readiness.yaml.
#define COOKBOT_ESTOP_PIN -1
#define COOKBOT_GRIPPER_PIN -1

// Axis pin placeholders. Real projects should define one verified entry per
// axis with step, direction, enable, min limit, max limit, and travel bounds.
// This skeleton deliberately keeps the list empty.
#define COOKBOT_AXIS_PIN_CONFIGURED 0

#endif
