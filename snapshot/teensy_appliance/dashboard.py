import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, Response

DB_PATH = os.path.expanduser("~/teensy_appliance/teensy_stats.db")
HTTP_PORT = 8080

app = Flask(__name__)


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row) if row else {}


@app.route("/api/latest")
def api_latest():
    conn = db_conn()
    row = conn.execute("SELECT * FROM latest_state WHERE singleton_id = 1").fetchone()
    conn.close()

    data = row_to_dict(row)
    ts = data.get("timestamp_utc")
    stale_sec = None
    is_live = False
    if ts:
        try:
            dt = datetime.fromisoformat(ts)
            stale_sec = (datetime.now(timezone.utc) - dt).total_seconds()
            is_live = stale_sec <= 5
        except Exception:
            pass
    data["stale_sec"] = stale_sec
    data["is_live"] = is_live
    return jsonify(data)


@app.route("/api/recent")
def api_recent():
    conn = db_conn()
    rows = conn.execute("""
        SELECT timestamp_utc, pps, state, pps_ok, tcp_ok, utc_ok, gps_ok, tracking,
               period_ns, err_ns, rms_ns, min_err_ns, max_err_ns,
               tcp_bytes, sbp_frames, crc_err,
               gps_week, gps_tow_ms, gps_ns_res,
               utc, utc_ns, utc_flags,
               sats, pdop, cn0_avg, fix_type,
               fe_mode, fe_control, fe_phase_ns, fe_holdover
        FROM samples
        ORDER BY id DESC
        LIMIT 800
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in reversed(rows)])


@app.route("/api/longterm")
def api_longterm():
    conn = db_conn()
    rows = conn.execute("""
        SELECT timestamp_utc, err_ns, rms_ns, period_ns, fe_phase_ns
        FROM samples
        WHERE id IN (
            SELECT id FROM samples ORDER BY id DESC LIMIT 30000
        )
        ORDER BY id ASC
    """).fetchall()
    conn.close()

    rows = [dict(r) for r in rows]
    if len(rows) > 1200:
        step = max(1, len(rows) // 1200)
        rows = rows[::step]
    return jsonify(rows)


def overlapping_adev(periods, m):
    if len(periods) < 2 * m + 1:
        return None
    y = [((p - 1_000_000_000.0) / 1_000_000_000.0) for p in periods]
    block = []
    for i in range(0, len(y) - m + 1):
        block.append(sum(y[i:i + m]) / m)
    if len(block) < 2:
        return None
    diffs2 = []
    for i in range(len(block) - 1):
        d = block[i + 1] - block[i]
        diffs2.append(d * d)
    if not diffs2:
        return None
    return (0.5 * (sum(diffs2) / len(diffs2))) ** 0.5


@app.route("/api/adev")
def api_adev():
    conn = db_conn()
    rows = conn.execute("""
        SELECT period_ns FROM samples
        WHERE period_ns IS NOT NULL
        ORDER BY id DESC
        LIMIT 10000
    """).fetchall()
    conn.close()

    periods = [float(r["period_ns"]) for r in reversed(rows)]
    taus = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    adev = [overlapping_adev(periods, t) for t in taus]
    return jsonify({"taus": taus, "adev": adev})


@app.route("/api/histogram")
def api_histogram():
    conn = db_conn()
    rows = conn.execute("""
        SELECT err_ns FROM samples
        WHERE err_ns IS NOT NULL
        ORDER BY id DESC
        LIMIT 3000
    """).fetchall()
    conn.close()

    vals = [float(r["err_ns"]) for r in rows]
    if not vals:
        return jsonify({"bins": [], "counts": []})

    vmin = min(vals)
    vmax = max(vals)
    if vmin == vmax:
        return jsonify({"bins": [vmin], "counts": [len(vals)]})

    bins_n = 30
    width = (vmax - vmin) / bins_n
    bins = [vmin + i * width for i in range(bins_n)]
    counts = [0] * bins_n

    for v in vals:
        idx = int((v - vmin) / width)
        if idx >= bins_n:
            idx = bins_n - 1
        counts[idx] += 1

    return jsonify({"bins": bins, "counts": counts})


@app.route("/")
def index():
    return Response("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Teensy Timing Appliance</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
  --bg: #f5f7fb;
  --card: #ffffff;
  --text: #111827;
  --muted: #6b7280;
  --border: #e5e7eb;
  --ok: #15803d;
  --bad: #b91c1c;
  --warn: #b45309;
}
body {
  font-family: Arial, sans-serif;
  margin: 0;
  background: var(--bg);
  color: var(--text);
}
.header {
  padding: 18px 20px 12px 20px;
  background: white;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}
h1 {
  margin: 0 0 10px 0;
  font-size: 34px;
}
.statusbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.pill {
  border-radius: 999px;
  padding: 8px 14px;
  font-weight: bold;
  font-size: 14px;
  background: #eef2ff;
}
.pill.ok { background: #dcfce7; color: var(--ok); }
.pill.bad { background: #fee2e2; color: var(--bad); }
.pill.warn { background: #fef3c7; color: var(--warn); }

.container {
  padding: 18px 20px 30px 20px;
}
.sectiontitle {
  margin: 8px 0 12px 0;
  font-size: 24px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.card {
  background: var(--card);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.07);
}
.label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: .04em;
}
.value {
  font-size: 24px;
  font-weight: 700;
}
.value.small {
  font-size: 18px;
}
.value.ok { color: var(--ok); }
.value.bad { color: var(--bad); }
.value.warn { color: var(--warn); }
.mono {
  font-family: Consolas, monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}
canvas {
  background: white;
  border-radius: 14px;
  padding: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,.07);
  margin-bottom: 16px;
}
</style>
</head>
<body>
  <div class="header">
    <h1>Teensy Timing Appliance</h1>
    <div class="statusbar">
      <div id="livePill" class="pill">Telemetry —</div>
      <div id="statePill" class="pill">State —</div>
      <div id="trackingPill" class="pill">Tracking —</div>
      <div id="agePill" class="pill">Age —</div>
    </div>
  </div>

  <div class="container">
    <div class="sectiontitle">Status</div>
    <div class="grid">
      <div class="card"><div class="label">State</div><div class="value" id="state">—</div></div>
      <div class="card"><div class="label">Tracking</div><div class="value" id="tracking">—</div></div>
      <div class="card"><div class="label">PPS OK</div><div class="value" id="pps_ok">—</div></div>
      <div class="card"><div class="label">TCP OK</div><div class="value" id="tcp_ok">—</div></div>
      <div class="card"><div class="label">UTC OK</div><div class="value" id="utc_ok">—</div></div>
      <div class="card"><div class="label">GPS OK</div><div class="value" id="gps_ok">—</div></div>
      <div class="card"><div class="label">PPS Count</div><div class="value" id="pps">—</div></div>
      <div class="card"><div class="label">Age</div><div class="value" id="stale_sec">—</div></div>
    </div>

    <div class="sectiontitle">Timing</div>
    <div class="grid">
      <div class="card"><div class="label">Latest Error</div><div class="value" id="err_ns">—</div></div>
      <div class="card"><div class="label">RMS Jitter</div><div class="value" id="rms_ns">—</div></div>
      <div class="card"><div class="label">Period</div><div class="value" id="period_ns">—</div></div>
      <div class="card"><div class="label">Min Error</div><div class="value" id="min_err_ns">—</div></div>
      <div class="card"><div class="label">Max Error</div><div class="value" id="max_err_ns">—</div></div>
      <div class="card"><div class="label">Drift</div><div class="value" id="drift_ppm">—</div></div>
    </div>

    <div class="sectiontitle">Receiver / Transport</div>
    <div class="grid">
      <div class="card"><div class="label">TCP Bytes</div><div class="value" id="tcp_bytes">—</div></div>
      <div class="card"><div class="label">SBP Frames</div><div class="value" id="sbp_frames">—</div></div>
      <div class="card"><div class="label">CRC Errors</div><div class="value" id="crc_err">—</div></div>
      <div class="card"><div class="label">GPS Week</div><div class="value" id="gps_week">—</div></div>
      <div class="card"><div class="label">GPS TOW ms</div><div class="value" id="gps_tow_ms">—</div></div>
      <div class="card"><div class="label">GPS ns residual</div><div class="value" id="gps_ns_res">—</div></div>
      <div class="card"><div class="label">UTC Flags</div><div class="value" id="utc_flags">—</div></div>
      <div class="card"><div class="label">UTC</div><div class="value small" id="utc">—</div></div>
    </div>

    <div class="sectiontitle">GNSS Quality</div>
    <div class="grid">
      <div class="card"><div class="label">Satellites</div><div class="value" id="sats">—</div></div>
      <div class="card"><div class="label">PDOP</div><div class="value" id="pdop">—</div></div>
      <div class="card"><div class="label">Avg C/N0</div><div class="value" id="cn0_avg">—</div></div>
      <div class="card"><div class="label">Fix Type</div><div class="value" id="fix_type">—</div></div>
    </div>

    <div class="sectiontitle">FE-5680A / Discipline</div>
    <div class="grid">
      <div class="card"><div class="label">FE Mode</div><div class="value" id="fe_mode">—</div></div>
      <div class="card"><div class="label">FE Control</div><div class="value" id="fe_control">—</div></div>
      <div class="card"><div class="label">FE Phase</div><div class="value" id="fe_phase_ns">—</div></div>
      <div class="card"><div class="label">Holdover</div><div class="value" id="fe_holdover">—</div></div>
      <div class="card"><div class="label">Last Update</div><div class="value small" id="timestamp_utc">—</div></div>
    </div>

    <div class="sectiontitle">Short-Term Timing</div>
    <canvas id="errChart" height="110"></canvas>
    <canvas id="rmsChart" height="110"></canvas>
    <canvas id="periodChart" height="110"></canvas>

    <div class="sectiontitle">Drift / FE</div>
    <canvas id="driftChart" height="110"></canvas>
    <canvas id="feChart" height="110"></canvas>

    <div class="sectiontitle">Error Histogram</div>
    <canvas id="histChart" height="110"></canvas>

    <div class="sectiontitle">Allan Deviation</div>
    <canvas id="adevChart" height="110"></canvas>

    <div class="sectiontitle">Long-Term Stability</div>
    <canvas id="longErrChart" height="110"></canvas>
    <canvas id="longRmsChart" height="110"></canvas>
  </div>

<script>
let errChart, rmsChart, periodChart, driftChart, feChart, histChart, adevChart, longErrChart, longRmsChart;

function mkChart(id, label, yLabel) {
  return new Chart(document.getElementById(id), {
    type: "line",
    data: { labels: [], datasets: [{ label, data: [], tension: 0.15 }] },
    options: {
      animation: false,
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        x: { title: { display: true, text: "Sample" } },
        y: { title: { display: true, text: yLabel } }
      }
    }
  });
}

function mkBar(id, label, yLabel) {
  return new Chart(document.getElementById(id), {
    type: "bar",
    data: { labels: [], datasets: [{ label, data: [] }] },
    options: {
      animation: false,
      responsive: true,
      scales: {
        x: { title: { display: true, text: "Error Bin (ns)" } },
        y: { title: { display: true, text: yLabel } }
      }
    }
  });
}

function mkLogChart(id, label, yLabel) {
  return new Chart(document.getElementById(id), {
    type: "line",
    data: { datasets: [{ label, data: [], tension: 0.15 }] },
    options: {
      animation: false,
      responsive: true,
      scales: {
        x: { type: "logarithmic", title: { display: true, text: "Tau (s)" } },
        y: { type: "logarithmic", title: { display: true, text: yLabel } }
      }
    }
  });
}

function initCharts() {
  errChart = mkChart("errChart", "Error (ns)", "ns");
  rmsChart = mkChart("rmsChart", "RMS Jitter (ns)", "ns");
  periodChart = mkChart("periodChart", "Period (ns)", "ns");
  driftChart = mkChart("driftChart", "Drift (ppm)", "ppm");
  feChart = mkChart("feChart", "FE Phase Error (ns)", "ns");
  histChart = mkBar("histChart", "Error Histogram", "Count");
  adevChart = mkLogChart("adevChart", "ADEV", "ADEV");
  longErrChart = mkChart("longErrChart", "Long Error (ns)", "ns");
  longRmsChart = mkChart("longRmsChart", "Long RMS (ns)", "ns");
}

function setText(id, value, suffix="") {
  const el = document.getElementById(id);
  el.textContent = (value === null || value === undefined || value === "") ? "—" : `${value}${suffix}`;
}

function setBoolTile(id, value) {
  const el = document.getElementById(id);
  const ok = Number(value) ? true : false;
  el.textContent = ok ? "OK" : "NO";
  el.className = "value " + (ok ? "ok" : "bad");
}

async function refreshLatest() {
  const d = await fetch("/api/latest").then(r => r.json());

  const livePill = document.getElementById("livePill");
  livePill.textContent = d.is_live ? "Telemetry LIVE" : "Telemetry STALE";
  livePill.className = "pill " + (d.is_live ? "ok" : "bad");

  const statePill = document.getElementById("statePill");
  statePill.textContent = "State " + (d.state ?? "—");
  statePill.className = "pill";

  const trackingPill = document.getElementById("trackingPill");
  trackingPill.textContent = Number(d.tracking) ? "Tracking YES" : "Tracking NO";
  trackingPill.className = "pill " + (Number(d.tracking) ? "ok" : "warn");

  const agePill = document.getElementById("agePill");
  agePill.textContent = "Age " + (d.stale_sec == null ? "—" : Number(d.stale_sec).toFixed(1) + " s");
  agePill.className = "pill";

  setText("state", d.state);
  setText("tracking", Number(d.tracking) ? "YES" : "NO");
  setBoolTile("pps_ok", d.pps_ok);
  setBoolTile("tcp_ok", d.tcp_ok);
  setBoolTile("utc_ok", d.utc_ok);
  setBoolTile("gps_ok", d.gps_ok);

  setText("stale_sec", d.stale_sec == null ? "—" : Number(d.stale_sec).toFixed(1), " s");

  setText("pps", d.pps);
  setText("err_ns", d.err_ns, " ns");
  setText("rms_ns", d.rms_ns, " ns");
  setText("period_ns", d.period_ns, " ns");
  setText("min_err_ns", d.min_err_ns, " ns");
  setText("max_err_ns", d.max_err_ns, " ns");

  let drift = "—";
  if (d.period_ns !== null && d.period_ns !== undefined) {
    drift = (((Number(d.period_ns) - 1000000000.0) / 1000000000.0) * 1e6).toFixed(3);
  }
  setText("drift_ppm", drift, " ppm");

  setText("tcp_bytes", d.tcp_bytes);
  setText("sbp_frames", d.sbp_frames);
  setText("crc_err", d.crc_err);
  setText("gps_week", d.gps_week);
  setText("gps_tow_ms", d.gps_tow_ms);
  setText("gps_ns_res", d.gps_ns_res);
  setText("utc_flags", d.utc_flags);

  setText("sats", d.sats);
  setText("pdop", d.pdop);
  setText("cn0_avg", d.cn0_avg);
  setText("fix_type", d.fix_type);

  setText("fe_mode", d.fe_mode);
  setText("fe_control", d.fe_control);
  setText("fe_phase_ns", d.fe_phase_ns, " ns");
  setText("fe_holdover", d.fe_holdover);

  setText("utc", d.utc);
  setText("timestamp_utc", d.timestamp_utc);
}

async function refreshRecent() {
  const rows = await fetch("/api/recent").then(r => r.json());
  const labels = rows.map((_, i) => i + 1);
  const err = rows.map(r => r.err_ns);
  const rms = rows.map(r => r.rms_ns);
  const period = rows.map(r => r.period_ns);
  const fe = rows.map(r => r.fe_phase_ns);
  const ppm = rows.map(r => r.period_ns == null ? null : ((Number(r.period_ns) - 1000000000.0) / 1000000000.0) * 1e6);

  errChart.data.labels = labels; errChart.data.datasets[0].data = err; errChart.update();
  rmsChart.data.labels = labels; rmsChart.data.datasets[0].data = rms; rmsChart.update();
  periodChart.data.labels = labels; periodChart.data.datasets[0].data = period; periodChart.update();
  driftChart.data.labels = labels; driftChart.data.datasets[0].data = ppm; driftChart.update();
  feChart.data.labels = labels; feChart.data.datasets[0].data = fe; feChart.update();
}

async function refreshHistogram() {
  const d = await fetch("/api/histogram").then(r => r.json());
  histChart.data.labels = d.bins.map(x => Number(x).toFixed(1));
  histChart.data.datasets[0].data = d.counts;
  histChart.update();
}

async function refreshAdev() {
  const d = await fetch("/api/adev").then(r => r.json());
  const pairs = d.taus.map((t, i) => ({x: t, y: d.adev[i]})).filter(p => p.y !== null);
  adevChart.data.datasets[0].data = pairs;
  adevChart.update();
}

async function refreshLongterm() {
  const rows = await fetch("/api/longterm").then(r => r.json());
  const labels = rows.map(r => r.timestamp_utc ? r.timestamp_utc.slice(11, 19) : "");
  const err = rows.map(r => r.err_ns);
  const rms = rows.map(r => r.rms_ns);

  longErrChart.data.labels = labels;
  longErrChart.data.datasets[0].data = err;
  longErrChart.update();

  longRmsChart.data.labels = labels;
  longRmsChart.data.datasets[0].data = rms;
  longRmsChart.update();
}

async function tick() {
  try {
    await refreshLatest();
    await refreshRecent();
    await refreshHistogram();
    await refreshAdev();
    await refreshLongterm();
  } catch (e) {
    console.error(e);
  }
}

initCharts();
tick();
setInterval(tick, 2000);
</script>
</body>
</html>
""", mimetype="text/html")


def main():
    print(f"Dashboard on 0.0.0.0:{HTTP_PORT}")
    app.run(host="0.0.0.0", port=HTTP_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
