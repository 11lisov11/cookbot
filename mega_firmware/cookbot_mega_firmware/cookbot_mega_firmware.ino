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
bool simulatedFaultActive = false;
String simulatedFaultCode = "";
unsigned long lastCommandAt = 0;

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
    sendOk(id, String("\"name\":\"CookBot Mega\",\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.1.0\",\"protocol_version\":1,\"hardware_configured\":false,\"capabilities\":") + capabilitiesJson());
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
  if (command == "get_faults") {
    sendOk(id, "\"faults\":" + faultsJson());
    return;
  }
  if (command == "inject_fault") {
    simulatedFaultActive = true;
    simulatedFaultCode = "simulated_fault";
    motionEnabled = false;
    sendState(id);
    return;
  }
  if (command == "clear_faults") {
    simulatedFaultActive = false;
    simulatedFaultCode = "";
    motionEnabled = false;
    homed = false;
    sendState(id);
    return;
  }
  if (command == "get_state") {
    sendState(id);
    return;
  }
  if (command == "enable_motion") {
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
    sendState(id);
    return;
  }
  if (command == "clear_estop") {
    estopActive = false;
    motionEnabled = false;
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
  return "{\"protocol_version\":1,\"firmware\":\"cookbot_mega_firmware\",\"version\":\"0.1.0\",\"hardware_configured\":" + configured + ",\"motion_commands_enabled\":false,\"supported_commands\":[\"hello\",\"ping\",\"get_state\",\"get_capabilities\",\"get_hardware_config\",\"get_limit_switches\",\"self_test\",\"get_faults\",\"inject_fault\",\"clear_faults\",\"enable_motion\",\"home_all\",\"set_joint\",\"set_gripper\",\"estop\",\"clear_estop\"]}";
}

String hardwareConfigJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  return "{\"hardware_configured\":" + configured + ",\"axis_count\":" + String(COOKBOT_AXIS_COUNT) + ",\"limit_switch_count\":" + String(COOKBOT_LIMIT_SWITCH_COUNT) + ",\"estop_pin\":" + String(COOKBOT_ESTOP_PIN) + ",\"gripper_pin\":" + String(COOKBOT_GRIPPER_PIN) + ",\"axis_pin_configured\":false,\"note\":\"placeholder_only_real_motion_locked\"}";
}

String limitSwitchesJson() {
  return "{\"configured\":false,\"switches\":[]}";
}

String selfTestJson() {
  String configured = COOKBOT_HARDWARE_CONFIGURED ? "true" : "false";
  return "{\"ok\":true,\"hardware_configured\":" + configured + ",\"motion_outputs_enabled\":false,\"checks\":[{\"id\":\"serial\",\"ok\":true},{\"id\":\"hardware_config\",\"ok\":true,\"detail\":\"placeholder\"},{\"id\":\"motion_outputs\",\"ok\":true,\"detail\":\"disabled\"}]}";
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
