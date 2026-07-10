# Connected Device Audit - 2026-07-10

This audit is read-only. No firmware was uploaded and no motor command was
sent during the device check.

## Windows enumeration

- `COM3`: `USB\\VID_1A86&PID_CA21\\CT21INCH`, bus description `UsbMonitor`.
  This is not identified as an Arduino Mega and must not be passed to avrdude.
- `COM4`: `USB\\VID_1D6B&PID_0121&MI_00`, bus description `CDC Serial`.
  Its parent USB composite device reports `Android`, but exposes only the CDC
  serial child (`MI_00`) in the current configuration.
- `arduino-cli board list` reports both ports as unknown.
- `adb devices -l` reports no authorized device, including after restarting
  the ADB daemon.

There is therefore no verified ATmega2560 upload port in the current device
set. Reading an AVR signature from either port would be unjustified: `COM3` is
a USB monitor, while `COM4` is a Linux/Android-style CDC gadget and may be the
UNO Q USB interface.

## UNO Q preparation

The local Arduino App Lab installer was checked before installation:

- file: `ArduinoAppLab_0.8.0_Windows_x86-64_installer.exe`;
- SHA-256: `007F7D4255F372D1B54ABCE6E0E3D473062E07ECB517D6094C54065160308376`;
- Authenticode status: valid;
- signer: Arduino SA.

It installed successfully to `C:\\Program Files\\Arduino\\Arduino App Lab`.
Initial UNO Q setup remains interactive because the official flow requires a
device name, password, Wi-Fi credentials, and possible Linux image update.
After that flow, `adb devices -l` must show exactly one device before CookBot
deployment proceeds.
