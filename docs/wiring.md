# CookBot Wiring

Verified project facts:

- UNO Q communicates with Arduino Mega over USB Serial or UART.
- Motors/servos must use a separate power supply.
- Arduino 5V must not power motors or servos.
- Motor supply ground, Arduino Mega ground, and UNO Q ground must be common.
- ESTOP must disable motor/servo power or assert a motion-disable input to Mega.

Unknown until hardware inspection:

- Real axis count.
- Motor/servo driver type.
- Pin map.
- Limit switch wiring polarity.
- Power current requirements.

Do not wire real motion until `docs/vendor_robot_notes.md` is completed for the physical arm.

