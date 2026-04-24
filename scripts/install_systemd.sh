#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR=${1:-/opt/cookbot}
SERVICE_DIR=${2:-/etc/systemd/system}

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/install_systemd.sh [$INSTALL_DIR]" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR"
rsync -a --delete \
  --exclude web/node_modules \
  --exclude web/dist \
  --exclude .venv \
  --exclude __pycache__ \
  --exclude .pytest_cache \
  ./ "$INSTALL_DIR/"

python3 -m pip install -r "$INSTALL_DIR/requirements.txt"
(cd "$INSTALL_DIR/web" && npm install && npm run build)

install -m 0644 "$INSTALL_DIR/deploy/systemd/cookbot-backend.service" "$SERVICE_DIR/cookbot-backend.service"
install -m 0644 "$INSTALL_DIR/deploy/systemd/cookbot-fake-mega.service" "$SERVICE_DIR/cookbot-fake-mega.service"

systemctl daemon-reload
systemctl enable cookbot-backend.service

echo "CookBot installed to $INSTALL_DIR"
echo "Start with: systemctl start cookbot-backend.service"

