# Mega to UNO Q Bluetooth Link

CookBot carries its newline-delimited JSON protocol over Bluetooth Classic
SPP/RFCOMM. The bytes and safety rules are identical to USB Serial; only the
transport changes.

## Data path

```text
Mega 2560 firmware -> Serial2 UART -> HC-05/HC-06-style SPP module
-> Bluetooth RFCOMM -> UNO Q Debian/BlueZ -> CookBot FastAPI
-> Home Assistant REST package and CookBot PWA over Wi-Fi
```

The UNO Q Linux side owns Bluetooth. No UNO Q Zephyr/MCU sketch is required for
this link.

## Mega wiring

The CookBot Bluetooth firmware profile uses Mega `Serial2`:

- Mega RX2 pin `17` receives module TXD.
- Mega TX2 pin `16` drives module RXD through the level conversion required by
  the exact module.
- Grounds must be common.
- Module VCC must match its carrier board specification.

Do not use `Serial1` in the current RAMPS map: TX1 pin `18` is `C_MIN`. Do not
use `Serial3`: TX3 pin `14` is `A_MIN`. Do not share UART0 with the USB serial
converter for normal dual-link operation.

The compile-time UART baud defaults to `9600`, which is common for unconfigured
HC-05/HC-06 data mode, but the physical module value is not yet verified. If
its AT configuration reports another baud, change `COOKBOT_BLUETOOTH_BAUD` and
rebuild.

## Build firmware

```powershell
pio run -e cookbot_mega2560_ramps14_bluetooth
pio run -e cookbot_mega2560_ramps14_bluetooth -t upload --upload-port COM_MEGA
```

Replace `COM_MEGA` only after reading the ATmega2560 signature. Never select a
port merely because it is the first COM device; during the current check,
`COM3` identified as a WCH `UsbMonitor`, not the Mega. The profile includes
the existing supervised RAMPS commissioning commands; it does not implement
vendor Cartesian inverse kinematics or autonomous motion.

## Pair on UNO Q

Discover the module and record its MAC address first:

```bash
bluetoothctl scan on
```

From the Windows workstation through ADB:

```powershell
python scripts/hardware_tooling.py unoq-bluetooth-check --address AA:BB:CC:DD:EE:FF
python scripts/hardware_tooling.py unoq-bluetooth-pair --address AA:BB:CC:DD:EE:FF --pin 1234
python scripts/hardware_tooling.py unoq-bluetooth-probe --address AA:BB:CC:DD:EE:FF --channel 1
```

The pairing script requires `bluez` and `expect` on UNO Q. Never commit the
module PIN or API token. Verify the SPP channel with SDP when the module does
not use channel `1`:

```bash
sdptool browse AA:BB:CC:DD:EE:FF
```

## Backend settings

```text
COOKBOT_MODE=hardware
COOKBOT_MEGA_TRANSPORT=bluetooth_rfcomm
COOKBOT_BLUETOOTH_ADDRESS=AA:BB:CC:DD:EE:FF
COOKBOT_BLUETOOTH_CHANNEL=1
COOKBOT_BLUETOOTH_TIMEOUT_S=3
COOKBOT_HARDWARE_CONFIGURED=false
```

`COOKBOT_HARDWARE_CONFIGURED` remains false until all physical readiness
evidence is complete. Bluetooth connectivity alone does not unlock motion.

The RFCOMM transport keeps one connection open, serializes requests, ignores
asynchronous boot/watchdog events while waiting for the matching response ID,
and reconnects once for read-only/status requests and ESTOP. It never
automatically replays motion, homing, output, or ESTOP-clear commands after an
ambiguous link loss.

## Home Assistant boundary

Home Assistant reads CookBot status through the local REST API and exposes an
emergency-stop action. It does not receive raw motor, G-code, recipe-run, or
ESTOP-clear access. Motion stays behind CookBot's authenticated safety API.
