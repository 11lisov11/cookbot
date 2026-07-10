# CookBot Wiring

Verified project facts:

- UNO Q communicates with Arduino Mega over USB Serial or Bluetooth Classic
  SPP/RFCOMM through a UART Bluetooth module.
- Motors/servos must use a separate power supply.
- Arduino 5V must not power motors or servos.
- Motor supply ground, Arduino Mega ground, and UNO Q ground must be common.
- ESTOP must disable motor/servo power or assert a motion-disable input to Mega.
- A vendor wiring image is stored at `docs/hardware_evidence/vendor_controller_wiring.png`.
- The vendor image labels motor connectors `A`, `B`, `C`, and a slider motor.
- The vendor image labels limit switches `A`, `B`, and `C`.
- The vendor image labels 12V input and 12V suction output terminals.
- User reported red A4988 stepstick-style stepper driver modules on the RAMPS controller.
- The vendor Android pendant confirms Bluetooth Classic SPP. For CookBot dual
  USB/Bluetooth operation, use a separate Mega hardware UART rather than
  sharing USB UART0.

Preferred CookBot Bluetooth UART:

- Mega `Serial2`, RX2 pin `17`, TX2 pin `16`;
- module TXD -> Mega RX2 (`17`);
- Mega TX2 (`16`) -> module RXD through the level shifting required by the
  exact module;
- common ground;
- module VCC only at the voltage supported by its carrier board.

`Serial1` is not used because Mega TX1 pin `18` is already the RAMPS `C_MIN`
limit input in the verified commissioning map. `Serial3` is not used because
Mega TX3 pin `14` is the RAMPS `A_MIN` input. The original vendor header in the
photo must be traced before reuse; do not assume it is `Serial2` from wire
colour alone.

Unknown until hardware inspection:

- Verified real axis count.
- A4988 module Rsense marking, Vref/current limit, microstepping jumpers, cooling margin, and enable polarity.
- Arduino Mega STEP/DIR/EN pin map.
- Limit switch wiring polarity and triggered electrical state.
- Power current requirements.
- ESTOP or fused motion power path.

Do not wire real motion until `docs/vendor_robot_notes.md` is completed for the physical arm.
