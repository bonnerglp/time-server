#!/bin/bash
VERSION_FILE="/home/pi/time-server/VERSION.txt"
REPO_VERSION="$(cat "$VERSION_FILE" 2>/dev/null || echo unknown)"
set -euo pipefail

BASE_DIR="/home/pi/timing"
DB="$BASE_DIR/timing.db"
TEXT_BODY="/tmp/timing_report_body.txt"
HTML_BODY="/tmp/timing_report_body.html"
SUMMARY_FILE="/tmp/timing_summary.txt"
LATEST_FILE="/tmp/timing_latest.txt"
PIKSI_EVENTS_FILE="/tmp/piksi_events.txt"
CHRONY_TRACKING_FILE="/tmp/chrony_tracking.txt"
CHRONY_SOURCES_FILE="/tmp/chrony_sources.txt"
QUALITY24_FILE="/tmp/timing_quality_24h.txt"

python3 "$BASE_DIR/aggregate_10min.py" || true
python3 "$BASE_DIR/plot_timing_report.py"

chronyc tracking > "$CHRONY_TRACKING_FILE" 2>/dev/null || echo "chronyc tracking failed" > "$CHRONY_TRACKING_FILE"
chronyc sources -v > "$CHRONY_SOURCES_FILE" 2>/dev/null || echo "chronyc sources failed" > "$CHRONY_SOURCES_FILE"

sqlite3 -separator '|' "$DB" "
SELECT
  bucket_start,
  ROUND(avg_phase_ns,1),
  ROUND(rms_phase_ns,1),
  ROUND(avg_rms60_ns,1),
  printf('%.3e', avg_adev_1s),
  ROUND(avg_sats,1),
  ROUND(avg_pdop,2),
  samples
FROM timing_10min
ORDER BY bucket_start DESC
LIMIT 12;
" > "$SUMMARY_FILE"

sqlite3 -separator '|' "$DB" "
SELECT
  timestamp,
  state,
  ROUND(current_phase_err_ns,1),
  ROUND(rms_60s_ns,1),
  ROUND(rms_10m_ns,1),
  ROUND(p2p_60s_ns,1),
  printf('%.3e', adev_1s),
  sats,
  ROUND(pdop,2),
  ROUND(cn0_avg,1),
  ROUND(gps_ns_res,1),
  ROUND(period_ns,1),
  fe_holdover,
  tcp_ok,
  gps_ok,
  pps_ok
FROM teensy_telemetry
ORDER BY timestamp DESC
LIMIT 1;
" > "$LATEST_FILE"

sqlite3 -separator '|' "$DB" "
SELECT
  event_time,
  event_type,
  detail
FROM piksi_events
WHERE event_time >= datetime('now','-1 day')
ORDER BY event_time DESC
LIMIT 20;
" > "$PIKSI_EVENTS_FILE" || true

python3 - <<'PY' > "$QUALITY24_FILE"
import sqlite3
import statistics
import math

db = "/home/pi/timing/timing.db"
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("""
SELECT avg_phase_ns
FROM timing_10min
WHERE bucket_start >= datetime('now','-1 day')
  AND avg_phase_ns IS NOT NULL
ORDER BY bucket_start
""")
vals = [float(r[0]) for r in cur.fetchall()]
conn.close()

if not vals:
    print("N/A|N/A|N/A|N/A|N/A")
else:
    mean_v = statistics.fmean(vals)
    std_v = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    min_v = min(vals)
    max_v = max(vals)
    p2p_v = max_v - min_v
    print(f"{mean_v:.1f}|{std_v:.1f}|{p2p_v:.1f}|{min_v:.1f}|{max_v:.1f}")
PY

IFS='|' read -r CUR_TS CUR_STATE CUR_PHASE CUR_RMS60 CUR_RMS10 CUR_P2P60 CUR_ADEV CUR_SATS CUR_PDOP CUR_CN0 CUR_GPSRES CUR_PERIOD CUR_HOLDOVER CUR_TCP_OK CUR_GPS_OK CUR_PPS_OK < "$LATEST_FILE"
IFS='|' read -r MEAN24 STD24 P2P24 MIN24 MAX24 < "$QUALITY24_FILE"

cat > "$TEXT_BODY" <<TXT
GNSS TIMING REPORT
System version: ${REPO_VERSION}
Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')

Timing Quality Summary (Last 24 Hours)
  Mean offset  : ${MEAN24:-N/A} ns
  Jitter (1σ)  : ${STD24:-N/A} ns
  Peak-to-peak : ${P2P24:-N/A} ns
  Min / Max    : ${MIN24:-N/A} ns / ${MAX24:-N/A} ns

Latest snapshot
  Time       : ${CUR_TS:-N/A}
  State      : ${CUR_STATE:-N/A}
  Phase      : ${CUR_PHASE:-N/A} ns
  RMS 60s    : ${CUR_RMS60:-N/A} ns
  RMS 10m    : ${CUR_RMS10:-N/A} ns
  P2P 60s    : ${CUR_P2P60:-N/A} ns
  ADEV 1s    : ${CUR_ADEV:-N/A}
  Satellites : ${CUR_SATS:-N/A}
  PDOP       : ${CUR_PDOP:-N/A}
  C/N0       : ${CUR_CN0:-N/A}
  GPS ns res : ${CUR_GPSRES:-N/A} ns
  PPS period : ${CUR_PERIOD:-N/A} ns
  Holdover   : ${CUR_HOLDOVER:-N/A}
  TCP OK     : ${CUR_TCP_OK:-N/A}
  GPS OK     : ${CUR_GPS_OK:-N/A}
  PPS OK     : ${CUR_PPS_OK:-N/A}

Recent 10-minute summary
TXT

cat "$SUMMARY_FILE" >> "$TEXT_BODY"

if [ -s "$PIKSI_EVENTS_FILE" ]; then
  {
    echo
    echo "Piksi events in last 24 hours"
    echo "-----------------------------"
    cat "$PIKSI_EVENTS_FILE"
  } >> "$TEXT_BODY"
fi

if [ -f "$CHRONY_TRACKING_FILE" ]; then
  {
    echo
    echo "Chrony / Time Sync Status"
    echo "------------------------"
    cat "$CHRONY_TRACKING_FILE"
    echo
    cat "$CHRONY_SOURCES_FILE"
  } >> "$TEXT_BODY"
fi

if [ -f "$BASE_DIR/report_summary.txt" ]; then
  {
    echo
    echo "Generated summary"
    echo "-----------------"
    cat "$BASE_DIR/report_summary.txt"
  } >> "$TEXT_BODY"
fi

python3 - <<'PY' > "$HTML_BODY"
import html
import os
from datetime import datetime, UTC

BASE_DIR = "/home/pi/timing"
SUMMARY_FILE = "/tmp/timing_summary.txt"
LATEST_FILE = "/tmp/timing_latest.txt"
PIKSI_EVENTS_FILE = "/tmp/piksi_events.txt"
CHRONY_TRACKING_FILE = "/tmp/chrony_tracking.txt"
CHRONY_SOURCES_FILE = "/tmp/chrony_sources.txt"
QUALITY24_FILE = "/tmp/timing_quality_24h.txt"

def read_file(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return default

def table_from_pipe(text, headers):
    rows = []
    for line in text.strip().splitlines():
        parts = line.split("|")
        rows.append(parts)
    if not rows:
        return "<p>No data.</p>"
    out = ["<table class='grid'><thead><tr>"]
    for h in headers:
        out.append(f"<th>{html.escape(h)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{html.escape(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)

def metric(label, value, cls=""):
    return f"<div class='metric'><div class='m-label'>{html.escape(label)}</div><div class='m-value {cls}'>{html.escape(str(value))}</div></div>"

summary_text = read_file(os.path.join(BASE_DIR, "report_summary.txt"), "No generated summary available.")
latest_text = read_file(os.path.join(BASE_DIR, "latest_snapshot.txt"), "No latest snapshot available.")
recent_text = read_file(SUMMARY_FILE, "")
piksi_text = read_file(PIKSI_EVENTS_FILE, "No Piksi events in last 24 hours.")
chrony_tracking = read_file(CHRONY_TRACKING_FILE, "No chrony tracking data.")
chrony_sources = read_file(CHRONY_SOURCES_FILE, "No chrony sources data.")
quality24_text = read_file(QUALITY24_FILE, "N/A|N/A|N/A|N/A|N/A").strip()

quality_parts = quality24_text.split("|")
while len(quality_parts) < 5:
    quality_parts.append("N/A")
mean24, std24, p2p24, min24, max24 = quality_parts[:5]

latest_lines = latest_text.splitlines()
latest_map = {}
for line in latest_lines:
    if ":" in line:
        k, v = line.split(":", 1)
        latest_map[k.strip()] = v.strip()

state = latest_map.get("State", "N/A")
tcp_ok = latest_map.get("TCP OK", "N/A")
gps_ok = latest_map.get("GPS OK", "N/A")
pps_ok = latest_map.get("PPS OK", "N/A")

def okcls(v):
    return "ok" if str(v).strip() in {"1", "TRACKING", "Normal"} else "bad"

plot_sections = [
    ("Phase Error Distribution (Last 24 Hours)", "timing_hist_24h.png", "timing_hist_24h"),
    ("Average phase - 7 day", "timing_7d.png", "timing_7d"),
    ("Average phase - 30 day", "timing_30d.png", "timing_30d"),
    ("Average phase - 90 day", "timing_90d.png", "timing_90d"),
    ("10-minute RMS jitter - 1 day", "jitter10m_1d.png", "jitter10m_1d"),
    ("10-minute RMS jitter - 7 day", "jitter10m_7d.png", "jitter10m_7d"),
    ("10-minute RMS jitter - 30 day", "jitter10m_30d.png", "jitter10m_30d"),
    ("10-minute RMS jitter - 90 day", "jitter10m_90d.png", "jitter10m_90d"),
    ("RMS 60s - 1 day", "rms60_1d.png", "rms60_1d"),
    ("RMS 60s - 7 day", "rms60_7d.png", "rms60_7d"),
    ("Satellites and PDOP - 1 day", "sats_pdop_1d.png", "sats_pdop_1d"),
    ("True overlapping Allan deviation vs tau", "allan_true_tau.png", "allan_true_tau"),
]

recent_table = table_from_pipe(
    recent_text,
    ["Bucket UTC", "Avg phase ns", "10m RMS jitter ns", "RMS60 ns", "ADEV 1s", "Sats", "PDOP", "Samples"]
)

plots_html = []
for title, fn, cid in plot_sections:
    path = os.path.join(BASE_DIR, fn)
    if os.path.exists(path):
        plots_html.append(f"<h3>{html.escape(title)}</h3><img src='cid:{cid}' alt='{html.escape(title)}'>")

html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>GNSS Timing Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; color: #222; background:#fff; }}
h1 {{ margin-bottom: 4px; }}
h2 {{ margin-top: 28px; border-bottom: 2px solid #ddd; padding-bottom: 6px; }}
h3 {{ margin-top: 24px; margin-bottom: 8px; }}
p.meta {{ color:#666; margin-top:0; }}
.metrics {{ display:flex; flex-wrap:wrap; gap:10px; margin:16px 0 22px 0; }}
.metric {{ border:1px solid #ddd; border-radius:10px; padding:10px 12px; min-width:150px; background:#fafafa; }}
.m-label {{ font-size:12px; color:#666; margin-bottom:6px; }}
.m-value {{ font-size:24px; font-weight:700; }}
.ok {{ color:#0a7a2f; }}
.bad {{ color:#b42318; }}
pre {{ background:#f6f6f6; padding:12px; border:1px solid #ddd; overflow-x:auto; white-space:pre-wrap; }}
table.grid {{ border-collapse:collapse; width:100%; font-size:14px; }}
table.grid th, table.grid td {{ border:1px solid #ddd; padding:6px 8px; text-align:left; }}
table.grid th {{ background:#f3f4f6; }}
img {{ max-width:1000px; width:100%; height:auto; display:block; margin:8px 0 22px 0; border:1px solid #ddd; }}
.section {{ margin-bottom:24px; }}
</style>
</head>
<body>
<h1>GNSS Timing Report</h1>
<p class="meta">Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>

<div class="metrics">
  {metric("State", state, okcls(state))}
  {metric("TCP OK", tcp_ok, okcls(tcp_ok))}
  {metric("GPS OK", gps_ok, okcls(gps_ok))}
  {metric("PPS OK", pps_ok, okcls(pps_ok))}
  {metric("Phase ns", latest_map.get("Current phase error", "N/A"))}
  {metric("RMS 60s ns", latest_map.get("RMS 60s", "N/A"))}
  {metric("RMS 10m ns", latest_map.get("RMS 10m", "N/A"))}
  {metric("ADEV 1s", latest_map.get("ADEV 1s", "N/A"))}
  {metric("Sats", latest_map.get("Satellites", "N/A"))}
  {metric("PDOP", latest_map.get("PDOP", "N/A"))}
</div>

<div class="section">
  <h2>Timing Quality Summary (Last 24 Hours)</h2>
  <div class="metrics">
    {metric("Mean offset", f"{mean24} ns")}
    {metric("Jitter (1σ)", f"{std24} ns")}
    {metric("Peak-to-peak", f"{p2p24} ns")}
    {metric("Min / Max", f"{min24} / {max24} ns")}
  </div>
</div>

<div class="section">
  <h2>Latest Snapshot</h2>
  <pre>{html.escape(latest_text)}</pre>
</div>

<div class="section">
  <h2>Recent 10-Minute Summary</h2>
  {recent_table}
</div>

<div class="section">
  <h2>Chrony / Time Sync Status</h2>
  <pre>{html.escape(chrony_tracking)}

{html.escape(chrony_sources)}</pre>
</div>

<div class="section">
  <h2>Piksi Events in Last 24 Hours</h2>
  <pre>{html.escape(piksi_text)}</pre>
</div>

<div class="section">
  <h2>Generated Summary</h2>
  <pre>{html.escape(summary_text)}</pre>
</div>

<div class="section">
  <h2>Plots</h2>
  {''.join(plots_html)}
</div>

</body>
</html>
"""
print(html_doc)
PY

python3 - <<'PY'
import os
import mimetypes
import datetime
from email.message import EmailMessage
import subprocess

TO="bonnerglp@gmail.com"
SUBJECT = "GNSS Timing Report - " + datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
TEXT_BODY = "/tmp/timing_report_body.txt"
HTML_BODY = "/tmp/timing_report_body.html"
BASE_DIR = "/home/pi/timing"

plot_sections = [
    ("timing_hist_24h.png", "timing_hist_24h"),
    ("timing_7d.png", "timing_7d"),
    ("timing_30d.png", "timing_30d"),
    ("timing_90d.png", "timing_90d"),
    ("jitter10m_1d.png", "jitter10m_1d"),
    ("jitter10m_7d.png", "jitter10m_7d"),
    ("jitter10m_30d.png", "jitter10m_30d"),
    ("jitter10m_90d.png", "jitter10m_90d"),
    ("rms60_1d.png", "rms60_1d"),
    ("rms60_7d.png", "rms60_7d"),
    ("sats_pdop_1d.png", "sats_pdop_1d"),
    ("allan_true_tau.png", "allan_true_tau"),
]

msg = EmailMessage()
msg["To"] = TO
msg["Subject"] = SUBJECT
msg["From"] = f"pi@{os.uname().nodename}"

with open(TEXT_BODY, "r", encoding="utf-8") as f:
    msg.set_content(f.read())

with open(HTML_BODY, "r", encoding="utf-8") as f:
    html_content = f.read()

msg.add_alternative(html_content, subtype="html")
html_part = msg.get_payload()[-1]

for filename, cid in plot_sections:
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        continue
    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with open(path, "rb") as fp:
        html_part.add_related(
            fp.read(),
            maintype=maintype,
            subtype=subtype,
            cid=f"<{cid}>",
            filename=filename,
            disposition="inline"
        )

subprocess.run(["/usr/sbin/sendmail", "-t", "-oi"], input=msg.as_bytes(), check=True)
print("Email sent successfully")
PY

echo "Timing report email sent"
