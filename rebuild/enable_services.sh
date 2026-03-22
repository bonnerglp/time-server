#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/6] Installing systemd service files..."
sudo cp "$REPO_ROOT/snapshot/systemd/piksi-monitor.service" /etc/systemd/system/
sudo cp "$REPO_ROOT/snapshot/systemd/teensy-collector.service" /etc/systemd/system/
sudo cp "$REPO_ROOT/snapshot/systemd/teensy-dash2.service" /etc/systemd/system/
sudo cp "$REPO_ROOT/snapshot/systemd/teensy_logger.service" /etc/systemd/system/

echo "[2/6] Reloading systemd..."
sudo systemctl daemon-reload

echo "[3/6] Enabling services..."
sudo systemctl enable piksi-monitor.service
sudo systemctl enable teensy-collector.service
sudo systemctl enable teensy-dash2.service
sudo systemctl enable teensy_logger.service

echo "[4/6] Restarting services..."
sudo systemctl restart chrony
sudo systemctl restart piksi-monitor.service
sudo systemctl restart teensy-collector.service
sudo systemctl restart teensy-dash2.service
sudo systemctl restart teensy_logger.service

echo "[5/6] Installing pi crontab..."
crontab "$REPO_ROOT/snapshot/crontab_pi.txt"

echo "[6/6] Service enable step complete."
echo
echo "Verify with:"
echo "  systemctl list-units --type=service | grep -E 'chrony|teensy|piksi'"
echo "  ss -tulnp | grep 8082"
echo "  chronyc sources -v"
