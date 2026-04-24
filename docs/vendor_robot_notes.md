# CookBot Vendor Robot Notes

Confirmed from user context:

- Hardware includes Arduino UNO Q.
- Hardware includes Arduino Mega.
- The arm is an AliExpress robotic arm.
- There is one gripper attachment.
- There are no interchangeable tools.
- There are no absolute encoders or force/torque sensors.
- Limit switches are present on motors/axes.

Unconfirmed:

- real axis count;
- pin map;
- driver type;
- servo or motor model;
- link dimensions;
- gear ratios;
- travel limits;
- current draw;
- switch polarity;
- mechanical hard-stop geometry.

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
