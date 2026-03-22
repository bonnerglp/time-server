#!/usr/bin/env bash
set -u

echo "==== SYSTEM OVERVIEW ===="
echo "Raspberry Pi Time Server"
echo "Generated: $(date -Is)"
echo

echo "==== ACTIVE SERVICES ===="
systemctl list-units --type=service --all | grep -E 'chrony|teensy|piksi' || echo "No matching services found"
echo

echo "==== LISTENING PORTS ===="
ss -tulnp | grep -E '(:8082|:8081|:123\b|:2947\b)' || echo "No expected ports found"
echo

echo "==== CHRONY STATUS ===="
chronyc tracking || true
echo
chronyc sources -v || true
echo

echo "==== PPS DEVICES ===="
ls -l /dev/pps* 2>/dev/null || echo "No /dev/pps devices found"
echo

echo "==== CRONTAB (pi) ===="
crontab -l 2>/dev/null || echo "No crontab for pi"
echo

echo "==== PROJECT STRUCTURE ===="
find ~/time-server/snapshot -maxdepth 2 -type d 2>/dev/null || echo "Snapshot directory not found"
echo

echo "==== GIT STATUS ===="
cd ~/time-server 2>/dev/null || exit 1
git log --oneline -n 5 || true
git status --short || true
echo

echo "==== RECENT TIMING FILES ===="
find /home/pi/timing -maxdepth 1 -type f \
  \( -name "*.log" -o -name "*.txt" -o -name "*.html" -o -name "*.png" \) \
  -printf "%TY-%Tm-%Td %TH:%TM  %9s  %f\n" 2>/dev/null | sort || true
echo

echo "==== DATABASE STATUS ===="

for db in \
  /home/pi/timing/timing.db \
  /home/pi/teensy_appliance/teensy_stats.db \
  /mnt/*/*.db \
  /mnt/*/*/*.db
do
  if [ -f "$db" ]; then
    size=$(du -h "$db" | cut -f1)
    mtime=$(date -r "$db" "+%Y-%m-%d %H:%M:%S")
    echo "[INFO] DB: $db"
    echo "       Size: $size"
    echo "       Last updated: $mtime"
  fi
done

echo
echo "==== SELF-DIAGNOSIS ===="
fail=0

check_service() {
  local svc="$1"
  if systemctl is-active --quiet "$svc"; then
    echo "[OK]   Service running: $svc"
  else
    echo "[FAIL] Service not running: $svc"
    fail=1
  fi
}

check_port() {
  local port="$1"
  if ss -tuln | grep -q ":$port "; then
    echo "[OK]   Port listening: $port"
  else
    echo "[FAIL] Port not listening: $port"
    fail=1
  fi
}

check_file() {
  local path="$1"
  if [ -e "$path" ]; then
    echo "[OK]   File exists: $path"
  else
    echo "[FAIL] Missing file: $path"
    fail=1
  fi
}

check_recent_file() {
  local path="$1"
  local max_age_sec="$2"
  if [ ! -e "$path" ]; then
    echo "[WARN] File missing: $path"
    return
  fi
  local now mtime age
  now=$(date +%s)
  mtime=$(stat -c %Y "$path" 2>/dev/null || echo 0)
  age=$((now - mtime))
  if [ "$age" -le "$max_age_sec" ]; then
    echo "[OK]   Recently updated: $path (age ${age}s)"
  else
    echo "[WARN] Stale file: $path (age ${age}s)"
  fi
}

check_service chrony.service
check_service teensy-collector.service
check_service teensy-dash2.service
check_service teensy_logger.service
check_service piksi-monitor.service

check_port 8082

if ls /dev/pps* >/dev/null 2>&1; then
  echo "[OK]   PPS device present"
else
  echo "[FAIL] No PPS device present"
  fail=1
fi

if chronyc sources 2>/dev/null | grep -q '^\#\* PPS'; then
  echo "[OK]   Chrony currently locked to PPS"
else
  echo "[WARN] Chrony not currently showing PPS as selected source"
fi

check_file /etc/chrony/chrony.conf
check_file /usr/local/bin/timing_daily_backup.sh
check_file /home/pi/timing/send_timing_report.sh
check_file /home/pi/timing/aggregate_10min.py
check_file /home/pi/timing/plot_timing_report.py
check_file /home/pi/timing/prune_timing_db.py
check_file /home/pi/timing/teensy_logger.py
check_file /home/pi/teensy_appliance/collector.py
check_file /home/pi/teensy_dash2/app.py

check_recent_file /home/pi/timing/aggregate.log 7200
check_recent_file /home/pi/timing/plot.log 7200
check_recent_file /home/pi/timing/report.log 93600
check_recent_file /home/pi/timing/backup.log 93600
check_recent_file /home/pi/timing/piksi_monitor.log 7200
check_recent_file /home/pi/timing/teensy_logger.out 7200

echo
if [ "$fail" -eq 0 ]; then
  echo "==== OVERALL RESULT: PASS ===="
  exit 0
else
  echo "==== OVERALL RESULT: FAIL ===="
  exit 1
fi
