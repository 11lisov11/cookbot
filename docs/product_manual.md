# CookBot Product Manual

CookBot v0.1 is a finished no-hardware product for local demonstration and software validation. It runs with simulator mode, fake Mega transport, mock camera, mock AI, YAML recipes, safety validation, diagnostics, backups, and a mobile-first PWA.

## Operating Modes

- No-hardware mode is the supported v0.1 mode.
- Real motion is locked until hardware readiness is verified with evidence.
- Heating, knives, relays, raw Mega commands, arbitrary code execution, and autonomous cooking are rejected by the safety layer.

## Daily Flow

1. Start the backend.
2. Open the PWA.
3. Complete first-run setup with backend URL and optional API token.
4. Check Product Readiness.
5. Use Control for homing/manual simulator motion.
6. Use Recipes for no-heat demos.
7. Use Diagnostics and Hardware Gate before any later hardware work.

## Product Readiness

The `/product/readiness` endpoint combines acceptance, diagnostics, and hardware gate state. For v0.1, the expected ready state is `no_hardware_product_ready` with real motion locked.

## Backup And Restore Validation

`GET /backup` creates a safe bundle containing workspace, hardware readiness, calibration status, recipes, and acceptance. `POST /restore/validate` checks a bundle shape and refuses bundles that try to apply real-motion readiness automatically.

