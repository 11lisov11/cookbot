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

void handleLine(const String &line);
String extractJsonString(const String &line, const String &key);
long extractJsonInt(const String &line, const String &key, long defaultValue);
void handleBenchUnlock(const String &id, const String &line);
void handleBenchTestOutput(const String &id, const String &line);
void handleRamps14JogAxis(const String &id, const String &line);
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
void sendOk(const String &id, const String &data);
void sendError(const String &id, const String &error);
void sendEvent(const String &event, const String &message);

void setup() {
  Serial.begin(115200);
  lastCommandAt = millis();
  sendEvent("boot", "CookBot Mega skeleton ready");
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      handleLine(line);
      lastCommandAt = millis();
    }
  }

  if (motionEnabled && millis() - lastCommandAt > WATCHDOG_TIMEOUT_MS) {
    motionEnabled = false;
    sendEvent("watchdog", "motion_disabled");
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
    sendOk(id, String("\"name\":\"CookBot Mega\",\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.1.0\",\"protocol_version\":1,\"hardware_configured\":") + configured + ",\"capabilities\":" + capabilitiesJson());
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
  delay(20);
  for (long index = 0; index < steps; index++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds((unsigned int)pulseUs);
    digitalWrite(stepPin, LOW);
    delayMicroseconds((unsigned int)stepDelayUs);
  }
  digitalWrite(enablePin, HIGH);

  sendOk(id, "\"jogged\":true,\"axis\":\"" + axis + "\",\"steps\":" + String(steps) + ",\"direction\":" + String(direction == 0 ? 0 : 1));
#else
  (void)line;
  sendError(id, "ramps14_commissioning_disabled");
#endif
}

void sendState(const String &id) {
  String data = "\"state\":{\"mode\":\"hardware\",\"estop\":";
  data += estopActive ? "true" : "false";
  data += ",\"homed\":";
  data += homed ? "true" : "false";
  data += ",\"calibrated\":false,\"motion_enabled\":";
  data += motionEnabled ? "true" : "false";
  data += ",\"services\":{\"mega\":\"serial\",\"backend\":\"external\"},\"axes\":[],\"gripper\":{\"position\":0,\"homed\":";
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
  return "{\"protocol_version\":1,\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.1.0\",\"hardware_configured\":" + configured + ",\"motion_commands_enabled\":false,\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"supported_commands\":[\"hello\",\"ping\",\"get_state\",\"get_capabilities\",\"get_hardware_config\",\"get_limit_switches\",\"self_test\",\"get_firmware_status\",\"read_inputs\",\"bench_unlock\",\"bench_test_output\",\"jog_axis\",\"get_faults\",\"inject_fault\",\"clear_faults\",\"enable_motion\",\"home_all\",\"set_joint\",\"set_gripper\",\"estop\",\"clear_estop\"]}";
}

String hardwareConfigJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  return "{\"hardware_configured\":" + configured + ",\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"axis_count\":" + String(COOKBOT_AXIS_COUNT) + ",\"limit_switch_count\":" + String(COOKBOT_LIMIT_SWITCH_COUNT) + ",\"estop_pin\":" + String(COOKBOT_ESTOP_PIN) + ",\"gripper_pin\":" + String(COOKBOT_GRIPPER_PIN) + ",\"axis_pin_configured\":" + ramps14CommissioningJson() + ",\"note\":\"ramps14_jog_only_no_autonomous_motion\"}";
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
  return "{\"ok\":true,\"hardware_configured\":" + configured + ",\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"motion_outputs_enabled\":" + ramps14CommissioningJson() + ",\"checks\":[{\"id\":\"serial\",\"ok\":true},{\"id\":\"hardware_config\",\"ok\":true,\"detail\":\"ramps14_commissioning_or_placeholder\"},{\"id\":\"motion_outputs\",\"ok\":true,\"detail\":\"jog_only\"},{\"id\":\"bench_outputs\",\"ok\":true,\"detail\":\"compile_time_locked\"}]}";
}

String firmwareStatusJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  return "{\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.1.0\",\"hardware_configured\":" + configured + ",\"bench_outputs_enabled\":" + benchOutputsEnabledJson() + ",\"ramps14_commissioning\":" + ramps14CommissioningJson() + ",\"bench_unlocked\":" + boolJson(benchUnlocked) + ",\"estop\":" + boolJson(estopActive) + ",\"motion_enabled\":" + boolJson(motionEnabled) + ",\"watchdog_timeout_ms\":" + String(WATCHDOG_TIMEOUT_MS) + "}";
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
  Serial.print("{\"id\":\"");
  Serial.print(id);
  Serial.print("\",\"ok\":true,\"data\":{");
  Serial.print(data);
  Serial.println("},\"error\":null}");
}

void sendError(const String &id, const String &error) {
  Serial.print("{\"id\":\"");
  Serial.print(id);
  Serial.print("\",\"ok\":false,\"data\":{},\"error\":\"");
  Serial.print(error);
  Serial.println("\"}");
}

void sendEvent(const String &event, const String &message) {
  Serial.print("{\"event\":\"");
  Serial.print(event);
  Serial.print("\",\"source\":\"mega\",\"message\":\"");
  Serial.print(message);
  Serial.println("\"}");
}
