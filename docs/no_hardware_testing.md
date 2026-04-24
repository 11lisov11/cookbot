# CookBot No-Hardware Testing

Run all checks on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
```

Run all checks on Linux/UNO Q:

```bash
bash scripts/check_all.sh
```

The check scripts run:

- pytest suite;
- Python compileall;
- backend smoke test;
- fake Mega TCP smoke test;
- web build;
- Arduino Mega compile when `arduino-cli` is installed.

No test requires real Mega, real camera, real AI key, or real robot arm.

The test suite also covers:

- multipart mock camera stream;
- calibration save/reset;
- recipe runtime status, pause, resume, abort;
- workspace model loading;
- diagnostics and simulator fault injection;
- no-hardware acceptance report;
- calibration wizard flow;
- OpenAI-compatible client parsing through a mocked HTTP response.

UNO Q service templates:

- `deploy/systemd/cookbot-backend.service`
- `deploy/systemd/cookbot-fake-mega.service`
- `scripts/install_systemd.sh`
