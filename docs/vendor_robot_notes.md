# CookBot Vendor Robot Notes

Confirmed from user context:

- Hardware includes Arduino UNO Q.
- Hardware includes Arduino Mega.
- The arm is an AliExpress robotic arm.
- There is one gripper attachment.
- There are no interchangeable tools.
- There are no absolute encoders or force/torque sensors.
- Limit switches are present on motors/axes.
- Vendor wiring image is stored at `docs/hardware_evidence/vendor_controller_wiring.png`.
- The image shows three labeled arm axes or motors `A`, `B`, and `C`, plus a separate slider motor.
- The image shows three labeled limit switches `A`, `B`, and `C`.
- The image shows 12V power input and 12V suction output terminals.
- The image shows a Bluetooth/UART module connection labeled RXD, TXD, GND, and VCC.
- User inspection found gearbox marking `P/N FLE 42-010`, `S/N H202600130` on the two lift-arm motors `A` and `B`.
- User inspection found gearbox marking `P/N FLE 42-010`, `S/N H202600230` on motor `C`.
- Public FLE42 gearbox listings indicate `010` corresponds to a likely `10:1` ratio, but this still needs exact vendor datasheet confirmation.
- The slider motor has no external gearbox per user inspection.
- User reported red A4988 stepstick-style stepper drivers on the RAMPS controller.

Unconfirmed:

- verified real axis count;
- Mega STEP/DIR/EN pin map;
- A4988 module Rsense marking, Vref/current limit, enable polarity, cooling margin, and microstepping;
- servo or motor model;
- link dimensions;
- final manufacturer-verified gearbox datasheet and exact output ratio tolerance;
- travel limits;
- current draw;
- switch polarity;
- ESTOP circuit or motion power cut path;
- mechanical hard-stop geometry.

Important: the vendor wiring image is useful evidence for connector labels, but it is
not enough to unlock real motion. It does not prove Arduino Mega pin mapping, driver
settings, limit switch polarity, safe homing directions, axis travel limits, or ESTOP
behavior.

Safe defaults in this repository:

- simulator-only axes: `joint_1`, `joint_2`, `joint_3`;
- simulator-only limits: -45 to 45;
- simulator-only gripper range: 0 to 1;
- firmware rejects real motion until hardware configuration is verified.

Manual verification required before real motion:

- photograph and trace wiring;
- identify every motor/servo driver;
- identify limit switch normal state and triggered state;
- verify external motor power and common ground;
- test ESTOP physically cuts or disables motion;
- define safe home direction for each axis;
- measure safe software limits at low power.

Mirror the completed verification state in `config/hardware_readiness.yaml`. CookBot treats missing evidence as not ready for real motion.

When all required evidence is complete, transfer the verified pin map into `mega_firmware/cookbot_mega_firmware/hardware_config.h` before implementing real motion outputs.
