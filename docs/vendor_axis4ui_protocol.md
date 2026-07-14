# AXIS4UI Vendor Controller Analysis

The local `AXIS4UI` bundle supplied with the robot was inspected statically. The
unsigned Windows executable was not launched. The analysis used its PyInstaller
archive, its Qt Designer XML resource (`Pyud.dll`), and the decompiled Android
application. Third-party binaries remain local and are ignored by Git.

The extraction method, bytecode/APK findings, and native-code boundary are in
`docs/vendor_axis4ui_reverse_engineering.md`.

## Identity and hashes

- Desktop UI: `Red Sun Global - Robot Arm Four Axis Teaching Controller v1.12`.
- Android UI: `RA Pendant` version `1.01`, package
  `com.ai2offline.test.RA__Pendant1`.
- `AXIS4UI.exe` SHA-256:
  `FEA9B588DB446B81532F94B9A32E908E2BE4F799638B8C4B757D5997EA6D8263`.
- `Pyud.dll` SHA-256:
  `1E00239966956997B8690CF9A728ED0B56A1D37919010E212CFB247879104ACA`.
- `RA__Pendant1.01.apk` SHA-256:
  `D9CB12E40DAAA694B059452840824E3AA604C54AFE11076ECB2B8DB57B83F5FA`.

`Pyud.dll` is not a native DLL. It is UTF-8 Qt Designer XML loaded by the
desktop Python application.

## Transport

- Desktop default: serial `115200` baud. The selectable values are `9600`,
  `19200`, `38400`, `57600`, `74880`, `115200`, and `230400`.
- Commands are ASCII and end with carriage return (`\r`).
- The Android app uses Bluetooth Classic Serial Port Profile (SPP) over
  RFCOMM. Its App Inventor Bluetooth client uses the standard SPP UUID
  `00001101-0000-1000-8000-00805f9b34fb`.
- The desktop UI reads line-oriented controller feedback. After a move it
  searches the received text for `X`, `Y`, `Z`, and `E` coordinate fields.
- Desktop jogs include `F`; Android jogs omit it and rely on controller state.

Bluetooth SPP transports bytes only. The UART baud between the Bluetooth
module and Mega is a separate module setting and cannot be recovered from the
Android APK. It must be measured or checked in the module's AT configuration.

## Coordinate protocol

The vendor controller accepts four-coordinate G-code. `X/Y/Z` are Cartesian
tool coordinates; `E` is labelled `Slide table`. These are not direct A/B/C
motor step counts.

```text
G1 X0 Y205 Z135 E-500 F100\r
G90\r
G91\r
G92 X0 Y100 Z0\r
G4 S1\r
```

The UI labels `F` as mm/s and constrains both jog and program speeds to
`5..150`, default `100`. The precise increment defaults to `1`; the quick
increment defaults to `10`.

No separate global speed-percentage setting was recovered from either host
application. A claimed default such as 30% or 50% therefore cannot be changed
in the supplied AXIS4UI/RA Pendant software without evidence from the missing
controller firmware or service configuration.

Observed reference positions:

| UI action | Command |
| --- | --- |
| Calibration reference | `G1 X0 Y205 Z100` |
| Vertical | `G1 X0 Y140 Z-30` |
| Stretch | `G1 X0 Y320 Z0` |
| Contract | `G1 X0 Y155 Z-40` |
| Vendor reset/calibration | `G2696` |

The desktop application sends program lines with a fixed `0.5 s` host delay.
This delay is not motor pulse timing and must not be copied into the A4988 step
generator. It also does not wait for an acknowledgement or motion-complete
response before transmitting the next program line.

## Output commands

| Command | Vendor UI meaning |
| --- | --- |
| `M6216` | Driver enable ON |
| `M6228` | Driver enable OFF |
| `M211` | Cooling fan ON |
| `M212` | Cooling fan OFF |
| `M14` | Vacuum/sucker ON |
| `M15` | Vacuum/sucker OFF |
| `M26` | Gripper ON |
| `M27` | Gripper OFF |
| `M61` | Execution/auxiliary output HIGH |
| `M62` | Execution/auxiliary output LOW |
| `M11`, `M12` | Ambiguous auxiliary pair; desktop symbols call it a second sucker while visible labels refer to end-switch A/B |

The ambiguity around `M11/M12` is retained intentionally. These commands must
not be connected to a safety input or exposed to recipes until traced on the
physical board.

## What this resolves

- Four logical machine coordinates are confirmed: `X`, `Y`, `Z`, and slider
  `E`.
- The vendor software is coordinate-based and includes a motion planner in its
  controller firmware; it does not issue raw A4988 steps from the desktop app.
- The normal host link is compatible with Bluetooth Classic SPP/RFCOMM.
- Default serial speed, motion speed range, startup coordinates, and output
  command numbers are now evidenced.

## Still unknown

- Vendor inverse-kinematics equations and arm link dimensions.
- Steps/mm or steps/degree for each motor, including microstep jumper state.
- Complete response grammar and controller error codes.
- Safe Cartesian workspace and collision envelope.
- Bluetooth module model, configured UART baud, PIN, MAC address, and RFCOMM
  channel on the physical robot.
- Physical meaning of `M11/M12`.

The supplied bundle contains no controller firmware or EEPROM parameter dump.
Consequently, "coordinate settings" means the missing steps-per-unit,
microstep, transmission, acceleration, geometry, and kinematic data described
in `docs/coordinate_motion_calibration.md`; those values cannot be recovered
from this EXE/APK.

CookBot therefore does not execute vendor G-code directly. The JSON safety
protocol remains authoritative until kinematics, calibration, limits, and
ESTOP are physically verified.
