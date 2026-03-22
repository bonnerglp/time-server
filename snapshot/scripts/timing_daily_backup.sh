#!/bin/bash
set -euo pipefail

BACKUP_ROOT="/mnt/TIMESERVER/daily"
DATE="$(date +%F_%H%M)"
TMPDIR="/tmp/timing_backup_${DATE}"
DB_SRC="/home/pi/timing/timing.db"
ARCHIVE="$BACKUP_ROOT/timing_backup_${DATE}.tar.gz"

mkdir -p "$BACKUP_ROOT"
mkdir -p "$TMPDIR"

# SQLite-safe snapshot
if [ -f "$DB_SRC" ]; then
    sqlite3 "$DB_SRC" ".backup '$TMPDIR/timing_${DATE}.db'"
fi

# Capture cron + packages
crontab -l > "$TMPDIR/pi_cron.txt" 2>/dev/null || true
dpkg --get-selections > "$TMPDIR/packages.txt"
pip3 freeze > "$TMPDIR/pip_packages.txt" 2>/dev/null || true

# Create backup (allow warnings)
tar -czf "$ARCHIVE" \
    --warning=no-file-changed \
    --exclude='/home/pi/timing/*.log' \
    --exclude='/home/pi/timing/*.png' \
    --exclude='/home/pi/timing/*.html' \
    --exclude='/home/pi/timing/__pycache__' \
    --exclude='/home/pi/timing/*.tmp' \
    --exclude='/mnt/TIMESERVER/daily' \
    /home/pi/timing \
    /usr/local/bin \
    /etc/systemd/system \
    -C "$TMPDIR" . || true

# Cleanup
rm -rf "$TMPDIR"

# Retention
find "$BACKUP_ROOT" -maxdepth 1 -type f -name 'timing_backup_*.tar.gz' -mtime +30 -delete

echo "Backup complete: $ARCHIVE"
