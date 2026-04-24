# CookBot Recipe Format

Recipes are YAML files in `recipes/`.

Minimal fields:

```yaml
id: dry_run_stir_demo
name: Dry Run Stir Demo
description: No-heat supervised motion demo.
locked: false
requires_homing: true
steps:
  - type: move_joint
    joint_id: joint_1
    position: 10.0
    speed: 0.25
```

Supported no-hardware MVP steps:

- `recipe_note`
- `snapshot`
- `home_all`
- `move_joint`
- `set_gripper`
- `wait`

Recipes with unknown or forbidden steps fail preflight.

