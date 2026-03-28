#!/usr/bin/env bash
set -u

green()  { printf "OK    %s\n" "$1"; }
red()    { printf "FAIL  %s\n" "$1"; }
yellow() { printf "WARN  %s\n" "$1"; }

fail=0

echo "================ TIME SERVER STATUS ================"
echo "Generated: $(date -Is)"
echo

echo "[ SYSTEM ROLE ]"
echo "Phase: Phase 1"
echo "Time server host: Raspberry Pi"
echo "Primary active timing source: Piksi PPS into Raspberry Pi / chrony"
echo "PPS fanout: Piksi PPS -> Raspberry Pi and Teensy"
echo "Ethernet/data fanout: Piksi Ethernet -> Raspberry Pi and Teensy"
echo "Teensy role: analytics / telemetry / measurement only"
echo "Teensy timing role: not yet disciplining Raspberry Pi"
echo "FE-5680A role: not yet integrated into active timing chain"
echo

echo "[ HARDWARE / SIGNAL CHAIN ]"
echo "Primary host:"
echo "  Raspberry Pi time server"
echo
echo "Current active timing chain:"
echo "  Piksi PPS -> Raspberry Pi PPS input -> chrony -> NTP service"
echo
echo "Current PPS distribution:"
echo "  Piksi PPS -> Raspberry Pi"
echo "  Piksi PPS -> Teensy"
echo
echo "Current Ethernet / data distribution:"
echo "  Piksi Ethernet -> Raspberry Pi"
echo "  Piksi Ethernet -> Teensy"
echo
echo "Current analytics chain:"
echo "  Teensy -> UDP telemetry collector -> logger -> dashboard"
echo
echo "Current active software components:"
echo "  chrony"
echo "  piksi-monitor.service"
echo "  teensy-collector.service"
echo "  teensy-dash2.service"
echo "  teensy_logger.service"
echo
echo "Planned / known project hardware:"
echo "  Piksi in current active chain"
echo "  ZED-F9T planned / available for later migration"
echo "  Teensy 4.1 for analytics / measurement / future discipline work"
echo "  FE-5680A planned for later holdover / discipline phase"
echo
echo "Repository model:"
echo "  Git stores source, config, services, rebuild scripts, and state snapshot"
echo "  Git does NOT store live DB history, logs, plots, or virtualenvs"
echo

echo "[ NETWORK ]"
echo "Hostname:"
hostname
echo "IP address(es):"
hostname -I 2>/dev/null || true
echo

echo "[ SERVICES ]"
for svc in chrony.service teensy-collector.service teensy-dash2.service teensy_logger.service piksi-monitor.service; do
  if systemctl is-active --quiet "$svc"; then
    green "$svc running"
  else
    red "$svc NOT running"
    fail=1
  fi
done
echo

echo "[ PORTS ]"
if ss -tuln | grep -q ":8082 "; then
  green "Dashboard listening on 8082"
else
  red "Dashboard NOT listening on 8082"
  fail=1
fi

if ss -tuln | grep -q ":123 "; then
  green "NTP port 123 listening"
else
  yellow "NTP port 123 not shown as listening"
fi
echo

echo "[ TIME SYNC ]"
if chronyc sources 2>/dev/null | grep -q '^\#\* PPS'; then
  green "PPS selected by chrony"
else
  yellow "PPS not currently selected by chrony"
fi

tracking_out="$(chronyc tracking 2>/dev/null || true)"
if [ -n "$tracking_out" ]; then
  stratum="$(printf '%s\n' "$tracking_out" | awk -F': ' '/Stratum/{print $2}')"
  refid="$(printf '%s\n' "$tracking_out" | awk -F': ' '/Reference ID/{print $2}')"
  systime="$(printf '%s\n' "$tracking_out" | awk -F': ' '/System time/{print $2}')"
  lastoff="$(printf '%s\n' "$tracking_out" | awk -F': ' '/Last offset/{print $2}')"
  rmsoff="$(printf '%s\n' "$tracking_out" | awk -F': ' '/RMS offset/{print $2}')"
  freq="$(printf '%s\n' "$tracking_out" | awk -F': ' '/Frequency/{print $2}')"
  skew="$(printf '%s\n' "$tracking_out" | awk -F': ' '/Skew/{print $2}')"
  leap="$(printf '%s\n' "$tracking_out" | awk -F': ' '/Leap status/{print $2}')"

  echo "Reference ID : ${refid:-unknown}"
  echo "Stratum      : ${stratum:-unknown}"
  echo "System time  : ${systime:-unknown}"
  echo "Last offset  : ${lastoff:-unknown}"
  echo "RMS offset   : ${rmsoff:-unknown}"
  echo "Frequency    : ${freq:-unknown}"
  echo "Skew         : ${skew:-unknown}"
  echo "Leap status  : ${leap:-unknown}"
else
  red "Unable to read chronyc tracking"
  fail=1
fi
echo

echo "[ PPS SOURCE DETAIL ]"
grep -Ei 'refclock|pps' /etc/chrony/chrony.conf 2>/dev/null || true
echo

echo "[ GNSS / DATA INPUT DETAIL ]"
echo "Configured operating note:"
echo "  Piksi PPS feeds Raspberry Pi and Teensy"
echo "  Piksi Ethernet feeds Raspberry Pi and Teensy"
echo "  Teensy is analytics-only at this stage"
echo "Available tty devices of interest:"
ls -l /dev/tty* 2>/dev/null | grep -E 'USB|ACM' || true
echo

echo "[ PPS DEVICES ]"
pps_list="$(ls /dev/pps* 2>/dev/null || true)"
if [ -n "$pps_list" ]; then
  green "PPS device(s): $(echo "$pps_list" | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
else
  red "No PPS devices found"
  fail=1
fi
echo

echo "[ TIMING QUALITY ]"
if [ -f /home/pi/timing/teensy_logger.out ]; then
  last_phase_line="$(grep 'phase=' /home/pi/timing/teensy_logger.out 2>/dev/null | tail -n 1 || true)"
  if [ -n "$last_phase_line" ]; then
    echo "Latest logger line:"
    echo "$last_phase_line"
  else
    yellow "No phase lines found in teensy_logger.out"
  fi
else
  yellow "Missing /home/pi/timing/teensy_logger.out"
fi

if [ -f /home/pi/timing/aggregate.log ]; then
  agg_age=$(( $(date +%s) - $(stat -c %Y /home/pi/timing/aggregate.log) ))
  echo "aggregate.log age : ${agg_age}s"
fi

if [ -f /home/pi/timing/plot.log ]; then
  plot_age=$(( $(date +%s) - $(stat -c %Y /home/pi/timing/plot.log) ))
  echo "plot.log age      : ${plot_age}s"
fi

if [ -f /home/pi/timing/piksi_monitor.log ]; then
  piksi_age=$(( $(date +%s) - $(stat -c %Y /home/pi/timing/piksi_monitor.log) ))
  echo "piksi_monitor age : ${piksi_age}s"
fi
echo

echo "[ DATABASE ]"
check_sqlite_db() {
  local db="$1"
  [ -f "$db" ] || return 0

  local size mtime age integrity tables rows
  size=$(du -h "$db" | cut -f1)
  mtime=$(date -r "$db" "+%Y-%m-%d %H:%M:%S")
  age=$(( $(date +%s) - $(stat -c %Y "$db") ))

  if [ "$age" -lt 300 ]; then
    green "$(basename "$db") ($size, updated ${age}s ago)"
  else
    yellow "$(basename "$db") ($size, updated ${age}s ago)"
  fi
  echo "  Path         : $db"
  echo "  Last updated : $mtime"

  if command -v sqlite3 >/dev/null 2>&1; then
    integrity=$(sqlite3 "$db" "PRAGMA integrity_check;" 2>/dev/null | head -n 1)
    if [ "$integrity" = "ok" ]; then
      echo "  Integrity    : OK"
    elif [ -n "$integrity" ]; then
      echo "  Integrity    : $integrity"
      fail=1
    else
      echo "  Integrity    : unable to check"
    fi

    tables=$(sqlite3 "$db" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" 2>/dev/null | tr '\n' ' ')
    echo "  Tables       : ${tables:-none}"

    for tbl in timing_samples timing_10min telemetry pps_stats measurements phase_data; do
      if sqlite3 "$db" "SELECT 1 FROM sqlite_master WHERE type='table' AND name='$tbl';" 2>/dev/null | grep -q 1; then
        rows=$(sqlite3 "$db" "SELECT COUNT(*) FROM \"$tbl\";" 2>/dev/null)
        echo "  Row count [$tbl] : $rows"
      fi
    done
  else
    echo "  sqlite3 not installed; skipping integrity and row counts"
  fi
  echo
}

for db in \
  /home/pi/timing/timing.db \
  /home/pi/teensy_appliance/teensy_stats.db \
  /mnt/*/*.db \
  /mnt/*/*/*.db
do
  check_sqlite_db "$db"
done

echo "[ CRON ]"
crontab -l 2>/dev/null || yellow "No crontab for pi"
echo

echo "[ KNOWN ISSUES ]"
echo "- Occasional SQLite 'database is locked (5)' during report generation; email still succeeds"
echo "- teensy_logger.out may show an older last phase line even while timing.db is still updating"
echo

echo "[ WORKFLOW ]"
echo "Refresh snapshot locally:"
echo "  ~/time-server/rebuild/dump_state.sh > ~/time-server/STATE_SNAPSHOT.txt"
echo
echo "Commit and push with fresh snapshot:"
echo "  ~/time-server/rebuild/commit_with_snapshot.sh \"commit message\""
echo
echo "Full rebuild path:"
echo "  ~/time-server/rebuild/rebuild_all.sh"
echo

echo "[ GIT ]"
cd ~/time-server 2>/dev/null || exit 1
git log --oneline -n 5 || true
git status --short || true
echo

echo "[ REPOSITORY TREE ]"
tree -L 3 ~/time-server 2>/dev/null || find ~/time-server -maxdepth 3 | sort
echo

echo "===================================================="
if [ "$fail" -eq 0 ]; then
  green "OVERALL: PASS"
else
  red "OVERALL: FAIL"
fi
echo "===================================================="
