#!/usr/bin/env bash
set -euo pipefail

ADDRESS=""
PIN="1234"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --address) ADDRESS=${2:-}; shift 2 ;;
    --pin) PIN=${2:-}; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! $ADDRESS =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
  echo "bluetooth_address_invalid" >&2
  exit 2
fi
if [[ ! $PIN =~ ^[0-9]{4,16}$ ]]; then
  echo "bluetooth_pin_invalid" >&2
  exit 2
fi
if ! command -v bluetoothctl >/dev/null 2>&1; then
  echo "bluetoothctl_not_found" >&2
  exit 3
fi
if ! command -v expect >/dev/null 2>&1; then
  echo "expect_not_found: install the expect package on UNO Q" >&2
  exit 3
fi

sudo -n systemctl enable --now bluetooth >/dev/null 2>&1 || true
if bluetoothctl info "$ADDRESS" 2>/dev/null | grep -q 'Paired: yes'; then
  bluetoothctl trust "$ADDRESS" >/dev/null
  echo "paired=true trusted=true address=$ADDRESS"
  exit 0
fi

export COOKBOT_BT_ADDRESS=$ADDRESS
export COOKBOT_BT_PIN=$PIN
expect <<'EXPECT_SCRIPT'
set timeout 45
set address $env(COOKBOT_BT_ADDRESS)
set pin $env(COOKBOT_BT_PIN)
spawn bluetoothctl
expect "#"
send "power on\r"
expect "#"
send "agent KeyboardOnly\r"
expect "#"
send "default-agent\r"
expect "#"
send "scan on\r"
after 3000
send "pair $address\r"
expect {
  -re "PIN code:" { send "$pin\r"; exp_continue }
  -re "Confirm passkey" { send "yes\r"; exp_continue }
  -re "Pairing successful" {}
  -re "AlreadyExists" {}
  timeout { exit 4 }
}
send "trust $address\r"
expect "#"
send "scan off\r"
expect "#"
send "quit\r"
expect eof
EXPECT_SCRIPT

if ! bluetoothctl info "$ADDRESS" | grep -q 'Paired: yes'; then
  echo "bluetooth_pair_failed" >&2
  exit 4
fi
bluetoothctl trust "$ADDRESS" >/dev/null
echo "paired=true trusted=true address=$ADDRESS"
