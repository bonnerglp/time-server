#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/7] Copying timing files..."
rsync -av --delete "$REPO_ROOT/snapshot/timing/" /home/pi/timing/

echo "[2/7] Copying teensy appliance files..."
rsync -av --delete "$REPO_ROOT/snapshot/teensy_appliance/" /home/pi/teensy_appliance/

echo "[3/7] Copying teensy dashboard 2 files..."
rsync -av --delete "$REPO_ROOT/snapshot/teensy_dash2/" /home/pi/teensy_dash2/

echo "[4/7] Installing chrony config..."
sudo cp "$REPO_ROOT/snapshot/chrony/chrony.conf" /etc/chrony/chrony.conf

echo "[5/7] Installing backup script..."
sudo cp "$REPO_ROOT/snapshot/scripts/timing_daily_backup.sh" /usr/local/bin/timing_daily_backup.sh
sudo chmod +x /usr/local/bin/timing_daily_backup.sh

echo "[6/7] Setting file permissions..."
chmod +x /home/pi/timing/*.py 2>/dev/null || true
chmod +x /home/pi/timing/*.sh 2>/dev/null || true
chmod +x /home/pi/teensy_appliance/*.py 2>/dev/null || true
chmod +x /home/pi/teensy_dash2/*.py 2>/dev/null || true

echo "[7/7] Initializing timing database..."
python3 /home/pi/timing/init_db.py || true

echo "Deploy step complete."
