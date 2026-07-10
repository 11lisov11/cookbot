#!/usr/bin/env bash
set -euo pipefail

ADDRESS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --address) ADDRESS=${2:-}; shift 2 ;;
    *) echo "unknown_argument:$1" >&2; exit 2 ;;
  esac
done

if [[ -n $ADDRESS && ! $ADDRESS =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
  echo "bluetooth_address_invalid" >&2
  exit 2
fi

command -v bluetoothctl >/dev/null 2>&1 || { echo "bluetoothctl_not_found" >&2; exit 3; }
command -v python3 >/dev/null 2>&1 || { echo "python3_not_found" >&2; exit 3; }
systemctl is-active --quiet bluetooth.service || { echo "bluetooth_service_inactive" >&2; exit 4; }

ADAPTER=$(bluetoothctl show 2>&1) || { echo "bluetooth_adapter_unavailable" >&2; exit 4; }
grep -q 'Powered: yes' <<<"$ADAPTER" || { echo "bluetooth_adapter_not_powered" >&2; exit 4; }

python3 - <<'PY'
import socket

required = ("AF_BLUETOOTH", "BTPROTO_RFCOMM")
missing = [name for name in required if not hasattr(socket, name)]
if missing:
    raise SystemExit("bluetooth_rfcomm_python_unsupported:" + ",".join(missing))
try:
    handle = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
except OSError as exc:
    raise SystemExit(f"bluetooth_rfcomm_kernel_unsupported:{exc}") from exc
handle.close()
print("rfcomm_socket=true")
PY

CONTROLLER=$(sed -n 's/^[[:space:]]*Controller \([^[:space:]]*\).*/\1/p' <<<"$ADAPTER" | head -n1)
echo "bluetooth_service=true"
echo "bluetooth_powered=true"
echo "bluetooth_controller=${CONTROLLER:-unknown}"

if [[ -n $ADDRESS ]]; then
  INFO=$(bluetoothctl info "${ADDRESS^^}" 2>&1 || true)
  if grep -q 'Paired: yes' <<<"$INFO"; then
    echo "device_paired=true"
  else
    echo "device_paired=false"
  fi
  if grep -q 'Trusted: yes' <<<"$INFO"; then
    echo "device_trusted=true"
  else
    echo "device_trusted=false"
  fi
fi
