#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 \"commit message\""
  exit 1
fi

cd ~/time-server

echo "[1/4] Refreshing STATE_SNAPSHOT.txt..."
~/time-server/rebuild/dump_state.sh > ~/time-server/STATE_SNAPSHOT.txt

echo "[2/4] Staging changes..."
git add STATE_SNAPSHOT.txt
git add .

echo "[3/4] Committing..."
git commit -m "$*"

echo "[4/4] Pushing..."
git push

echo
echo "Done."
