# Troubleshooting

## Backend Does Not Start

Run:

```powershell
python -m compileall unoq_backend
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

Check that dependencies from `requirements-dev.txt` are installed.

## PWA Shows Token Required

`COOKBOT_API_TOKEN` is set. Open first-run setup or Settings, enter the token, and save it. The PWA stores it in browser local storage and sends `X-CookBot-Token`.

## Camera Is Blank

In no-hardware mode `COOKBOT_CAMERA=mock` should return an SVG snapshot. Check `/camera/snapshot`. For `libcamera`, verify the Linux camera stack separately.

## Recipe Will Not Run

Open Recipes and run preflight from the API if needed:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/recipes/dry_run_stir_demo/preflight -Method Post
```

Common reasons are `not_homed`, `estop_active`, `recipe_locked`, `workspace_not_verified`, `calibration_required`, or `real_motion_locked`.

## Real Motion Is Locked

This is expected in v0.1. Do not bypass it. Fill `config/hardware_readiness.yaml`, document evidence, configure real firmware pins, verify physical ESTOP and limit switches, then create a separate hardware-enabling change.

