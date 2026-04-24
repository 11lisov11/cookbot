# CookBot Homing and Limits

Limit switches are used for homing and end-stop detection. They are not absolute position sensors.

CookBot tracks:

- commanded position;
- home state;
- calibration state;
- limit switch state.

CookBot does not claim to know true physical position without encoders. After ESTOP, manual movement while unpowered, communication loss, limit switch fault, or stall, the system requires re-home before motion.

Simulator defaults:

- `joint_1`: -45 to 45
- `joint_2`: -45 to 45
- `joint_3`: -45 to 45
- `gripper`: 0 to 1

These are placeholders only.

