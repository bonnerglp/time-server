#!/usr/bin/env bash
set -euo pipefail

cd ~/time-server
mkdir -p /home/pi/timing
chmod +x ~/time-server/monitoring/zed_monitor.py
sudo cp ~/time-server/systemd/zed-monitor.service /etc/systemd/system/zed-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable zed-monitor.service
sudo systemctl restart zed-monitor.service
sleep 2
sudo systemctl --no-pager --full status zed-monitor.service || true
