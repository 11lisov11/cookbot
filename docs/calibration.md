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

No-hardware calibration wizard endpoints:

- `GET /calibration/wizard/status`
- `POST /calibration/wizard/start`
- `POST /calibration/wizard/advance`
- `POST /calibration/wizard/reset`

The wizard walks through ESTOP confirmation, external power confirmation, no-real-motion confirmation, simulator homing, simulated calibration, and saving the simulator profile. It does not prove real hardware calibration.

Real calibration must record:

- verified axis names;
- pin map;
- switch polarity;
- safe min/max limits;
- speed limits;
- motion direction for homing;
- fault handling result.

Until those values are verified, the firmware skeleton rejects real `set_joint` and `set_gripper` motion.
