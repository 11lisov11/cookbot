# Release Checklist

Use this checklist before tagging a no-hardware release.

- `python -m pytest tests/` passes.
- `python -m compileall unoq_backend` passes.
- backend smoke passes.
- fake Mega smoke passes.
- `npm install` and `npm run build` pass in `web/`.
- `arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware` passes when Arduino CLI is available.
- `/acceptance` reports `ok: true`.
- `/product/readiness` reports `no_hardware_product_ready`.
- `config/hardware_readiness.yaml` still keeps real motion locked unless hardware evidence exists.
- GitHub Actions workflow is present.
- README and release notes describe the no-hardware boundary.

