#!/usr/bin/env python3
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("ZED_MONITOR_DB", "/home/pi/timing/zed_monitor.db")
STATUS_JSON = os.environ.get("ZED_MONITOR_STATUS", "/home/pi/timing/zed_status.json")
GPSPIPE_BIN = os.environ.get("GPSPIPE_BIN", "/usr/bin/gpspipe")
POLL_SECONDS = float(os.environ.get("ZED_MONITOR_POLL_SECONDS", "10"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def db_connect() -> sqlite3.Connection:
    ensure_parent(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS zed_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            gps_time_utc TEXT,
            mode INTEGER,
            fix_type TEXT,
            status TEXT,
            device TEXT,
            lat REAL,
            lon REAL,
            alt_m REAL,
            track_deg REAL,
            speed_m_s REAL,
            climb_m_s REAL,
            pdop REAL,
            hdop REAL,
            vdop REAL,
            sats_used INTEGER,
            sats_visible INTEGER,
            avg_cn0 REAL,
            max_cn0 REAL,
            gps_count INTEGER,
            glo_count INTEGER,
            gal_count INTEGER,
            bds_count INTEGER,
            qzss_count INTEGER,
            sbas_count INTEGER,
            unknown_count INTEGER,
            raw_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS zed_heartbeat (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ts_utc TEXT NOT NULL,
            ok INTEGER NOT NULL,
            message TEXT
        )
        """
    )
    conn.commit()
    return conn


def prn_constellation(prn: int) -> str:
    if 1 <= prn <= 32:
        return "gps"
    if 33 <= prn <= 64:
        return "sbas"
    if 65 <= prn <= 96:
        return "glo"
    if 120 <= prn <= 158:
        return "sbas"
    if 193 <= prn <= 197:
        return "qzss"
    if 201 <= prn <= 263:
        return "bds"
    if 301 <= prn <= 336:
        return "gal"
    return "unknown"


def mode_to_fix_type(mode: int | None) -> str:
    if mode == 1:
        return "NO_FIX"
    if mode == 2:
        return "2D"
    if mode == 3:
        return "3D"
    return "UNKNOWN"


def safe_float(v):
    try:
        if v is None:
            return None
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def safe_int(v):
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def run_gpspipe_once(timeout_sec: int = 12) -> list[dict]:
    cmd = [GPSPIPE_BIN, "-w", "-n", "12"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    lines = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            lines.append(json.loads(line))
        except Exception:
            pass
    return lines


def extract_sample(objs: list[dict]) -> dict:
    tpv = None
    sky = None
    dev = None

    for obj in objs:
        cls = obj.get("class")
        if cls == "DEVICE":
            dev = obj
        elif cls == "TPV":
            tpv = obj
        elif cls == "SKY":
            sky = obj

    satellites = []
    if sky and isinstance(sky.get("satellites"), list):
        satellites = sky["satellites"]

    sats_visible = len(satellites)
    sats_used = sum(1 for s in satellites if s.get("used") is True)

    cn0_values = []
    constellation_counts = {
        "gps": 0,
        "glo": 0,
        "gal": 0,
        "bds": 0,
        "qzss": 0,
        "sbas": 0,
        "unknown": 0,
    }

    for sat in satellites:
        prn = safe_int(sat.get("PRN"))
        cno = safe_float(sat.get("ss"))
        if cno is not None:
            cn0_values.append(cno)
        if prn is not None:
            key = prn_constellation(prn)
            if key not in constellation_counts:
                key = "unknown"
            constellation_counts[key] += 1
        else:
            constellation_counts["unknown"] += 1

    mode = safe_int((tpv or {}).get("mode"))
    sample = {
        "ts_utc": utc_now_iso(),
        "gps_time_utc": (tpv or {}).get("time"),
        "mode": mode,
        "fix_type": mode_to_fix_type(mode),
        "status": "OK" if tpv or sky else "NO_DATA",
        "device": (dev or {}).get("path") or (tpv or {}).get("device") or (sky or {}).get("device"),
        "lat": safe_float((tpv or {}).get("lat")),
        "lon": safe_float((tpv or {}).get("lon")),
        "alt_m": safe_float((tpv or {}).get("altHAE") or (tpv or {}).get("alt")),
        "track_deg": safe_float((tpv or {}).get("track")),
        "speed_m_s": safe_float((tpv or {}).get("speed")),
        "climb_m_s": safe_float((tpv or {}).get("climb")),
        "pdop": safe_float((sky or {}).get("pdop")),
        "hdop": safe_float((sky or {}).get("hdop")),
        "vdop": safe_float((sky or {}).get("vdop")),
        "sats_used": sats_used,
        "sats_visible": sats_visible,
        "avg_cn0": round(sum(cn0_values) / len(cn0_values), 3) if cn0_values else None,
        "max_cn0": round(max(cn0_values), 3) if cn0_values else None,
        "gps_count": constellation_counts["gps"],
        "glo_count": constellation_counts["glo"],
        "gal_count": constellation_counts["gal"],
        "bds_count": constellation_counts["bds"],
        "qzss_count": constellation_counts["qzss"],
        "sbas_count": constellation_counts["sbas"],
        "unknown_count": constellation_counts["unknown"],
        "raw_json": json.dumps({"tpv": tpv, "sky": sky, "device": dev}, sort_keys=True),
    }
    return sample


def write_status_json(sample: dict) -> None:
    ensure_parent(STATUS_JSON)
    tmp = STATUS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, STATUS_JSON)


def store_sample(conn: sqlite3.Connection, sample: dict) -> None:
    conn.execute(
        """
        INSERT INTO zed_samples (
            ts_utc, gps_time_utc, mode, fix_type, status, device,
            lat, lon, alt_m, track_deg, speed_m_s, climb_m_s,
            pdop, hdop, vdop, sats_used, sats_visible,
            avg_cn0, max_cn0,
            gps_count, glo_count, gal_count, bds_count, qzss_count, sbas_count, unknown_count,
            raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sample["ts_utc"],
            sample["gps_time_utc"],
            sample["mode"],
            sample["fix_type"],
            sample["status"],
            sample["device"],
            sample["lat"],
            sample["lon"],
            sample["alt_m"],
            sample["track_deg"],
            sample["speed_m_s"],
            sample["climb_m_s"],
            sample["pdop"],
            sample["hdop"],
            sample["vdop"],
            sample["sats_used"],
            sample["sats_visible"],
            sample["avg_cn0"],
            sample["max_cn0"],
            sample["gps_count"],
            sample["glo_count"],
            sample["gal_count"],
            sample["bds_count"],
            sample["qzss_count"],
            sample["sbas_count"],
            sample["unknown_count"],
            sample["raw_json"],
        ),
    )
    conn.execute(
        """
        INSERT INTO zed_heartbeat (id, ts_utc, ok, message)
        VALUES (1, ?, 1, ?)
        ON CONFLICT(id) DO UPDATE SET
            ts_utc = excluded.ts_utc,
            ok = excluded.ok,
            message = excluded.message
        """,
        (sample["ts_utc"], f"fix={sample['fix_type']} sats_used={sample['sats_used']} pdop={sample['pdop']}"),
    )
    conn.commit()


def store_failure(conn: sqlite3.Connection, message: str) -> None:
    ts = utc_now_iso()
    conn.execute(
        """
        INSERT INTO zed_heartbeat (id, ts_utc, ok, message)
        VALUES (1, ?, 0, ?)
        ON CONFLICT(id) DO UPDATE SET
            ts_utc = excluded.ts_utc,
            ok = excluded.ok,
            message = excluded.message
        """,
        (ts, message[:500]),
    )
    conn.commit()


def one_line_summary(sample: dict) -> str:
    return (
        f"{sample['ts_utc']} "
        f"fix={sample['fix_type']} status={sample['status']} "
        f"used={sample['sats_used']} visible={sample['sats_visible']} "
        f"pdop={sample['pdop']} avg_cn0={sample['avg_cn0']} max_cn0={sample['max_cn0']}"
    )


def main() -> int:
    conn = db_connect()
    print(f"zed-monitor starting: db={DB_PATH} status={STATUS_JSON} poll={POLL_SECONDS}s", flush=True)

    while True:
        loop_start = time.time()
        try:
            objs = run_gpspipe_once(timeout_sec=max(12, int(POLL_SECONDS) + 5))
            sample = extract_sample(objs)
            write_status_json(sample)
            store_sample(conn, sample)
            print(one_line_summary(sample), flush=True)
        except subprocess.TimeoutExpired:
            msg = "gpspipe timeout"
            store_failure(conn, msg)
            print(msg, file=sys.stderr, flush=True)
        except Exception as exc:
            msg = f"zed-monitor error: {exc}"
            store_failure(conn, msg)
            print(msg, file=sys.stderr, flush=True)

        elapsed = time.time() - loop_start
        sleep_for = max(1.0, POLL_SECONDS - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
