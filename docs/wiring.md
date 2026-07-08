# CookBot Wiring

Verified project facts:

- UNO Q communicates with Arduino Mega over USB Serial or UART.
- Motors/servos must use a separate power supply.
- Arduino 5V must not power motors or servos.
- Motor supply ground, Arduino Mega ground, and UNO Q ground must be common.
- ESTOP must disable motor/servo power or assert a motion-disable input to Mega.
- A vendor wiring image is stored at `docs/hardware_evidence/vendor_controller_wiring.png`.
- The vendor image labels motor connectors `A`, `B`, `C`, and a slider motor.
- The vendor image labels limit switches `A`, `B`, and `C`.
- The vendor image labels 12V input and 12V suction output terminals.
- User reported red A4988 stepstick-style stepper driver modules on the RAMPS controller.

Unknown until hardware inspection:

- Verified real axis count.
- A4988 module Rsense marking, Vref/current limit, microstepping jumpers, cooling margin, and enable polarity.
- Arduino Mega STEP/DIR/EN pin map.
- Limit switch wiring polarity and triggered electrical state.
- Power current requirements.
- ESTOP or fused motion power path.

Do not wire real motion until `docs/vendor_robot_notes.md` is completed for the physical arm.
