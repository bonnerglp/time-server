#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${HOME}/time-server/chat_exports"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/chat_context_${TS}.txt"

mkdir -p "${OUT_DIR}"

section () {
  echo
  echo "==================== $1 ===================="
}

append_file () {
  local title="$1"
  local path="$2"
  section "$title"
  if [ -f "$path" ]; then
    cat "$path"
  else
    echo "Missing: $path"
  fi
}

append_tail () {
  local title="$1"
  local path="$2"
  local lines="${3:-80}"
  section "$title"
  if [ -f "$path" ]; then
    tail -n "$lines" "$path"
  else
    echo "Missing: $path"
  fi
}

append_ls_if_exists () {
  local title="$1"
  shift
  section "$title"
  local found=0
  for p in "$@"; do
    if [ -e "$p" ]; then
      found=1
      ls -lh "$p"
    fi
  done
  if [ "$found" -eq 0 ]; then
    echo "No matching files found"
  fi
}

{
  echo "==================== CHAT CONTEXT EXPORT ===================="
  echo "Generated local: $(date)"
  echo "Generated UTC:   $(date -u)"
  echo "Host: $(hostname)"
  echo

  section "HOW TO USE THIS EXPORT"
  cat <<'EOF'
Paste this file into a new chat when you want precise edits to the live system.
It includes:
- current snapshot
- live dashboard/collector code
- ZED bridge sender
- latest DB state
- sample live telemetry
- report summaries
- plot file inventory

If the new chat is about Teensy firmware, also paste the current Teensy sketch separately.
EOF

  # Refresh snapshot first
  if [ -x ~/time-server/rebuild/dump_state.sh ]; then
    ~/time-server/rebuild/dump_state.sh > ~/time-server/system_config/STATE_SNAPSHOT.txt || true
  fi

  append_file "STATE SNAPSHOT" ~/time-server/system_config/STATE_SNAPSHOT.txt

  append_file "LIVE DASHBOARD BACKEND (~/teensy_dash2/app.py)" ~/teensy_dash2/app.py
  append_file "LIVE DASHBOARD FRONTEND (~/teensy_dash2/static/app.js)" ~/teensy_dash2/static/app.js
  append_file "LIVE DASHBOARD TEMPLATE (~/teensy_dash2/templates/index.html)" ~/teensy_dash2/templates/index.html
  append_file "LIVE COLLECTOR (~/teensy_appliance/collector.py)" ~/teensy_appliance/collector.py
  append_file "ZED TO TEENSY BRIDGE (~/time-server/pi/send_zed_to_teensy.py)" ~/time-server/pi/send_zed_to_teensy.py

  section "LATEST DB STATE (latest_state)"
  python3 - <<'PY'
import os, sqlite3, json
db = os.path.expanduser("~/teensy_appliance/teensy_stats.db")
if not os.path.exists(db):
    print("Database not found:", db)
else:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM latest_state WHERE singleton_id=1").fetchone()
    if row:
        d = dict(row)
        print(json.dumps(d, indent=2, default=str))
    else:
        print("No latest_state row found")
    conn.close()
PY

  section "LATEST ZED STATUS JSON"
  if [ -f /home/pi/timing/zed_status.json ]; then
    python3 - <<'PY'
import json
with open("/home/pi/timing/zed_status.json","r",encoding="utf-8") as f:
    d = json.load(f)
print(json.dumps(d, indent=2, default=str))
PY
  else
    echo "Missing: /home/pi/timing/zed_status.json"
  fi

  section "SAMPLE LIVE TELEMETRY (up to 5 lines)"
  timeout 3 nc 10.0.0.116 2323 2>/dev/null | head -n 5 || echo "No live telemetry captured"

  append_tail "REPORT SUMMARY TXT (tail)" /home/pi/timing/report_summary.txt 120
  append_tail "LATEST SNAPSHOT TXT (tail)" /home/pi/timing/latest_snapshot.txt 120

  section "LATEST STATS SUMMARY FROM DB"
  python3 - <<'PY'
import os, sqlite3, math
db = os.path.expanduser("~/teensy_appliance/teensy_stats.db")
if not os.path.exists(db):
    print("Database not found:", db)
    raise SystemExit

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT timestamp_utc, err_ns, sats, sats_visible, pdop, cn0_avg,
           piksi_minus_zed_ns, piksi_minus_zed_rms_ns, fix_type
    FROM samples
    ORDER BY id DESC
    LIMIT 600
""").fetchall()
conn.close()

rows = list(reversed(rows))
print(f"rows_loaded={len(rows)}")

def vals(key):
    out = []
    for r in rows:
        v = r[key]
        if v is None:
            continue
        try:
            out.append(float(v))
        except Exception:
            pass
    return out

def summary(name, xs):
    if not xs:
        print(f"{name}: no data")
        return
    mean = sum(xs) / len(xs)
    mn = min(xs)
    mx = max(xs)
    print(f"{name}: n={len(xs)} mean={mean:.3f} min={mn:.3f} max={mx:.3f}")

summary("err_ns", vals("err_ns"))
summary("sats", vals("sats"))
summary("sats_visible", vals("sats_visible"))
summary("pdop", vals("pdop"))
summary("cn0_avg", vals("cn0_avg"))
summary("piksi_minus_zed_ns", vals("piksi_minus_zed_ns"))
summary("piksi_minus_zed_rms_ns", vals("piksi_minus_zed_rms_ns"))

fixes = {}
for r in rows:
    fx = r["fix_type"]
    if not fx:
        continue
    fixes[fx] = fixes.get(fx, 0) + 1
print("fix_type_counts:", fixes)
PY

  append_ls_if_exists "TIMING PLOTS INVENTORY" \
    /home/pi/timing/*.png

  section "KEY PLOT PATHS"
  cat <<'EOF'
These files are often useful to attach or mention in a new chat:
- /home/pi/timing/allan_true_tau.png
- /home/pi/timing/timing_7d.png
- /home/pi/timing/timing_30d.png
- /home/pi/timing/timing_90d.png
- /home/pi/timing/jitter10m_1d.png
- /home/pi/timing/jitter10m_7d.png
- /home/pi/timing/jitter10m_30d.png
- /home/pi/timing/jitter10m_90d.png
- /home/pi/timing/rms60_1d.png
- /home/pi/timing/rms60_7d.png
- /home/pi/timing/sats_pdop_1d.png
EOF

  section "SYSTEMD SERVICES OF INTEREST"
  systemctl --no-pager --full status \
    zed-monitor.service \
    zed-to-teensy.service \
    teensy-collector.service \
    teensy-dash2.service \
    chrony.service 2>/dev/null || true

  echo
  echo "==================== END CHAT CONTEXT ===================="
} | tee "${OUT_FILE}"

echo
echo "Saved export to: ${OUT_FILE}"
