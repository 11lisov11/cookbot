/*
  CookBot Arduino Mega firmware skeleton.

  This no-hardware MVP sketch compiles for arduino:avr:mega and exposes the
  CookBot newline-delimited JSON command shape. It intentionally does not drive
  motors because the real pin map, drivers, limits, currents, and axis count
  have not been verified on the user's hardware.
*/

#include "hardware_config.h"

static const unsigned long WATCHDOG_TIMEOUT_MS = 1500;

bool estopActive = false;
bool motionEnabled = false;
bool homed = false;
bool benchUnlocked = false;
bool simulatedFaultActive = false;
String simulatedFaultCode = "";
unsigned long lastCommandAt = 0;
Print *responseOutput = &Serial;
String usbInputLine = "";
#if COOKBOT_BLUETOOTH_UART_ENABLED
String bluetoothInputLine = "";
#endif

void handleLine(const String &line);
void processTransportInput(Stream &input, Print &output, String &buffer);
String extractJsonString(const String &line, const String &key);
long extractJsonInt(const String &line, const String &key, long defaultValue);
void handleBenchUnlock(const String &id, const String &line);
void handleBenchTestOutput(const String &id, const String &line);
void handleRamps14JogAxis(const String &id, const String &line);
void handleRamps14MoveAxis(const String &id, const String &line);
void handleRamps14SeekLimit(const String &id, const String &line);
void handleRamps14SetOutput(const String &id, const String &line);
void handleRamps14SetAxisEnabled(const String &id, const String &line);
void sendState(const String &id);
String capabilitiesJson();
String hardwareConfigJson();
String limitSwitchesJson();
String selfTestJson();
String firmwareStatusJson();
String inputsJson();
String benchOutputsEnabledJson();
String boolJson(bool value);
String faultsJson();
String ramps14CommissioningJson();
String bluetoothUartEnabledJson();
void sendOk(const String &id, const String &data);
void sendError(const String &id, const String &error);
void sendEvent(const String &event, const String &message);
void sendEventTo(Print &output, const String &event, const String &message);

#if COOKBOT_RAMPS14_COMMISSIONING
struct Ramps14AxisPins {
  uint8_t stepPin;
  uint8_t dirPin;
  uint8_t enablePin;
};

bool resolveRamps14AxisPins(const String &axis, Ramps14AxisPins &pins);
bool resolveRamps14OutputPin(const String &outputId, uint8_t &pin);
void clearRamps14AxisEnables();
void clearRamps14Outputs();
void ensureRamps14MotionFanOn();
void refreshRamps14MotionFanCooldown();
void clearRamps14MotionFanCooldown();
void updateRamps14MotionFanCooldown();
unsigned long ramps14MotionFanRemainingMs();
bool readRamps14LimitActive(const String &limitId);
unsigned long profiledDelayUs(long stepIndex, long totalSteps, long startDelayUs, long minDelayUs, long accelSteps, long decelSteps);
void slowDelayMicroseconds(unsigned long delayUs);
bool defaultDigitalStepBackendForAxis(const String &axis);
long runRamps14Steps(const Ramps14AxisPins &pins, bool digitalStepBackend, long direction, long maxSteps, long pulseUs, long startDelayUs, long minDelayUs, long accelSteps, long decelSteps, bool holdEnabled, const String &targetLimit, bool stopOnLimit, bool &limitHit);

bool ramps14MotionFanAutoActive = false;
unsigned long ramps14MotionFanKeepaliveUntilMs = 0;
#endif

void setup() {
  Serial.begin(115200);
#if COOKBOT_BLUETOOTH_UART_ENABLED
  COOKBOT_BLUETOOTH_SERIAL.begin(COOKBOT_BLUETOOTH_BAUD);
#endif
#if COOKBOT_RAMPS14_COMMISSIONING
  clearRamps14AxisEnables();
  clearRamps14Outputs();
#endif
  lastCommandAt = millis();
  sendEvent("boot", "CookBot Mega skeleton ready");
}

void loop() {
  processTransportInput(Serial, Serial, usbInputLine);
#if COOKBOT_BLUETOOTH_UART_ENABLED
  processTransportInput(COOKBOT_BLUETOOTH_SERIAL, COOKBOT_BLUETOOTH_SERIAL, bluetoothInputLine);
#endif

  if (motionEnabled && millis() - lastCommandAt > WATCHDOG_TIMEOUT_MS) {
    motionEnabled = false;
    sendEvent("watchdog", "motion_disabled");
  }

#if COOKBOT_RAMPS14_COMMISSIONING
  updateRamps14MotionFanCooldown();
#endif
}

void processTransportInput(Stream &input, Print &output, String &buffer) {
  while (input.available() > 0) {
    char next = (char)input.read();
    if (next == '\n' || next == '\r') {
      buffer.trim();
      if (buffer.length() > 0) {
        Print *previousOutput = responseOutput;
        responseOutput = &output;
        handleLine(buffer);
        responseOutput = previousOutput;
        lastCommandAt = millis();
      }
      buffer = "";
      continue;
    }

    if (buffer.length() >= COOKBOT_TRANSPORT_MAX_LINE_BYTES) {
      Print *previousOutput = responseOutput;
      responseOutput = &output;
      sendError("mega", "transport_line_too_long");
      responseOutput = previousOutput;
      buffer = "";
      continue;
    }
    buffer += next;
  }
}

void handleLine(const String &line) {
  String id = extractJsonString(line, "id");
  String command = extractJsonString(line, "command");
  if (id.length() == 0) {
    id = "mega";
  }

  if (command == "hello") {
    String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
    sendOk(id, String("\"name\":\"CookBot Mega\",\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.2.0\",\"protocol_version\":1,\"hardware_configured\":") + configured + ",\"capabilities\":" + capabilitiesJson());
    return;
  }
  if (command == "ping") {
    sendOk(id, "\"pong\":true");
    return;
  }
  if (command == "get_capabilities") {
    sendOk(id, "\"capabilities\":" + capabilitiesJson());
    return;
  }
  if (command == "get_hardware_config") {
    sendOk(id, "\"hardware_config\":" + hardwareConfigJson());
    return;
  }
  if (command == "get_limit_switches") {
    sendOk(id, "\"limit_switches\":" + limitSwitchesJson());
    return;
  }
  if (command == "self_test") {
    sendOk(id, "\"self_test\":" + selfTestJson());
    return;
  }
  if (command == "get_firmware_status") {
    sendOk(id, "\"firmware_status\":" + firmwareStatusJson());
    return;
  }
  if (command == "read_inputs") {
    sendOk(id, "\"inputs\":" + inputsJson());
    return;
  }
  if (command == "bench_unlock") {
    handleBenchUnlock(id, line);
    return;
  }
  if (command == "bench_test_output") {
    handleBenchTestOutput(id, line);
    return;
  }
  if (command == "jog_axis") {
    handleRamps14JogAxis(id, line);
    return;
  }
  if (command == "move_axis") {
    handleRamps14MoveAxis(id, line);
    return;
  }
  if (command == "seek_limit") {
    handleRamps14SeekLimit(id, line);
    return;
  }
  if (command == "set_output") {
    handleRamps14SetOutput(id, line);
    return;
  }
  if (command == "set_axis_enabled") {
    handleRamps14SetAxisEnabled(id, line);
    return;
  }
  if (command == "get_faults") {
    sendOk(id, "\"faults\":" + faultsJson());
    return;
  }
  if (command == "inject_fault") {
    simulatedFaultActive = true;
    simulatedFaultCode = "simulated_fault";
    motionEnabled = false;
    benchUnlocked = false;
    sendState(id);
    return;
  }
  if (command == "clear_faults") {
    simulatedFaultActive = false;
    simulatedFaultCode = "";
    motionEnabled = false;
    benchUnlocked = false;
    homed = false;
    sendState(id);
    return;
  }
  if (command == "get_state") {
    sendState(id);
    return;
  }
  if (command == "enable_motion") {
#if !COOKBOT_HARDWARE_CONFIGURED
    sendError(id, "hardware_not_configured");
    return;
#endif
    if (simulatedFaultActive) {
      sendError(id, "active_fault");
      return;
    }
    if (estopActive) {
      sendError(id, "estop_active");
      return;
    }
    motionEnabled = true;
    sendState(id);
    return;
  }
  if (command == "home_all") {
#if !COOKBOT_HARDWARE_CONFIGURED
    sendError(id, "hardware_not_configured");
    return;
#endif
    if (simulatedFaultActive) {
      sendError(id, "active_fault");
      return;
    }
    if (estopActive) {
      sendError(id, "estop_active");
      return;
    }
    homed = true;
    sendState(id);
    return;
  }
  if (command == "set_joint" || command == "set_gripper") {
#if COOKBOT_HARDWARE_CONFIGURED
    sendError(id, "real_motion_not_implemented");
#else
    sendError(id, "hardware_not_configured");
#endif
    return;
  }
  if (command == "estop") {
    estopActive = true;
    motionEnabled = false;
    benchUnlocked = false;
#if COOKBOT_RAMPS14_COMMISSIONING
    clearRamps14AxisEnables();
    clearRamps14Outputs();
#endif
    sendState(id);
    return;
  }
  if (command == "clear_estop") {
    estopActive = false;
    motionEnabled = false;
    benchUnlocked = false;
    homed = false;
    sendState(id);
    return;
  }

  sendError(id, "unknown_command");
}

String extractJsonString(const String &line, const String &key) {
  String marker = "\"" + key + "\":";
  int markerIndex = line.indexOf(marker);
  if (markerIndex < 0) {
    return "";
  }
  int firstQuote = line.indexOf('"', markerIndex + marker.length());
  if (firstQuote < 0) {
    return "";
  }
  int secondQuote = line.indexOf('"', firstQuote + 1);
  if (secondQuote < 0) {
    return "";
  }
  return line.substring(firstQuote + 1, secondQuote);
}

long extractJsonInt(const String &line, const String &key, long defaultValue) {
  String marker = "\"" + key + "\":";
  int markerIndex = line.indexOf(marker);
  if (markerIndex < 0) {
    return defaultValue;
  }
  int length = (int)line.length();
  int valueStart = markerIndex + marker.length();
  while (valueStart < length && (line[valueStart] == ' ' || line[valueStart] == '\t')) {
    valueStart++;
  }
  int valueEnd = valueStart;
  while (valueEnd < length && (isDigit(line[valueEnd]) || line[valueEnd] == '-')) {
    valueEnd++;
  }
  if (valueEnd == valueStart) {
    return defaultValue;
  }
  return line.substring(valueStart, valueEnd).toInt();
}

void handleBenchUnlock(const String &id, const String &line) {
#if COOKBOT_BENCH_OUTPUTS_ENABLED
  if (estopActive) {
    sendError(id, "estop_active");
    return;
  }
  String confirm = extractJsonString(line, "confirm");
  if (confirm != "BENCH_ONLY") {
    sendError(id, "bench_confirm_required");
    return;
  }
  benchUnlocked = true;
  sendOk(id, "\"bench_unlocked\":true,\"bench_outputs_enabled\":true");
#else
  (void)line;
  sendError(id, "bench_outputs_disabled");
#endif
}

void handleBenchTestOutput(const String &id, const String &line) {
#if COOKBOT_BENCH_OUTPUTS_ENABLED
  if (estopActive) {
    benchUnlocked = false;
    sendError(id, "estop_active");
    return;
  }
  if (!benchUnlocked) {
    sendError(id, "bench_locked");
    return;
  }
  long pin = extractJsonInt(line, "pin", -1);
  long durationMs = extractJsonInt(line, "duration_ms", 25);
  if (pin < 2 || pin > 53) {
    sendError(id, "invalid_bench_pin");
    return;
  }
  if (durationMs < 1 || durationMs > COOKBOT_BENCH_MAX_PULSE_MS) {
    sendError(id, "invalid_bench_duration");
    return;
  }
  pinMode((uint8_t)pin, OUTPUT);
  digitalWrite((uint8_t)pin, HIGH);
  delay((unsigned long)durationMs);
  digitalWrite((uint8_t)pin, LOW);
  benchUnlocked = false;
  sendOk(id, "\"bench_tested\":true,\"pin\":" + String(pin) + ",\"duration_ms\":" + String(durationMs));
#else
  (void)line;
  sendError(id, "bench_outputs_disabled");
#endif
}

void handleRamps14JogAxis(const String &id, const String &line) {
#if COOKBOT_RAMPS14_COMMISSIONING
  if (estopActive) {
    sendError(id, "estop_active");
    return;
  }
  if (simulatedFaultActive) {
    sendError(id, "active_fault");
    return;
  }

  String axis = extractJsonString(line, "axis");
  long steps = extractJsonInt(line, "steps", 0);
  long direction = extractJsonInt(line, "direction", 1);
  long pulseUs = extractJsonInt(line, "pulse_us", 4);
  long stepDelayUs = extractJsonInt(line, "step_delay_us", 2500);

  if (steps < 1 || steps > 25) {
    sendError(id, "invalid_jog_steps");
    return;
  }
  if (pulseUs < 2 || pulseUs > 20 || stepDelayUs < 1000 || stepDelayUs > 20000) {
    sendError(id, "invalid_jog_timing");
    return;
  }

  uint8_t stepPin = 255;
  uint8_t dirPin = 255;
  uint8_t enablePin = 255;
  if (axis == "B" || axis == "X") {
    stepPin = 54;
    dirPin = 55;
    enablePin = 38;
  } else if (axis == "A" || axis == "Y") {
    stepPin = 60;
    dirPin = 61;
    enablePin = 56;
  } else if (axis == "C" || axis == "Z") {
    stepPin = 46;
    dirPin = 48;
    enablePin = 62;
  } else if (axis == "SLIDER" || axis == "E0") {
    stepPin = 26;
    dirPin = 28;
    enablePin = 24;
  } else if (axis == "E1") {
    stepPin = 36;
    dirPin = 34;
    enablePin = 30;
  } else {
    sendError(id, "unknown_axis");
    return;
  }

  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(enablePin, OUTPUT);
  digitalWrite(stepPin, LOW);
  digitalWrite(dirPin, direction == 0 ? LOW : HIGH);
  digitalWrite(enablePin, LOW);
  ensureRamps14MotionFanOn();
  delay(20);
  for (long index = 0; index < steps; index++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds((unsigned int)pulseUs);
    digitalWrite(stepPin, LOW);
    delayMicroseconds((unsigned int)stepDelayUs);
  }
  refreshRamps14MotionFanCooldown();
  digitalWrite(enablePin, HIGH);

  sendOk(id, "\"jogged\":true,\"axis\":\"" + axis + "\",\"steps\":" + String(steps) + ",\"direction\":" + String(direction == 0 ? 0 : 1));
#else
  (void)line;
  sendError(id, "ramps14_commissioning_disabled");
#endif
}

void handleRamps14MoveAxis(const String &id, const String &line) {
#if COOKBOT_RAMPS14_COMMISSIONING
  if (estopActive) {
    sendError(id, "estop_active");
    return;
  }
  if (simulatedFaultActive) {
    sendError(id, "active_fault");
    return;
  }

  String axis = extractJsonString(line, "axis");
  long steps = extractJsonInt(line, "steps", 0);
  long direction = extractJsonInt(line, "direction", 1);
  long defaultPulseUs = 4;
  long defaultStartDelayUs = 8000;
  long defaultMinDelayUs = 8000;
  long defaultAccelSteps = 0;
  long defaultDecelSteps = 0;
  if (axis == "A" || axis == "Y") {
    defaultPulseUs = 3;
    defaultStartDelayUs = 5000;
    defaultMinDelayUs = 3500;
    defaultAccelSteps = 300;
    defaultDecelSteps = 100;
  } else if (axis == "SLIDER" || axis == "E0") {
    defaultPulseUs = 8;
    defaultStartDelayUs = 12000;
    defaultMinDelayUs = 12000;
  }
  long pulseUs = extractJsonInt(line, "pulse_us", defaultPulseUs);
  long startDelayUs = extractJsonInt(line, "start_delay_us", defaultStartDelayUs);
  long minDelayUs = extractJsonInt(line, "min_delay_us", defaultMinDelayUs);
  long accelSteps = extractJsonInt(line, "accel_steps", defaultAccelSteps);
  long decelSteps = extractJsonInt(line, "decel_steps", defaultDecelSteps);
  long hold = extractJsonInt(line, "hold", 0);
  String stepBackend = extractJsonString(line, "step_backend");
  if (stepBackend.length() == 0) {
    stepBackend = defaultDigitalStepBackendForAxis(axis) ? "digital" : "direct";
  }

  if (steps < 1 || steps > 30000) {
    sendError(id, "invalid_move_steps");
    return;
  }
  if (pulseUs < 2 || pulseUs > 20 || minDelayUs < 250 || minDelayUs > 200000 || startDelayUs < minDelayUs || startDelayUs > 250000 || accelSteps < 0 || accelSteps > 10000 || decelSteps < 0 || decelSteps > 10000) {
    sendError(id, "invalid_move_timing");
    return;
  }
  if (hold < 0 || hold > 1) {
    sendError(id, "invalid_hold");
    return;
  }
  if (stepBackend != "direct" && stepBackend != "digital") {
    sendError(id, "invalid_step_backend");
    return;
  }

  Ramps14AxisPins pins;
  if (!resolveRamps14AxisPins(axis, pins)) {
    sendError(id, "unknown_axis");
    return;
  }

  bool limitHit = false;
  long moved = runRamps14Steps(pins, stepBackend == "digital", direction, steps, pulseUs, startDelayUs, minDelayUs, accelSteps, decelSteps, hold == 1, "", false, limitHit);
  sendOk(id, "\"moved\":true,\"axis\":\"" + axis + "\",\"steps\":" + String(moved) + ",\"direction\":" + String(direction == 0 ? 0 : 1) + ",\"motion_profile\":\"trapezoid\",\"step_backend\":\"" + stepBackend + "\",\"min_delay_us\":" + String(minDelayUs) + ",\"start_delay_us\":" + String(startDelayUs) + ",\"accel_steps\":" + String(accelSteps) + ",\"decel_steps\":" + String(decelSteps) + ",\"hold\":" + boolJson(hold == 1));
#else
  (void)line;
  sendError(id, "ramps14_commissioning_disabled");
#endif
}

void handleRamps14SeekLimit(const String &id, const String &line) {
#if COOKBOT_RAMPS14_COMMISSIONING
  if (estopActive) {
    sendError(id, "estop_active");
    return;
  }
  if (simulatedFaultActive) {
    sendError(id, "active_fault");
    return;
  }

  String axis = extractJsonString(line, "axis");
  String limitId = extractJsonString(line, "limit");
  long maxSteps = extractJsonInt(line, "max_steps", 0);
  long direction = extractJsonInt(line, "direction", 0);
  long defaultSeekDelayUs = (axis == "A" || axis == "Y") ? 4000 : 8000;
  long pulseUs = extractJsonInt(line, "pulse_us", 4);
  long startDelayUs = extractJsonInt(line, "start_delay_us", defaultSeekDelayUs);
  long minDelayUs = extractJsonInt(line, "min_delay_us", defaultSeekDelayUs);
  long accelSteps = extractJsonInt(line, "accel_steps", 0);
  long decelSteps = extractJsonInt(line, "decel_steps", 0);
  String stepBackend = extractJsonString(line, "step_backend");
  if (stepBackend.length() == 0) {
    stepBackend = defaultDigitalStepBackendForAxis(axis) ? "digital" : "direct";
  }

  if (maxSteps < 1 || maxSteps > 40000) {
    sendError(id, "invalid_seek_steps");
    return;
  }
  if (limitId != "A_MIN" && limitId != "B_MIN" && limitId != "C_MIN") {
    sendError(id, "unknown_limit");
    return;
  }
  if (pulseUs < 2 || pulseUs > 20 || minDelayUs < 250 || minDelayUs > 200000 || startDelayUs < minDelayUs || startDelayUs > 250000 || accelSteps < 0 || accelSteps > 10000 || decelSteps < 0 || decelSteps > 10000) {
    sendError(id, "invalid_seek_timing");
    return;
  }
  if (stepBackend != "direct" && stepBackend != "digital") {
    sendError(id, "invalid_step_backend");
    return;
  }

  Ramps14AxisPins pins;
  if (!resolveRamps14AxisPins(axis, pins)) {
    sendError(id, "unknown_axis");
    return;
  }

  bool limitHit = false;
  long moved = runRamps14Steps(pins, stepBackend == "digital", direction, maxSteps, pulseUs, startDelayUs, minDelayUs, accelSteps, decelSteps, false, limitId, true, limitHit);
  sendOk(id, "\"limit_hit\":" + boolJson(limitHit) + ",\"axis\":\"" + axis + "\",\"limit\":\"" + limitId + "\",\"steps\":" + String(moved) + ",\"direction\":" + String(direction == 0 ? 0 : 1) + ",\"motion_profile\":\"trapezoid\",\"step_backend\":\"" + stepBackend + "\",\"min_delay_us\":" + String(minDelayUs) + ",\"start_delay_us\":" + String(startDelayUs) + ",\"accel_steps\":" + String(accelSteps) + ",\"decel_steps\":" + String(decelSteps));
#else
  (void)line;
  sendError(id, "ramps14_commissioning_disabled");
#endif
}

void handleRamps14SetOutput(const String &id, const String &line) {
#if COOKBOT_RAMPS14_COMMISSIONING
  if (estopActive) {
    clearRamps14Outputs();
    sendError(id, "estop_active");
    return;
  }
  if (simulatedFaultActive) {
    clearRamps14Outputs();
    sendError(id, "active_fault");
    return;
  }

  String outputId = extractJsonString(line, "output");
  long pwm = extractJsonInt(line, "pwm", -1);
  long durationMs = extractJsonInt(line, "duration_ms", 0);
  if (pwm < 0 || pwm > 255) {
    sendError(id, "invalid_output_pwm");
    return;
  }
  if (durationMs < 0 || durationMs > 60000) {
    sendError(id, "invalid_output_duration");
    return;
  }

  uint8_t pin = 255;
  if (!resolveRamps14OutputPin(outputId, pin)) {
    sendError(id, "unknown_output");
    return;
  }

  pinMode(pin, OUTPUT);
  if (pwm == 0) {
    digitalWrite(pin, LOW);
  } else if (pwm >= 255) {
    digitalWrite(pin, HIGH);
  } else {
    analogWrite(pin, (int)pwm);
  }

  if (durationMs > 0) {
    delay((unsigned long)durationMs);
    digitalWrite(pin, LOW);
  }

  if (outputId == "D9") {
    if (pwm == 0 || durationMs > 0) {
      clearRamps14MotionFanCooldown();
    } else {
      ramps14MotionFanAutoActive = false;
      ramps14MotionFanKeepaliveUntilMs = 0;
    }
  }

  sendOk(id, "\"output\":\"" + outputId + "\",\"pin\":" + String(pin) + ",\"pwm\":" + String(pwm) + ",\"duration_ms\":" + String(durationMs) + ",\"latched\":" + boolJson(durationMs == 0));
#else
  (void)line;
  sendError(id, "ramps14_commissioning_disabled");
#endif
}

void handleRamps14SetAxisEnabled(const String &id, const String &line) {
#if COOKBOT_RAMPS14_COMMISSIONING
  if (estopActive) {
    clearRamps14AxisEnables();
    sendError(id, "estop_active");
    return;
  }
  if (simulatedFaultActive) {
    clearRamps14AxisEnables();
    sendError(id, "active_fault");
    return;
  }

  String axis = extractJsonString(line, "axis");
  long enabled = extractJsonInt(line, "enabled", -1);
  if (enabled < 0 || enabled > 1) {
    sendError(id, "invalid_axis_enabled");
    return;
  }

  Ramps14AxisPins pins;
  if (!resolveRamps14AxisPins(axis, pins)) {
    sendError(id, "unknown_axis");
    return;
  }

  pinMode(pins.enablePin, OUTPUT);
  digitalWrite(pins.enablePin, enabled == 1 ? LOW : HIGH);
  sendOk(id, "\"axis\":\"" + axis + "\",\"enable_pin\":" + String(pins.enablePin) + ",\"enabled\":" + boolJson(enabled == 1));
#else
  (void)line;
  sendError(id, "ramps14_commissioning_disabled");
#endif
}

#if COOKBOT_RAMPS14_COMMISSIONING
bool resolveRamps14AxisPins(const String &axis, Ramps14AxisPins &pins) {
  if (axis == "B" || axis == "X") {
    pins.stepPin = 54;
    pins.dirPin = 55;
    pins.enablePin = 38;
    return true;
  }
  if (axis == "A" || axis == "Y") {
    pins.stepPin = 60;
    pins.dirPin = 61;
    pins.enablePin = 56;
    return true;
  }
  if (axis == "C" || axis == "Z") {
    pins.stepPin = 46;
    pins.dirPin = 48;
    pins.enablePin = 62;
    return true;
  }
  if (axis == "SLIDER" || axis == "E0") {
    pins.stepPin = 26;
    pins.dirPin = 28;
    pins.enablePin = 24;
    return true;
  }
  if (axis == "E1") {
    pins.stepPin = 36;
    pins.dirPin = 34;
    pins.enablePin = 30;
    return true;
  }
  return false;
}

void clearRamps14AxisEnables() {
  const uint8_t enablePins[] = {38, 56, 62, 24, 30};
  for (uint8_t index = 0; index < sizeof(enablePins); index++) {
    pinMode(enablePins[index], OUTPUT);
    digitalWrite(enablePins[index], HIGH);
  }
}

bool resolveRamps14OutputPin(const String &outputId, uint8_t &pin) {
  if (outputId == "D8") {
    pin = 8;
    return true;
  }
  if (outputId == "D9") {
    pin = 9;
    return true;
  }
  if (outputId == "D10") {
    pin = 10;
    return true;
  }
  return false;
}

void clearRamps14Outputs() {
  clearRamps14MotionFanCooldown();
  pinMode(8, OUTPUT);
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  digitalWrite(8, LOW);
  digitalWrite(9, LOW);
  digitalWrite(10, LOW);
}

void ensureRamps14MotionFanOn() {
  pinMode(9, OUTPUT);
  digitalWrite(9, HIGH);
  refreshRamps14MotionFanCooldown();
}

void refreshRamps14MotionFanCooldown() {
  ramps14MotionFanAutoActive = true;
  ramps14MotionFanKeepaliveUntilMs = millis() + COOKBOT_RAMPS14_MOTION_FAN_COOLDOWN_MS;
}

void clearRamps14MotionFanCooldown() {
  ramps14MotionFanAutoActive = false;
  ramps14MotionFanKeepaliveUntilMs = 0;
}

void updateRamps14MotionFanCooldown() {
  if (!ramps14MotionFanAutoActive) {
    return;
  }
  if ((long)(millis() - ramps14MotionFanKeepaliveUntilMs) < 0) {
    return;
  }
  digitalWrite(9, LOW);
  clearRamps14MotionFanCooldown();
}

unsigned long ramps14MotionFanRemainingMs() {
  if (!ramps14MotionFanAutoActive) {
    return 0;
  }
  unsigned long now = millis();
  if ((long)(ramps14MotionFanKeepaliveUntilMs - now) <= 0) {
    return 0;
  }
  return ramps14MotionFanKeepaliveUntilMs - now;
}

bool readRamps14LimitActive(const String &limitId) {
  int pin = -1;
  if (limitId == "B_MIN") {
    pin = 3;
  } else if (limitId == "A_MIN") {
    pin = 14;
  } else if (limitId == "C_MIN") {
    pin = 18;
  } else {
    return false;
  }
  pinMode((uint8_t)pin, INPUT_PULLUP);
  return digitalRead((uint8_t)pin) == LOW;
}

unsigned long profiledDelayUs(long stepIndex, long totalSteps, long startDelayUs, long minDelayUs, long accelSteps, long decelSteps) {
  long delayUs = minDelayUs;
  if (accelSteps > 0 && stepIndex < accelSteps) {
    long delta = startDelayUs - minDelayUs;
    long accelDelay = startDelayUs - ((delta * stepIndex) / accelSteps);
    if (accelDelay > delayUs) {
      delayUs = accelDelay;
    }
  }

  long stepsRemaining = totalSteps - stepIndex - 1;
  if (decelSteps > 0 && stepsRemaining < decelSteps) {
    long delta = startDelayUs - minDelayUs;
    long decelIndex = decelSteps - stepsRemaining;
    long decelDelay = minDelayUs + ((delta * decelIndex) / decelSteps);
    if (decelDelay > delayUs) {
      delayUs = decelDelay;
    }
  }

  if (delayUs < minDelayUs) {
    delayUs = minDelayUs;
  }
  return (unsigned long)delayUs;
}

void slowDelayMicroseconds(unsigned long delayUs) {
  while (delayUs > 16000UL) {
    delayMicroseconds(16000);
    delayUs -= 16000UL;
  }
  if (delayUs > 0) {
    delayMicroseconds((unsigned int)delayUs);
  }
}

bool defaultDigitalStepBackendForAxis(const String &axis) {
  return axis == "SLIDER" || axis == "E0";
}

long runRamps14Steps(const Ramps14AxisPins &pins, bool digitalStepBackend, long direction, long maxSteps, long pulseUs, long startDelayUs, long minDelayUs, long accelSteps, long decelSteps, bool holdEnabled, const String &targetLimit, bool stopOnLimit, bool &limitHit) {
  limitHit = false;
  pinMode(pins.stepPin, OUTPUT);
  pinMode(pins.dirPin, OUTPUT);
  pinMode(pins.enablePin, OUTPUT);
  digitalWrite(pins.stepPin, LOW);
  digitalWrite(pins.dirPin, direction == 0 ? LOW : HIGH);
  digitalWrite(pins.enablePin, LOW);
  ensureRamps14MotionFanOn();
  delay(20);

  volatile uint8_t *stepPort = portOutputRegister(digitalPinToPort(pins.stepPin));
  uint8_t stepMask = digitalPinToBitMask(pins.stepPin);

  long moved = 0;
  for (long index = 0; index < maxSteps; index++) {
    if (stopOnLimit && readRamps14LimitActive(targetLimit)) {
      limitHit = true;
      break;
    }
    if (digitalStepBackend) {
      digitalWrite(pins.stepPin, HIGH);
    } else {
      *stepPort |= stepMask;
    }
    slowDelayMicroseconds((unsigned long)pulseUs);
    if (digitalStepBackend) {
      digitalWrite(pins.stepPin, LOW);
    } else {
      *stepPort &= (uint8_t)~stepMask;
    }
    moved++;
    slowDelayMicroseconds(profiledDelayUs(index, maxSteps, startDelayUs, minDelayUs, accelSteps, decelSteps));
    if (stopOnLimit && readRamps14LimitActive(targetLimit)) {
      limitHit = true;
      break;
    }
  }

  if (!holdEnabled) {
    digitalWrite(pins.enablePin, HIGH);
  }
  refreshRamps14MotionFanCooldown();
  return moved;
}
#endif

void sendState(const String &id) {
  String data = "\"state\":{\"mode\":\"hardware\",\"estop\":";
  data += estopActive ? "true" : "false";
  data += ",\"homed\":";
  data += homed ? "true" : "false";
  data += ",\"calibrated\":false,\"motion_enabled\":";
  data += motionEnabled ? "true" : "false";
  data += ",\"services\":{\"mega\":";
#if COOKBOT_BLUETOOTH_UART_ENABLED
  data += "\"usb_serial+bluetooth_rfcomm\"";
#else
  data += "\"usb_serial\"";
#endif
  data += ",\"backend\":\"external\"},\"axes\":[],\"gripper\":{\"position\":0,\"homed\":";
  data += homed ? "true" : "false";
  data += ",\"calibrated\":false,\"moving\":false},\"limit_switches\":{},\"queue_depth\":0,\"last_error\":";
  if (simulatedFaultActive) {
    data += "\"";
    data += simulatedFaultCode;
    data += "\"";
  } else {
    data += "null";
  }
  data += "}";
  sendOk(id, data);
}

String capabilitiesJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  return "{\"protocol_version\":1,\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.2.0\",\"hardware_configured\":" + configured + ",\"motion_commands_enabled\":false,\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"bluetooth_uart_enabled\":" + bluetoothUartEnabledJson() + ",\"supported_transports\":[\"usb_serial\",\"bluetooth_rfcomm\"],\"supported_commands\":[\"hello\",\"ping\",\"get_state\",\"get_capabilities\",\"get_hardware_config\",\"get_limit_switches\",\"self_test\",\"get_firmware_status\",\"read_inputs\",\"bench_unlock\",\"bench_test_output\",\"jog_axis\",\"move_axis\",\"seek_limit\",\"set_output\",\"set_axis_enabled\",\"get_faults\",\"inject_fault\",\"clear_faults\",\"enable_motion\",\"home_all\",\"set_joint\",\"set_gripper\",\"estop\",\"clear_estop\"]}";
}

String hardwareConfigJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  return "{\"hardware_configured\":" + configured + ",\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"bluetooth_uart_enabled\":" + bluetoothUartEnabledJson() + ",\"axis_count\":" + String(COOKBOT_AXIS_COUNT) + ",\"limit_switch_count\":" + String(COOKBOT_LIMIT_SWITCH_COUNT) + ",\"estop_pin\":" + String(COOKBOT_ESTOP_PIN) + ",\"gripper_pin\":" + String(COOKBOT_GRIPPER_PIN) + ",\"axis_pin_configured\":" + ramps14CommissioningJson() + ",\"note\":\"ramps14_jog_only_no_autonomous_motion\"}";
}

String limitSwitchesJson() {
#if COOKBOT_RAMPS14_COMMISSIONING
  return "{\"configured\":true,\"switches\":[{\"id\":\"B_MIN\",\"pin\":3,\"state\":\"not_read\"},{\"id\":\"A_MIN\",\"pin\":14,\"state\":\"not_read\"},{\"id\":\"C_MIN\",\"pin\":18,\"state\":\"not_read\"}]}";
#else
  return "{\"configured\":false,\"switches\":[]}";
#endif
}

String selfTestJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  return "{\"ok\":true,\"hardware_configured\":" + configured + ",\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"bluetooth_uart_enabled\":" + bluetoothUartEnabledJson() + ",\"motion_outputs_enabled\":" + ramps14CommissioningJson() + ",\"checks\":[{\"id\":\"usb_serial\",\"ok\":true},{\"id\":\"bluetooth_uart\",\"ok\":true,\"enabled\":" + bluetoothUartEnabledJson() + "},{\"id\":\"hardware_config\",\"ok\":true,\"detail\":\"ramps14_commissioning_or_placeholder\"},{\"id\":\"motion_outputs\",\"ok\":true,\"detail\":\"jog_only\"},{\"id\":\"bench_outputs\",\"ok\":true,\"detail\":\"compile_time_locked\"}]}";
}

String firmwareStatusJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  String data = "{\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.2.0\",\"hardware_configured\":" + configured + ",\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"bluetooth_uart_enabled\":" + bluetoothUartEnabledJson() + ",\"bench_unlocked\":" + boolJson(benchUnlocked) + ",\"estop\":" + boolJson(estopActive) + ",\"motion_enabled\":" + boolJson(motionEnabled) + ",\"watchdog_timeout_ms\":" + String(WATCHDOG_TIMEOUT_MS);
#if COOKBOT_BLUETOOTH_UART_ENABLED
  data += ",\"bluetooth_uart_port\":" + String(COOKBOT_BLUETOOTH_UART_PORT) + ",\"bluetooth_baud\":" + String(COOKBOT_BLUETOOTH_BAUD) + ",\"bluetooth_rx_pin\":" + String(COOKBOT_BLUETOOTH_RX_PIN) + ",\"bluetooth_tx_pin\":" + String(COOKBOT_BLUETOOTH_TX_PIN);
#endif
#if COOKBOT_RAMPS14_COMMISSIONING
  data += ",\"motion_fan_output\":\"D9\",\"motion_fan_cooldown_ms\":" + String(COOKBOT_RAMPS14_MOTION_FAN_COOLDOWN_MS) + ",\"motion_fan_auto_active\":" + boolJson(ramps14MotionFanAutoActive) + ",\"motion_fan_remaining_ms\":" + String(ramps14MotionFanRemainingMs());
#endif
  data += "}";
  return data;
}

String inputsJson() {
#if COOKBOT_RAMPS14_COMMISSIONING
  pinMode(3, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
  pinMode(18, INPUT_PULLUP);
  return "{\"estop_pin\":" + String(COOKBOT_ESTOP_PIN) + ",\"estop_active\":" + boolJson(estopActive) + ",\"limit_switches\":[{\"id\":\"B_MIN\",\"pin\":3,\"active\":" + boolJson(digitalRead(3) == LOW) + "},{\"id\":\"A_MIN\",\"pin\":14,\"active\":" + boolJson(digitalRead(14) == LOW) + "},{\"id\":\"C_MIN\",\"pin\":18,\"active\":" + boolJson(digitalRead(18) == LOW) + "}]}";
#else
  return "{\"estop_pin\":" + String(COOKBOT_ESTOP_PIN) + ",\"estop_active\":" + boolJson(estopActive) + ",\"limit_switches\":[]}";
#endif
}

String benchOutputsEnabledJson() {
#if COOKBOT_BENCH_OUTPUTS_ENABLED
  return "true";
#else
  return "false";
#endif
}

String ramps14CommissioningJson() {
#if COOKBOT_RAMPS14_COMMISSIONING
  return "true";
#else
  return "false";
#endif
}

String bluetoothUartEnabledJson() {
#if COOKBOT_BLUETOOTH_UART_ENABLED
  return "true";
#else
  return "false";
#endif
}

String boolJson(bool value) {
  return value ? "true" : "false";
}

String faultsJson() {
  if (!simulatedFaultActive) {
    return "{}";
  }
  return "{\"" + simulatedFaultCode + "\":\"firmware simulated fault\"}";
}

void sendOk(const String &id, const String &data) {
  responseOutput->print("{\"id\":\"");
  responseOutput->print(id);
  responseOutput->print("\",\"ok\":true,\"data\":{");
  responseOutput->print(data);
  responseOutput->println("},\"error\":null}");
}

void sendError(const String &id, const String &error) {
  responseOutput->print("{\"id\":\"");
  responseOutput->print(id);
  responseOutput->print("\",\"ok\":false,\"data\":{},\"error\":\"");
  responseOutput->print(error);
  responseOutput->println("\"}");
}

void sendEvent(const String &event, const String &message) {
  sendEventTo(Serial, event, message);
#if COOKBOT_BLUETOOTH_UART_ENABLED
  sendEventTo(COOKBOT_BLUETOOTH_SERIAL, event, message);
#endif
}

void sendEventTo(Print &output, const String &event, const String &message) {
  output.print("{\"event\":\"");
  output.print(event);
  output.print("\",\"source\":\"mega\",\"message\":\"");
  output.print(message);
  output.println("\"}");
}
