# Mobile Use

The PWA is designed for a phone on the same trusted local network.

## Localhost Development

On the development machine:

```powershell
python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000
cd web
npm run dev
```

Use `http://127.0.0.1:5173` locally.

## Phone Access

For phone access, bind explicitly to a LAN address and keep the service on a trusted network:

```powershell
$env:COOKBOT_BIND="0.0.0.0"
python -m uvicorn unoq_backend.app:app --host 0.0.0.0 --port 8000
```

Set the backend URL in first-run setup, for example `http://192.168.1.20:8000`. If `COOKBOT_API_TOKEN` is set, enter the same token in Settings.

## Safety Notes

The sticky ESTOP remains visible in the PWA. In v0.1 it stops simulator/fake Mega motion only. Physical emergency stop wiring must be verified before any real motor output is enabled.

