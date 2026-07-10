# Smart Home Integration

Arduino UNO Q is the local Wi-Fi/Bluetooth hub. Its Debian side runs BlueZ,
CookBot FastAPI, and Home Assistant Container. The Arduino Mega remains the
real-time RAMPS/A4988 controller and talks to UNO Q through a Bluetooth Classic
SPP module connected to Mega `Serial2`.

```text
Mega + RAMPS -> Serial2 -> Bluetooth SPP/RFCOMM -> UNO Q BlueZ
              -> CookBot :8000 -> Home Assistant :8123 -> local Wi-Fi clients
```

## Deployment boundary

No UNO Q MCU sketch is required for this architecture. Wi-Fi, Bluetooth,
Docker, systemd, and the CookBot API run on the Debian MPU. Flashing the UNO Q
STM32/Zephyr MCU would not provide the RFCOMM link and could replace an
unrelated App Lab sketch, so the deployment scripts intentionally leave it
unchanged.

The Mega firmware target is:

```bash
pio run -e cookbot_mega2560_ramps14_bluetooth
```

It keeps USB Serial active for recovery and adds the same newline JSON protocol
on `Serial2` at a compile-time default of `9600` baud. That UART baud is not the
Bluetooth air rate and must match the physical module configuration.

## Home Assistant surface

`deploy/homeassistant/cookbot_package.yaml` imports CookBot state and exposes
only an emergency-stop action. It deliberately does not expose motion, raw
Mega commands, recipe start, heating, or ESTOP reset. The package authenticates
to CookBot with `cookbot_api_token` from Home Assistant `secrets.yaml`.

The complete ADB installer and local validation scripts are maintained in
`C:\\Умный дом`. The installer:

1. checks a current non-root ADB image;
2. deploys CookBot and its PWA;
3. installs BlueZ, Docker Engine, and Home Assistant Container;
4. checks kernel/Python RFCOMM support;
5. installs a token-protected CookBot systemd service;
6. optionally pairs an explicitly selected Bluetooth address;
7. runs protocol-only `hello`, `ping`, status, self-test, and input checks.

## Compatibility gate

Arduino documentation confirms that UNO Q contains a WCBN3536A/WCN3980
Bluetooth 5.1 radio. A version number alone is not proof that the installed
Debian image exposes Bluetooth Classic RFCOMM. Deployment therefore requires a
live `bluetoothctl` adapter plus a successful `AF_BLUETOOTH/BTPROTO_RFCOMM`
socket check before selecting `COOKBOT_MEGA_TRANSPORT=bluetooth_rfcomm`.

The following physical values remain mandatory inputs and are never guessed:

- SPP module MAC address and PIN;
- module UART baud and logic voltage;
- RFCOMM channel discovered through SDP;
- verified common ground and safe Mega RX/TX level shifting.

Real-motion readiness remains independent from hub readiness. A working
Bluetooth link does not unlock motion while the hardware gate is incomplete.
