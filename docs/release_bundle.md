# Release Bundle

CookBot release bundles are local zip files for no-hardware field handoff. They package tracked source files, documentation, configs, scripts, built PWA assets when present, and PlatformIO Mega firmware artifacts when present.

The release manifest always keeps:

- `real_motion_locked=true`
- `ready_for_real_motion=false`

This package is for deployment and commissioning preparation only. It does not certify real motor movement.

## Build

Run the full check script first, or build the web/PWA and firmware artifacts manually. Then create the bundle:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release.ps1 --output dist/release --json
```

Linux/UNO Q:

```bash
bash scripts/build_release.sh --output dist/release --json
```

The build writes:

- `dist/release/cookbot-<version>-<commit>.zip`
- `dist/release/latest_release_path.txt`

## Validate

Validate the latest generated bundle:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1 --latest --output dist/release --json
```

Or validate a specific bundle:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1 dist/release/cookbot-0.3.0-<commit>.zip --json
```

Validation reads `COOKBOT_RELEASE_MANIFEST.json` inside the zip and checks every file size and SHA256 digest.

## Contents

Expected categories:

- `source`: tracked project files.
- `web_dist`: generated PWA production build, if `web/dist` exists.
- `mega_firmware_build`: PlatformIO `firmware.hex` and `firmware.elf` for locked, bench, and RAMPS/Bluetooth Mega builds, if `.pio/build` exists.

The bundle intentionally excludes `.git`, local logs, Python caches, `node_modules`, and generated release output.
