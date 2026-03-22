#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Updating apt package lists..."
sudo apt update

echo "[2/5] Installing core packages..."
sudo apt install -y \
  chrony \
  python3 \
  python3-pip \
  python3-venv \
  sqlite3 \
  git \
  rsync

echo "[3/5] Installing Python packages from captured environment..."
if [ -f snapshot/requirements_system.txt ]; then
  pip3 install -r snapshot/requirements_system.txt || true
fi

echo "[4/5] Creating required directories..."
mkdir -p /home/pi/timing
mkdir -p /home/pi/teensy_appliance
mkdir -p /home/pi/teensy_dash2

echo "[5/5] Package install step complete."
