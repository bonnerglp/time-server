from pathlib import Path
import sys

REPO_ROOT = "/home/pi/time-server"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pi.utils.version import get_version
REPO_VERSION = get_version()

#!/usr/bin/env python3
import os
import sqlite3
import math
import statistics
from datetime import datetime, timedelta, timezone

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE_DIR = "/home/pi/timing"
DB_PATH = os.path.join(BASE_DIR, "timing.db")

OUT_SUMMARY_TXT = os.path.join(BASE_DIR, "report_summary.txt")
OUT_SUMMARY_HTML = os.path.join(BASE_DIR, "report_summary.html")
OUT_LATEST_TXT = os.path.join(BASE_DIR, "latest_snapshot.txt")
OUT_LATEST_HTML = os.path.join(BASE_DIR, "latest_snapshot.html")

OUT_PHASE_7D = os.path.join(BASE_DIR, "timing_7d.png")
OUT_PHASE_30D = os.path.join(BASE_DIR, "timing_30d.png")
OUT_PHASE_90D = os.path.join(BASE_DIR, "timing_90d.png")
OUT_HIST_24H = os.path.join(BASE_DIR, "timing_hist_24h.png")

OUT_JITTER10M_1D = os.path.join(BASE_DIR, "jitter10m_1d.png")
OUT_JITTER10M_7D = os.path.join(BASE_DIR, "jitter10m_7d.png")
OUT_JITTER10M_30D = os.path.join(BASE_DIR, "jitter10m_30d.png")
OUT_JITTER10M_90D = os.path.join(BASE_DIR, "jitter10m_90d.png")

OUT_RMS60_1D = os.path.join(BASE_DIR, "rms60_1d.png")
OUT_RMS60_7D = os.path.join(BASE_DIR, "rms60_7d.png")
OUT_SATS_PDOP_1D = os.path.join(BASE_DIR, "sats_pdop_1d.png")
OUT_ALLAN_TRUE_TAU = os.path.join(BASE_DIR, "allan_true_tau.png")

def parse_ts(s):
    s = str(s).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def fmt_num(v, units="", sci=False):
    if v is None:
        return "N/A"
    if sci:
        txt = f"{v:.3e}"
    else:
        av = abs(v)
        if av != 0 and (av < 0.01 or av >= 1e6):
            txt = f"{v:.3e}"
        else:
            txt = f"{v:.3f}"
    return f"{txt}{(' ' + units) if units else ''}"

def load_rows():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("""
            SELECT
                bucket_start,
                avg_phase_ns,
                rms_phase_ns,
                avg_rms60_ns,
                avg_adev_1s,
                avg_sats,
                avg_pdop,
                samples
            FROM timing_10min
            ORDER BY bucket_start
        """)
        rows = []
        for r in cur.fetchall():
            rows.append({
                "dt": parse_ts(r[0]),
                "avg_phase_ns": float(r[1]) if r[1] is not None else None,
                "rms_phase_ns": float(r[2]) if r[2] is not None else None,
                "avg_rms60_ns": float(r[3]) if r[3] is not None else None,
                "avg_adev_1s": float(r[4]) if r[4] is not None else None,
                "avg_sats": float(r[5]) if r[5] is not None else None,
                "avg_pdop": float(r[6]) if r[6] is not None else None,
                "samples": int(r[7]) if r[7] is not None else 0,
            })
        return rows
    finally:
        conn.close()

def load_latest():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("""
            SELECT
                timestamp,
                state,
                current_phase_err_ns,
                rms_60s_ns,
                rms_10m_ns,
                p2p_60s_ns,
                adev_1s,
                sats,
                pdop,
                cn0_avg,
                gps_ns_res,
                period_ns,
                fe_holdover,
                tcp_ok,
                gps_ok,
                pps_ok
            FROM teensy_telemetry
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        r = cur.fetchone()
        if not r:
            return None
        return {
            "timestamp": r[0],
            "state": r[1],
            "current_phase_err_ns": r[2],
            "rms_60s_ns": r[3],
            "rms_10m_ns": r[4],
            "p2p_60s_ns": r[5],
            "adev_1s": r[6],
            "sats": r[7],
            "pdop": r[8],
            "cn0_avg": r[9],
            "gps_ns_res": r[10],
            "period_ns": r[11],
            "fe_holdover": r[12],
            "tcp_ok": r[13],
            "gps_ok": r[14],
            "pps_ok": r[15],
        }
    finally:
        conn.close()

def load_raw_phase(days=7):
    conn = sqlite3.connect(DB_PATH)
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cur = conn.execute("""
            SELECT timestamp, current_phase_err_ns
            FROM teensy_telemetry
            WHERE timestamp >= ?
              AND current_phase_err_ns IS NOT NULL
            ORDER BY timestamp
        """, (cutoff,))
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return None, None

    t = np.array([parse_ts(r[0]).timestamp() for r in rows], dtype=float)
    x_ns = np.array([float(r[1]) for r in rows], dtype=float)

    good = np.isfinite(t) & np.isfinite(x_ns)
    t = t[good]
    x_ns = x_ns[good]

    if len(t) < 20:
        return None, None

    order = np.argsort(t)
    t = t[order]
    x_ns = x_ns[order]

    uniq_idx = np.concatenate(([True], np.diff(t) > 0))
    t = t[uniq_idx]
    x_ns = x_ns[uniq_idx]

    if len(t) < 20:
        return None, None

    return t, x_ns * 1e-9

def resample_phase_to_1s(t, x_sec):
    if t is None or x_sec is None or len(t) < 20:
        return None, None

    start = math.ceil(t[0])
    stop = math.floor(t[-1])

    if stop - start < 100:
        return None, None

    grid = np.arange(start, stop + 1, 1.0)
    x_grid = np.interp(grid, t, x_sec)
    return grid, x_grid

def overlapping_adev_from_phase(x_sec, tau0=1.0):
    n = len(x_sec)
    if n < 10:
        return None, None

    max_m = max(1, n // 10)
    ms = []
    base = 1
    while base <= max_m:
        for mult in (1, 2, 5):
            m = mult * base
            if m <= max_m:
                ms.append(m)
        base *= 10
    ms = sorted(set(ms))

    taus = []
    adevs = []
    x = np.asarray(x_sec, dtype=float)

    for m in ms:
        if n - 2 * m < 10:
            continue
        d = x[2*m:] - 2*x[m:-m] + x[:-2*m]
        sigma2 = np.sum(d * d) / (2.0 * (m * tau0) ** 2 * (n - 2 * m))
        if sigma2 > 0 and np.isfinite(sigma2):
            taus.append(m * tau0)
            adevs.append(math.sqrt(sigma2))

    if not taus:
        return None, None

    return np.array(taus, dtype=float), np.array(adevs, dtype=float)

def since(rows, days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [r for r in rows if r["dt"] >= cutoff]

def values(rows, key):
    return [r[key] for r in rows if r[key] is not None]

def stats(vals):
    if not vals:
        return None
    mean_v = statistics.fmean(vals)
    rms_v = math.sqrt(statistics.fmean([v * v for v in vals]))
    std_v = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    median_v = statistics.median(vals)
    p95_v = sorted(vals)[max(0, math.ceil(0.95 * len(vals)) - 1)]
    return {
        "count": len(vals),
        "min": min(vals),
        "max": max(vals),
        "mean": mean_v,
        "median": median_v,
        "rms": rms_v,
        "std": std_v,
        "p95": p95_v,
    }

def fmt_stats(label, s, units="ns", sci=False):
    if s is None:
        return f"{label}: no data"
    return (
        f"{label}: n={s['count']}, "
        f"min={fmt_num(s['min'], units, sci)}, "
        f"max={fmt_num(s['max'], units, sci)}, "
        f"mean={fmt_num(s['mean'], units, sci)}, "
        f"median={fmt_num(s['median'], units, sci)}, "
        f"rms={fmt_num(s['rms'], units, sci)}, "
        f"std={fmt_num(s['std'], units, sci)}, "
        f"p95={fmt_num(s['p95'], units, sci)}"
    )

def moving_average(vals, window):
    out = []
    for i in range(len(vals)):
        start = max(0, i - window + 1)
        sub = vals[start:i+1]
        out.append(sum(sub) / len(sub))
    return out

def style_time_axis(ax, days, start, now):
    ax.set_xlim(start, now)
    if days <= 1:
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    elif days <= 7:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    elif days <= 30:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    else:
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    plt.xticks(rotation=30, ha="right")

def plot_series(rows, days, key, ylabel, title, out_png, zero_line=False, rolling_window=6):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    sub = [r for r in rows if r[key] is not None and r["dt"] >= start]
    if not sub:
        return False

    x = [r["dt"] for r in sub]
    y = [r[key] for r in sub]
    y_roll = moving_average(y, rolling_window)

    plt.figure(figsize=(12, 5.5))
    plt.plot(x, y, linewidth=1.0, alpha=0.6, label="raw")
    plt.plot(x, y_roll, linewidth=2.0, label=f"rolling avg ({rolling_window} pts)")
    if zero_line:
        plt.axhline(0, linewidth=1.0, linestyle="--", alpha=0.7)

    plt.title(title)
    plt.xlabel("UTC time")
    plt.ylabel(ylabel)
    ax = plt.gca()
    style_time_axis(ax, days, start, now)
    ax.grid(True, which="major", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    return True

def plot_hist_24h(rows, out_png):
    sub = since(rows, 1)
    vals = [r["avg_phase_ns"] for r in sub if r["avg_phase_ns"] is not None]
    if not vals:
        return False
    plt.figure(figsize=(10, 5))
    plt.hist(vals, bins=40)
    plt.title("Average Phase Histogram - Last 24 Hours")
    plt.xlabel("Average phase (ns)")
    plt.ylabel("Count")
    plt.grid(True, which="major", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    return True

def plot_sats_pdop(rows, out_png):
    sub = since(rows, 1)
    sub = [r for r in sub if r["avg_sats"] is not None or r["avg_pdop"] is not None]
    if not sub:
        return False

    x = [r["dt"] for r in sub]
    sats = [r["avg_sats"] if r["avg_sats"] is not None else float("nan") for r in sub]
    pdop = [r["avg_pdop"] if r["avg_pdop"] is not None else float("nan") for r in sub]

    fig, ax1 = plt.subplots(figsize=(12, 5.5))
    ax1.plot(x, sats, linewidth=1.5)
    ax1.set_ylabel("Satellites")
    ax1.set_xlabel("UTC time")
    style_time_axis(ax1, 1, datetime.now(timezone.utc) - timedelta(days=1), datetime.now(timezone.utc))
    ax1.grid(True, which="major", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(x, pdop, linewidth=1.2, linestyle="--")
    ax2.set_ylabel("PDOP")

    fig.suptitle("Satellites and PDOP - Last 24 Hours")
    fig.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    return True

def plot_true_allan_tau(t, x_sec, out_png):
    grid_t, grid_x = resample_phase_to_1s(t, x_sec)
    if grid_t is None or grid_x is None:
        return None, None

    taus, adevs = overlapping_adev_from_phase(grid_x, tau0=1.0)
    if taus is None or adevs is None or len(taus) == 0:
        return None, None

    plt.figure(figsize=(8.5, 5.5))
    plt.loglog(taus, adevs, marker="o", linewidth=1.8)
    plt.title("True Overlapping Allan Deviation vs Tau")
    plt.xlabel("Tau (s)")
    plt.ylabel("ADEV")
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()

    return taus, adevs

def trend_24h(rows):
    now = datetime.now(timezone.utc)
    last24 = [r["avg_phase_ns"] for r in rows if r["avg_phase_ns"] is not None and r["dt"] >= now - timedelta(days=1)]
    prev24 = [r["avg_phase_ns"] for r in rows if r["avg_phase_ns"] is not None and now - timedelta(days=2) <= r["dt"] < now - timedelta(days=1)]
    if not last24 or not prev24:
        return None
    prev_mean = statistics.fmean(prev24)
    last_mean = statistics.fmean(last24)
    delta = last_mean - prev_mean
    return prev_mean, last_mean, delta

def write_latest_snapshot(latest):
    if not latest:
        with open(OUT_LATEST_TXT, "w", encoding="utf-8") as f:
            f.write("No latest telemetry available.\n")
        with open(OUT_LATEST_HTML, "w", encoding="utf-8") as f:
            f.write("<html><body><p>No latest telemetry available.</p></body></html>\n")
        return

    lines = [
        "Latest Timing Snapshot",
        f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Telemetry timestamp : {latest['timestamp']}",
        f"State               : {latest['state']}",
        f"Current phase error : {latest['current_phase_err_ns']} ns",
        f"RMS 60s             : {latest['rms_60s_ns']} ns",
        f"RMS 10m             : {latest['rms_10m_ns']} ns",
        f"P2P 60s             : {latest['p2p_60s_ns']} ns",
        f"ADEV 1s             : {latest['adev_1s']}",
        f"Satellites          : {latest['sats']}",
        f"PDOP                : {latest['pdop']}",
        f"C/N0 avg            : {latest['cn0_avg']}",
        f"GPS ns residual     : {latest['gps_ns_res']} ns",
        f"PPS period          : {latest['period_ns']} ns",
        f"Holdover            : {latest['fe_holdover']}",
        f"TCP OK              : {latest['tcp_ok']}",
        f"GPS OK              : {latest['gps_ok']}",
        f"PPS OK              : {latest['pps_ok']}",
    ]

    with open(OUT_LATEST_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    html = []
    html.append("<!doctype html><html><head><meta charset='utf-8'><title>Latest Timing Snapshot</title>")
    html.append("<style>body{font-family:Arial,sans-serif;margin:20px;color:#222} pre{background:#f6f6f6;padding:12px;border:1px solid #ddd}</style>")
    html.append("</head><body><h2>Latest Timing Snapshot</h2><pre>")
    html.append("\n".join(lines))
    html.append("</pre></body></html>")

    with open(OUT_LATEST_HTML, "w", encoding="utf-8") as f:
        f.write("\n".join(html) + "\n")

def write_reports(rows, latest, taus, adevs):
    now = datetime.now(timezone.utc)

    rows_24h = since(rows, 1)
    rows_7d = since(rows, 7)
    rows_30d = since(rows, 30)
    rows_90d = since(rows, 90)

    phase_24h = stats(values(rows_24h, "avg_phase_ns"))
    phase_7d = stats(values(rows_7d, "avg_phase_ns"))
    phase_30d = stats(values(rows_30d, "avg_phase_ns"))
    phase_90d = stats(values(rows_90d, "avg_phase_ns"))

    jitter10m_24h = stats(values(rows_24h, "rms_phase_ns"))
    jitter10m_7d = stats(values(rows_7d, "rms_phase_ns"))
    jitter10m_30d = stats(values(rows_30d, "rms_phase_ns"))
    jitter10m_90d = stats(values(rows_90d, "rms_phase_ns"))

    rms60_24h = stats(values(rows_24h, "avg_rms60_ns"))
    rms60_7d = stats(values(rows_7d, "avg_rms60_ns"))

    adev1s_24h = stats(values(rows_24h, "avg_adev_1s"))
    adev1s_7d = stats(values(rows_7d, "avg_adev_1s"))
    adev1s_30d = stats(values(rows_30d, "avg_adev_1s"))
    adev1s_90d = stats(values(rows_90d, "avg_adev_1s"))

    sats_24h = stats(values(rows_24h, "avg_sats"))
    pdop_24h = stats(values(rows_24h, "avg_pdop"))

    tr = trend_24h(rows)

    lines = []
    lines.append("Timing Report Summary")
    lines.append(f"Generated (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("Source table: timing_10min")
    lines.append("Primary metric: avg_phase_ns")
    lines.append("Jitter metric: rms_phase_ns (10-minute RMS jitter)")
    lines.append("ADEV metric in timing_10min: avg_adev_1s")
    lines.append("True multi-tau ADEV source: teensy_telemetry.current_phase_err_ns")
    lines.append("")

    if latest:
        lines.append("Latest snapshot")
        lines.append(f"  Telemetry timestamp : {latest['timestamp']}")
        lines.append(f"  State               : {latest['state']}")
        lines.append(f"  Current phase error : {latest['current_phase_err_ns']} ns")
        lines.append(f"  RMS 60s             : {latest['rms_60s_ns']} ns")
        lines.append(f"  RMS 10m             : {latest['rms_10m_ns']} ns")
        lines.append(f"  P2P 60s             : {latest['p2p_60s_ns']} ns")
        lines.append(f"  ADEV 1s             : {latest['adev_1s']}")
        lines.append(f"  Satellites          : {latest['sats']}")
        lines.append(f"  PDOP                : {latest['pdop']}")
        lines.append(f"  C/N0 avg            : {latest['cn0_avg']}")
        lines.append("")
    else:
        lines.append("Latest snapshot: unavailable")
        lines.append("")

    lines.append(fmt_stats("Avg phase - last 24h", phase_24h, "ns"))
    lines.append(fmt_stats("Avg phase - last 7d", phase_7d, "ns"))
    lines.append(fmt_stats("Avg phase - last 30d", phase_30d, "ns"))
    lines.append(fmt_stats("Avg phase - last 90d", phase_90d, "ns"))
    lines.append("")

    lines.append(fmt_stats("10m RMS jitter - last 24h", jitter10m_24h, "ns"))
    lines.append(fmt_stats("10m RMS jitter - last 7d", jitter10m_7d, "ns"))
    lines.append(fmt_stats("10m RMS jitter - last 30d", jitter10m_30d, "ns"))
    lines.append(fmt_stats("10m RMS jitter - last 90d", jitter10m_90d, "ns"))
    lines.append("")

    lines.append(fmt_stats("RMS60 - last 24h", rms60_24h, "ns"))
    lines.append(fmt_stats("RMS60 - last 7d", rms60_7d, "ns"))
    lines.append("")

    lines.append(fmt_stats("ADEV 1s in timing_10min - last 24h", adev1s_24h, "", sci=True))
    lines.append(fmt_stats("ADEV 1s in timing_10min - last 7d", adev1s_7d, "", sci=True))
    lines.append(fmt_stats("ADEV 1s in timing_10min - last 30d", adev1s_30d, "", sci=True))
    lines.append(fmt_stats("ADEV 1s in timing_10min - last 90d", adev1s_90d, "", sci=True))
    lines.append("")

    lines.append(fmt_stats("Satellites - last 24h", sats_24h, ""))
    lines.append(fmt_stats("PDOP - last 24h", pdop_24h, ""))
    lines.append("")

    if taus is not None and adevs is not None and len(taus) > 0:
        lines.append("True overlapping Allan deviation vs tau")
        for tau, adev in zip(taus, adevs):
            lines.append(f"  tau={int(tau):>5d} s : adev={adev:.3e}")
        lines.append("")
    else:
        lines.append("True overlapping Allan deviation vs tau: insufficient raw data")
        lines.append("")

    if tr is None:
        lines.append("Trend: insufficient data for last-24h vs prior-24h comparison")
    else:
        prev_mean, last_mean, delta = tr
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
        lines.append(
            f"Trend: last 24h mean={last_mean:.3f} ns, "
            f"prior 24h mean={prev_mean:.3f} ns, "
            f"change={delta:.3f} ns ({direction})"
        )

    lines.append("")
    lines.append(f"10-minute rows total: {len(rows)}")
    lines.append(f"10-minute rows in last 24h: {len(rows_24h)}")
    lines.append(f"10-minute rows in last 7d: {len(rows_7d)}")
    lines.append(f"10-minute rows in last 30d: {len(rows_30d)}")
    lines.append(f"10-minute rows in last 90d: {len(rows_90d)}")

    with open(OUT_SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    html = []
    html.append("<!doctype html>")
    html.append("<html><head><meta charset='utf-8'><title>Timing Report Summary</title>")
    html.append("<style>")
    html.append("body{font-family:Arial,sans-serif;margin:20px;color:#222}")
    html.append("pre{background:#f6f6f6;padding:12px;border:1px solid #ddd;overflow-x:auto}")
    html.append("img{max-width:1000px;height:auto;margin-bottom:18px}")
    html.append("</style></head><body>")
    html.append("<h2>Timing Report Summary</h2>")
    html.append(f"<p><b>Generated (UTC):</b> {now.strftime('%Y-%m-%d %H:%M:%S')}</p>")
    html.append("<pre>")
    html.append("\n".join(lines))
    html.append("</pre>")

    sections = [
        ("timing_7d.png", "Average phase - 7 day"),
        ("timing_30d.png", "Average phase - 30 day"),
        ("timing_90d.png", "Average phase - 90 day"),
        ("timing_hist_24h.png", "Average phase histogram - last 24 hours"),
        ("jitter10m_1d.png", "10-minute RMS jitter - 1 day"),
        ("jitter10m_7d.png", "10-minute RMS jitter - 7 day"),
        ("jitter10m_30d.png", "10-minute RMS jitter - 30 day"),
        ("jitter10m_90d.png", "10-minute RMS jitter - 90 day"),
        ("rms60_1d.png", "RMS 60s - 1 day"),
        ("rms60_7d.png", "RMS 60s - 7 day"),
        ("sats_pdop_1d.png", "Satellites and PDOP - 1 day"),
        ("allan_true_tau.png", "True overlapping Allan deviation vs tau"),
    ]
    for fn, label in sections:
        path = os.path.join(BASE_DIR, fn)
        if os.path.exists(path):
            html.append(f"<h3>{label}</h3>")
            html.append(f"<img src='{fn}' alt='{label}'>")

    html.append("</body></html>")

    with open(OUT_SUMMARY_HTML, "w", encoding="utf-8") as f:
        f.write("\n".join(html) + "\n")

def main():
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    rows = load_rows()
    if not rows:
        raise RuntimeError("No rows found in timing_10min")

    latest = load_latest()

    raw_t, raw_x = load_raw_phase(days=7)
    taus, adevs = plot_true_allan_tau(raw_t, raw_x, OUT_ALLAN_TRUE_TAU)

    plot_series(rows, 7, "avg_phase_ns", "Average phase (ns)", "Average Phase - Last 7 Days", OUT_PHASE_7D, zero_line=True)
    plot_series(rows, 30, "avg_phase_ns", "Average phase (ns)", "Average Phase - Last 30 Days", OUT_PHASE_30D, zero_line=True)
    plot_series(rows, 90, "avg_phase_ns", "Average phase (ns)", "Average Phase - Last 90 Days", OUT_PHASE_90D, zero_line=True)

    plot_series(rows, 1, "rms_phase_ns", "10-minute RMS jitter (ns)", "10-Minute RMS Jitter - Last 1 Day", OUT_JITTER10M_1D)
    plot_series(rows, 7, "rms_phase_ns", "10-minute RMS jitter (ns)", "10-Minute RMS Jitter - Last 7 Days", OUT_JITTER10M_7D)
    plot_series(rows, 30, "rms_phase_ns", "10-minute RMS jitter (ns)", "10-Minute RMS Jitter - Last 30 Days", OUT_JITTER10M_30D)
    plot_series(rows, 90, "rms_phase_ns", "10-minute RMS jitter (ns)", "10-Minute RMS Jitter - Last 90 Days", OUT_JITTER10M_90D)

    plot_series(rows, 1, "avg_rms60_ns", "RMS 60s (ns)", "RMS 60s - Last 1 Day", OUT_RMS60_1D)
    plot_series(rows, 7, "avg_rms60_ns", "RMS 60s (ns)", "RMS 60s - Last 7 Days", OUT_RMS60_7D)

    plot_hist_24h(rows, OUT_HIST_24H)
    plot_sats_pdop(rows, OUT_SATS_PDOP_1D)

    write_latest_snapshot(latest)
    write_reports(rows, latest, taus, adevs)

    print("Report upgrade complete")
    print(f"Summary TXT:  {OUT_SUMMARY_TXT}")
    print(f"Summary HTML: {OUT_SUMMARY_HTML}")
    print(f"Latest TXT:   {OUT_LATEST_TXT}")
    print(f"Latest HTML:  {OUT_LATEST_HTML}")
    print(f"Allan plot:   {OUT_ALLAN_TRUE_TAU}")
    print(f"Phase plots: {OUT_PHASE_7D}, {OUT_PHASE_30D}, {OUT_PHASE_90D}")
    print(f"Jitter plots: {OUT_JITTER10M_1D}, {OUT_JITTER10M_7D}, {OUT_JITTER10M_30D}, {OUT_JITTER10M_90D}")
    print(f"Other plots: {OUT_RMS60_1D}, {OUT_RMS60_7D}, {OUT_SATS_PDOP_1D}, {OUT_HIST_24H}")

if __name__ == "__main__":
    main()



def _prepend_system_version(path_str, repo_version):
    from pathlib import Path
    p = Path(path_str)
    if not p.exists():
        return
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return
    line = f"System version: {repo_version}\n"
    if text.startswith(line):
        return
    p.write_text(line + "\n" + text, encoding="utf-8")

_prepend_system_version("/home/pi/timing/report_summary.txt", REPO_VERSION)
_prepend_system_version("/home/pi/timing/latest_snapshot.txt", REPO_VERSION)
