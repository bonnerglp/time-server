from pathlib import Path
import sys

REPO_ROOT = "/home/pi/time-server"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pi.utils.version import get_version
REPO_VERSION = get_version()

# VERSION_HELPER_AVAILABLE
import math
import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template

DB_PATH = "/home/pi/teensy_appliance/teensy_stats.db"
HTTP_PORT = int(os.environ.get("DASHBOARD_PORT", "8082"))

app = Flask(__name__)

@app.context_processor
def inject_repo_version():
    return {"repo_version": REPO_VERSION}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def now_utc():
    return datetime.now(timezone.utc)

def latest_packet():
    conn = db()
    row = conn.execute("SELECT * FROM latest_state WHERE singleton_id=1").fetchone()
    conn.close()
    if not row:
        return {"online": False, "state": "OFFLINE"}
    pkt = dict(row)
    try:
        ts = datetime.fromisoformat(pkt["timestamp_utc"])
        age = (now_utc() - ts).total_seconds()
    except Exception:
        age = None
    pkt["age_s"] = age
    pkt["online"] = age is not None and age < 90
    if not pkt["online"] and pkt.get("state") is None:
        pkt["state"] = "OFFLINE"
    return pkt

def recent_history(limit=7200):
    conn = db()
    rows = conn.execute("""
        SELECT timestamp_utc,
               err_ns, period_ns, rms_ns,
               tcp_bytes, sbp_frames, crc_err,
               sats, pdop, cn0_avg,
               fe_phase_ns,
               gps_tow_ms, gps_ns_res,
               utc_ns
        FROM samples
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def filtered_err_values(limit=40000, abs_limit_ns=100000):
    rows = recent_history(limit)
    vals = []
    for r in rows:
        v = r.get("err_ns")
        if v is None:
            continue
        try:
            x = float(v)
        except Exception:
            continue
        if abs(x) > abs_limit_ns:
            continue
        vals.append(x)
    return vals

def rms_of(values):
    if not values:
        return None
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(var)

def peak_to_peak(values):
    if not values:
        return None
    return max(values) - min(values)

def allan_from_err_ns(err_ns_values):
    xs = []
    for v in err_ns_values:
        try:
            xs.append(float(v) * 1e-9)
        except Exception:
            pass

    n = len(xs)
    if n < 8:
        return []

    out = []
    m = 1
    while 2 * m < n:
        avgs = []
        for i in range(0, n - m + 1, m):
            chunk = xs[i:i + m]
            if len(chunk) == m:
                avgs.append(sum(chunk) / m)

        if len(avgs) < 3:
            break

        s = 0.0
        count = 0
        for i in range(len(avgs) - 2):
            d = avgs[i + 2] - 2 * avgs[i + 1] + avgs[i]
            s += d * d
            count += 1

        if count > 0:
            adev = math.sqrt(s / (2.0 * count)) / m
            out.append({"tau_s": m, "adev": adev})

        m *= 2

    return out

def histogram(values, bins=41):
    vals = []
    for v in values:
        if v is None:
            continue
        try:
            vals.append(float(v))
        except Exception:
            pass

    if len(vals) < 2:
        return {"centers": [], "counts": []}

    vmin = min(vals)
    vmax = max(vals)
    if vmin == vmax:
        vmin -= 1
        vmax += 1

    width = (vmax - vmin) / bins
    counts = [0] * bins
    centers = [vmin + (i + 0.5) * width for i in range(bins)]

    for v in vals:
        idx = int((v - vmin) / width)
        if idx >= bins:
            idx = bins - 1
        if idx < 0:
            idx = 0
        counts[idx] += 1

    return {"centers": centers, "counts": counts}

def frequency_ppb(period_ns_values):
    out = []
    for v in period_ns_values:
        if v is None:
            out.append(None)
            continue
        try:
            out.append((float(v) - 1_000_000_000.0) / 1_000_000_000.0 * 1e9)
        except Exception:
            out.append(None)
    return out

def holdover_estimate(err_ns_values, window=300):
    vals = []
    for v in err_ns_values[-window:]:
        if v is None:
            continue
        try:
            vals.append(float(v))
        except Exception:
            pass

    n = len(vals)
    if n < 10:
        return {"slope_ns_per_s": None, "drift_1h_ns": None}

    x_mean = (n - 1) / 2.0
    y_mean = sum(vals) / n

    num = 0.0
    den = 0.0
    for i, y in enumerate(vals):
        dx = i - x_mean
        dy = y - y_mean
        num += dx * dy
        den += dx * dx

    slope = num / den if den else 0.0
    return {
        "slope_ns_per_s": slope,
        "drift_1h_ns": slope * 3600.0
    }

def live_stats():
    vals = filtered_err_values(40000, abs_limit_ns=100000)
    current_phase = vals[-1] if vals else None

    vals_60 = vals[-60:] if vals else []
    vals_600 = vals[-600:] if vals else []

    rms_60 = rms_of(vals_60)
    rms_600 = rms_of(vals_600)
    p2p_60 = peak_to_peak(vals_60)

    adev_rows = allan_from_err_ns(vals[-5000:] if vals else [])
    adev_1s = None
    for row in adev_rows:
        if row.get("tau_s") == 1:
            adev_1s = row.get("adev")
            break

    return {
        "current_phase_err_ns": current_phase,
        "rms_60s_ns": rms_60,
        "rms_10m_ns": rms_600,
        "p2p_60s_ns": p2p_60,
        "adev_1s": adev_1s,
        "samples_60s": len(vals_60),
        "samples_10m": len(vals_600),
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/latest")
def api_latest():
    return jsonify(latest_packet())

@app.route("/api/history")
def api_history():
    return jsonify(recent_history(7200))

@app.route("/api/allan")
def api_allan():
    vals = filtered_err_values(20000, abs_limit_ns=100000)
    return jsonify(allan_from_err_ns(vals))

@app.route("/api/histogram")
def api_histogram():
    vals = filtered_err_values(5000, abs_limit_ns=100000)
    return jsonify(histogram(vals, bins=51))

@app.route("/api/frequency")
def api_frequency():
    rows = recent_history(5000)
    vals = [r.get("period_ns") for r in rows]
    return jsonify(frequency_ppb(vals))

@app.route("/api/holdover")
def api_holdover():
    vals = filtered_err_values(2000, abs_limit_ns=100000)
    return jsonify(holdover_estimate(vals, window=300))

@app.route("/api/live_stats")
def api_live_stats():
    return jsonify(live_stats())

@app.route("/api/raw/latest")
def api_raw_latest():
    pkt = latest_packet()
    return jsonify({"packet": pkt, "raw": pkt})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=HTTP_PORT, debug=False)
