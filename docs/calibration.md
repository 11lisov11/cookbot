# CookBot Calibration

The no-hardware MVP includes a simulator-only calibration endpoint:

```text
POST /calibration/simulate
```

This marks simulated axes as calibrated for UI and workflow testing. It is not a substitute for real calibration.

Calibration persistence endpoints:

- `GET /calibration/status`
- `POST /calibration/save`
- `POST /calibration/reset`

The saved file defaults to `config/calibration.json`. It stores simulator axis ranges and calibration flags only.

Real calibration must record:

- verified axis names;
- pin map;
- switch polarity;
- safe min/max limits;
- speed limits;
- motion direction for homing;
- fault handling result.

Until those values are verified, the firmware skeleton rejects real `set_joint` and `set_gripper` motion.
