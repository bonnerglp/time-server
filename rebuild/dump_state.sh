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
echo "Primary active timing source: ZED-F9T PPS into Raspberry Pi / chrony"
echo "PPS fanout: ZED-F9T PPS -> Raspberry Pi and Teensy"
echo "Ethernet/data fanout: ZED-F9T USB -> zed-splitter -> gpsd-direct and ser2net"
echo "Teensy role: analytics / telemetry / measurement only"
echo "Teensy timing role: not yet disciplining Raspberry Pi"
echo "FE-5680A role: not yet integrated into active timing chain"
echo

echo "[ HARDWARE / SIGNAL CHAIN ]"
echo "Primary host:"
echo "  Raspberry Pi time server"
echo
echo "Current active timing chain:"
echo "  ZED-F9T PPS -> Raspberry Pi PPS input -> chrony -> NTP service"
echo
echo "Current PPS distribution:"
echo "  ZED-F9T PPS -> Raspberry Pi"
echo "  ZED-F9T PPS -> Teensy"
echo
echo "Current Ethernet / data distribution:"
echo "  ZED-F9T USB -> Raspberry Pi"
echo "  zed-splitter -> gpsd-direct"
echo "  zed-splitter -> ser2net"
echo "  ser2net -> remote u-center monitoring"
echo
echo "Current analytics chain:"
echo "  Teensy -> UDP telemetry collector -> logger -> dashboard"
echo
echo "Current active software components:"
echo "  chrony"
echo "  zed-splitter.service"
echo "  gpsd-direct.service"
echo "  ser2net.service"
echo "  teensy-collector.service"
echo "  teensy-dash2.service"
echo "  teensy_logger.service"
echo
echo "Planned / known project hardware:"
echo "  ZED-F9T in current active chain"
echo "  Teensy 4.1 for analytics / measurement / future discipline work"
echo "  Piksi retained as optional comparison / reference source"
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
for svc in chrony.service zed-splitter.service gpsd-direct.service ser2net.service teensy-collector.service teensy-dash2.service teensy_logger.service; do
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
echo "  ZED-F9T PPS feeds Raspberry Pi and Teensy"
echo "  ZED-F9T USB feeds Raspberry Pi"
echo "  zed-splitter provides shared read access to gpsd-direct and ser2net"
echo "  Direct USB is used for configuration writes; TCP is for monitoring only"
echo "Available tty devices of interest:"
ls -l /dev/ttyACM* 2>/dev/null || true
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

echo

echo "[ DATABASE ]"
check_sqlite_db() {
  local db="$1"
  [ -f "$db" ] || return 0

  local size mtime age
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
  echo
}

for db in \
  /home/pi/timing/timing.db \
  /home/pi/teensy_appliance/teensy_stats.db
do
  check_sqlite_db "$db"
done

echo "[ WORKFLOW ]"
echo "Refresh snapshot locally:"
echo "  ~/time-server/rebuild/dump_state.sh > ~/time-server/system_config/STATE_SNAPSHOT.txt"
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

echo "===================================================="
if [ "$fail" -eq 0 ]; then
  green "OVERALL: PASS"
else
  red "OVERALL: FAIL"
fi
echo "===================================================="
