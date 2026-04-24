# Release Notes

## v0.1.0 No-Hardware Product

- FastAPI backend with simulator, fake Mega, mock camera, mock AI, recipe engine, safety validation, diagnostics, logs, schemas, acceptance, backup, restore validation, and product readiness endpoints.
- Mobile-first PWA with first-run setup, sticky ESTOP, tabbed Control/Recipes/Diagnostics/Calibration/Hardware Gate/Settings views, backup export, and restore validation.
- Fake Mega TCP/in-process protocol for no-hardware checks.
- Arduino Mega firmware skeleton that compiles while keeping hardware outputs disabled until verified configuration is added.
- Documentation for architecture, safety, calibration, no-hardware testing, mobile use, troubleshooting, and release checks.
- GitHub Actions CI for backend tests, compile checks, web build, smoke tests, and optional firmware compile.

Real cooking, heating, knife handling, relay control, and real motor movement are not enabled in this release.
