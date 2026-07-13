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

// Optional Bluetooth Classic SPP module connected to a dedicated Mega hardware
// UART. Keep this off in normal builds. The RAMPS commissioning profile uses
// Serial2 because Serial1 TX (18) conflicts with C_MIN and Serial3 TX (14)
// conflicts with A_MIN.
#ifndef COOKBOT_BLUETOOTH_UART_ENABLED
#define COOKBOT_BLUETOOTH_UART_ENABLED 0
#endif

#ifndef COOKBOT_BLUETOOTH_UART_PORT
#define COOKBOT_BLUETOOTH_UART_PORT 2
#endif

#ifndef COOKBOT_BLUETOOTH_BAUD
#define COOKBOT_BLUETOOTH_BAUD 9600UL
#endif

#ifndef COOKBOT_TRANSPORT_MAX_LINE_BYTES
#define COOKBOT_TRANSPORT_MAX_LINE_BYTES 384
#endif

#if COOKBOT_BLUETOOTH_UART_ENABLED
#if COOKBOT_BLUETOOTH_UART_PORT == 1
#define COOKBOT_BLUETOOTH_SERIAL Serial1
#define COOKBOT_BLUETOOTH_RX_PIN 19
#define COOKBOT_BLUETOOTH_TX_PIN 18
#elif COOKBOT_BLUETOOTH_UART_PORT == 2
#define COOKBOT_BLUETOOTH_SERIAL Serial2
#define COOKBOT_BLUETOOTH_RX_PIN 17
#define COOKBOT_BLUETOOTH_TX_PIN 16
#elif COOKBOT_BLUETOOTH_UART_PORT == 3
#define COOKBOT_BLUETOOTH_SERIAL Serial3
#define COOKBOT_BLUETOOTH_RX_PIN 15
#define COOKBOT_BLUETOOTH_TX_PIN 14
#else
#error "COOKBOT_BLUETOOTH_UART_PORT must be 1, 2, or 3"
#endif

#if COOKBOT_RAMPS14_COMMISSIONING && COOKBOT_BLUETOOTH_UART_PORT != 2
#error "RAMPS commissioning Bluetooth must use Serial2; Serial1/3 conflict with verified limit pins"
#endif
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

// Coordinate motion remains locked until these are measured for every axis.
#ifndef COOKBOT_MICROSTEP_CONFIG_VERIFIED
#define COOKBOT_MICROSTEP_CONFIG_VERIFIED 0
#endif

#ifndef COOKBOT_COORDINATE_CALIBRATION_VERIFIED
#define COOKBOT_COORDINATE_CALIBRATION_VERIFIED 0
#endif

#ifndef COOKBOT_BENCH_MAX_PULSE_MS
#define COOKBOT_BENCH_MAX_PULSE_MS 250
#endif

#endif
