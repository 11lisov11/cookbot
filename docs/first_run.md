# CookBot First Run

Windows development:

```powershell
python -m pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

UNO Q Debian:

```bash
python3 -m pip install -r requirements-dev.txt
bash scripts/check_all.sh
python3 -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

For phone access, bind to the UNO Q LAN address only after local checks pass:

```bash
COOKBOT_BIND=192.168.x.x python3 -m uvicorn unoq_backend.app:app --host 192.168.x.x --port 8000
```

Do not expose CookBot control to the public internet.

Real camera trial on UNO Q/Linux:

```bash
COOKBOT_CAMERA=libcamera python3 -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
```

The backend uses `libcamera-still` for snapshots. If the camera command fails, CookBot reports camera failure and does not enable any motion by itself.
