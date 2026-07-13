# AXIS4UI Reverse-Engineering Report

This report records reproducible facts recovered from the vendor bundle. The
unsigned desktop executable was not run while a real controller was attached.
Original vendor binaries and generated decompiler output remain ignored by Git.

## Artifact identification

| Artifact | Result |
| --- | --- |
| `AXIS4UI.exe` | PE32+ x86-64 Windows GUI, unsigned, PyInstaller archive, Python 3.9 |
| Python entry point | `AXIS4UI`, 23,316-byte marshalled code object |
| `Pyud.dll` | UTF-8 Qt Designer XML, not a native DLL |
| `RA__Pendant1.01.apk` | App Inventor Android app, package `com.ai2offline.test.RA__Pendant1` |

SHA-256 values are recorded in `docs/vendor_axis4ui_protocol.md` and
`config/vendor_controller_profile.yaml`.

The PyInstaller archive was listed and extracted with PyInstaller 6.20. Python
3.9 bytecode was recursively disassembled with `xdis/pydisasm`; `pycdc` was
built from its upstream source and used for partial source reconstruction. The
APK was decompiled with JADX 1.5.6. One framework class failed to decompile;
the application class `Screen1` and its Bluetooth handlers were recovered.

## Native-code boundary

The executable entry point at image RVA `0xB310` belongs to the PyInstaller
bootloader. Its imports are normal Windows GUI/runtime libraries. The robot UI
logic is Python bytecode loaded by the embedded Python interpreter. Therefore,
disassembling more bootloader machine code cannot reveal A4988 timing,
kinematics, or motor current settings.

No `.hex`, `.elf`, `.bin`, Arduino sketch, EEPROM image, or controller parameter
dump exists in the supplied bundle. The low-level vendor motion planner is not
present on the PC or in the APK.

## Desktop behavior

- Opens a selected serial port; default `115200` baud.
- Writes ASCII commands terminated by carriage return (`\r`).
- Reads feedback with blocking `readline()` and appends it to a text log.
- Precise and quick increments default to `1` and `10`.
- Jog and program feed default to `F100`; the visible range is `5..150 mm/s`.
- Jog handlers send `G1X...F...`, `G1Y...F...`, `G1Z...F...`, or `G1E...F...`.
- The displayed coordinate is updated after a fixed `100 ms`, based on the
  requested value rather than verified physical feedback.
- Program execution sends one line every `500 ms`. It does not wait for `ok`,
  queue capacity, or motion completion before sending the next line.
- Coordinate feedback parsing searches text for `X`, `Y`, `Z`, and `E` fields;
  it is not a structured or checksummed protocol.

The fixed host delays are UI pacing. They are not STEP pulse width or STEP
period and do not explain the slow shaft directly.

## Android behavior

- Uses Bluetooth Classic SPP/RFCOMM through the standard SPP UUID.
- Sends the same carriage-return-terminated G/M commands.
- Polls available receive bytes every `30 ms` and appends all received text.
- Android jog commands omit `F`, so the controller must retain a feed value or
  apply its firmware default.
- Multi-line text replaces newline with carriage return and is sent without
  motion-complete flow control.

## Recovered command set

| Command | Recovered meaning |
| --- | --- |
| `G1 X.. Y.. Z.. E.. F..` | Absolute or relative coordinate move |
| `G4 S..` | Dwell |
| `G90` / `G91` | Absolute / relative mode |
| `G92 X.. Y.. Z.. E..` | Set current coordinate |
| `G2696` | Vendor calibration/reset request; internal semantics unavailable |
| `M6216` / `M6228` | Driver enable on/off |
| `M211` / `M212` | Cooling fan on/off |
| `M14` / `M15` | Vacuum on/off |
| `M26` / `M27` | Gripper on/off |
| `M61` / `M62` | Execution output high/low |
| `M11` / `M12` | Ambiguous auxiliary pair |

CookBot implements this grammar in `unoq_backend/vendor_gcode.py` and a
hardware-free behavioral endpoint in `scripts/vendor_axis4ui_emulator.py`.
Validation never forwards commands to Mega.

## What "coordinate settings" means

The vendor applications contain only target coordinates and feed. The missing
controller converts them to motor motion using machine-specific data:

- full steps per motor revolution;
- A4988 microstep jumper state;
- gearbox ratio;
- slider screw/belt travel per revolution;
- joint zero offsets and steps per degree;
- arm link dimensions and inverse kinematics;
- per-axis acceleration and maximum STEP rate;
- coordinate and collision limits.

These values must come from the original controller firmware/EEPROM or from
physical measurement. Changing an `X/Y/Z` target is not a substitute for those
conversion parameters.

## Speed conclusion

CookBot's current A commissioning profile produces about `285.47 STEP/s`.
Assuming a 200-step motor, `1/16` microstepping, and the likely `10:1` gearbox,
that is about `0.535 output RPM`. This arithmetic explains the visibly slow
motion. However, previous tests also lost effective travel when the period was
reduced to `3000 us`, so raising STEP frequency alone is not a valid fix.

The unresolved fault domain is the physical driver and transmission: actual
MS1/MS2/MS3 state, A4988 Vref/Rsense current limit, winding pairs, supply
voltage at the driver during motion, driver cooling, coupler/gearbox slip, and
mechanical preload. A 5 A power-supply rating does not set 5 A motor current;
the A4988 current limit is set by Vref and Rsense.
