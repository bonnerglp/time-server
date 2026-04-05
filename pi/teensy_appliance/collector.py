from pathlib import Path
import sys

REPO_ROOT = "/home/pi/time-server"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pi.utils.version import get_version
REPO_VERSION = get_version()

import os
import socket
import sqlite3
import time
from datetime import datetime, timezone

DB_PATH = os.path.expanduser("~/teensy_appliance/teensy_stats.db")
UDP_PORT = 5005

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    repo_version TEXT,

    pps INTEGER,
    state TEXT,
    pps_ok INTEGER,
    zed_ok INTEGER,
    tcp_ok INTEGER,
    utc_ok INTEGER,
    gps_ok INTEGER,
    tracking INTEGER,

    period_ns REAL,
    err_ns REAL,
    rms_ns REAL,
    min_err_ns REAL,
    max_err_ns REAL,

    tcp_bytes INTEGER,
    sbp_frames INTEGER,
    crc_err INTEGER,

    gps_week INTEGER,
    gps_tow_ms INTEGER,
    gps_ns_res REAL,
    utc TEXT,
    utc_ns INTEGER,
    utc_flags TEXT,

    sats INTEGER,
    sats_visible INTEGER,
    pdop REAL,
    hdop REAL,
    vdop REAL,
    cn0_avg REAL,
    cn0_max REAL,
    fix_type TEXT,

    gps_count INTEGER,
    gal_count INTEGER,
    glo_count INTEGER,
    bds_count INTEGER,
    qzss_count INTEGER,
    zed_status TEXT,

    piksi_minus_zed_ns REAL,
    piksi_minus_zed_rms_ns REAL,
    piksi_minus_zed_valid INTEGER,
    piksi_minus_zed_rejected INTEGER,
    piksi_minus_zed_min_ns REAL,
    piksi_minus_zed_max_ns REAL,

    fe_hz INTEGER,
    fe_mhz REAL,
    fe_valid INTEGER,
    fe_sanity_ok INTEGER,
    fe_low_hz INTEGER,
    fe_high_hz INTEGER,

    fe_ppb REAL,
    fe_delta_hz REAL,
    fe_avg_hz REAL,
    fe_min_hz REAL,
    fe_max_hz REAL,
    fe_stability_rms_hz REAL
);

CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON samples(timestamp_utc);
"""

LATEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS latest_state (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    timestamp_utc TEXT NOT NULL,
    repo_version TEXT,

    pps INTEGER,
    state TEXT,
    pps_ok INTEGER,
    zed_ok INTEGER,
    tcp_ok INTEGER,
    utc_ok INTEGER,
    gps_ok INTEGER,
    tracking INTEGER,

    period_ns REAL,
    err_ns REAL,
    rms_ns REAL,
    min_err_ns REAL,
    max_err_ns REAL,

    tcp_bytes INTEGER,
    sbp_frames INTEGER,
    crc_err INTEGER,

    gps_week INTEGER,
    gps_tow_ms INTEGER,
    gps_ns_res REAL,
    utc TEXT,
    utc_ns INTEGER,
    utc_flags TEXT,

    sats INTEGER,
    sats_visible INTEGER,
    pdop REAL,
    hdop REAL,
    vdop REAL,
    cn0_avg REAL,
    cn0_max REAL,
    fix_type TEXT,

    gps_count INTEGER,
    gal_count INTEGER,
    glo_count INTEGER,
    bds_count INTEGER,
    qzss_count INTEGER,
    zed_status TEXT,

    piksi_minus_zed_ns REAL,
    piksi_minus_zed_rms_ns REAL,
    piksi_minus_zed_valid INTEGER,
    piksi_minus_zed_rejected INTEGER,
    piksi_minus_zed_min_ns REAL,
    piksi_minus_zed_max_ns REAL,

    fe_hz INTEGER,
    fe_mhz REAL,
    fe_valid INTEGER,
    fe_sanity_ok INTEGER,
    fe_low_hz INTEGER,
    fe_high_hz INTEGER,

    fe_ppb REAL,
    fe_delta_hz REAL,
    fe_avg_hz REAL,
    fe_min_hz REAL,
    fe_max_hz REAL,
    fe_stability_rms_hz REAL
);
"""

FIELDS = [
    "pps", "state", "pps_ok", "zed_ok", "tcp_ok", "utc_ok", "gps_ok", "tracking",
    "period_ns", "err_ns", "rms_ns", "min_err_ns", "max_err_ns",
    "tcp_bytes", "sbp_frames", "crc_err",
    "gps_week", "gps_tow_ms", "gps_ns_res",
    "utc", "utc_ns", "utc_flags",
    "sats", "sats_visible", "pdop", "hdop", "vdop", "cn0_avg", "cn0_max", "fix_type",
    "gps_count", "gal_count", "glo_count", "bds_count", "qzss_count", "zed_status",
    "piksi_minus_zed_ns", "piksi_minus_zed_rms_ns", "piksi_minus_zed_valid",
    "piksi_minus_zed_rejected", "piksi_minus_zed_min_ns", "piksi_minus_zed_max_ns",
    "fe_hz", "fe_mhz", "fe_valid", "fe_sanity_ok", "fe_low_hz", "fe_high_hz",
    "fe_ppb", "fe_delta_hz", "fe_avg_hz", "fe_min_hz", "fe_max_hz", "fe_stability_rms_hz",
]

MAX_ABS_ERR_NS = 100000
MIN_PERIOD_NS = 900_000_000
MAX_PERIOD_NS = 1_100_000_000

MIGRATION_COLUMNS = {
    "repo_version": "TEXT",
    "zed_ok": "INTEGER",
    "sats_visible": "INTEGER",
    "hdop": "REAL",
    "vdop": "REAL",
    "cn0_max": "REAL",
    "gps_count": "INTEGER",
    "gal_count": "INTEGER",
    "glo_count": "INTEGER",
    "bds_count": "INTEGER",
    "qzss_count": "INTEGER",
    "zed_status": "TEXT",
    "piksi_minus_zed_ns": "REAL",
    "piksi_minus_zed_rms_ns": "REAL",
    "piksi_minus_zed_valid": "INTEGER",
    "piksi_minus_zed_rejected": "INTEGER",
    "piksi_minus_zed_min_ns": "REAL",
    "piksi_minus_zed_max_ns": "REAL",
    "fe_hz": "INTEGER",
    "fe_mhz": "REAL",
    "fe_valid": "INTEGER",
    "fe_sanity_ok": "INTEGER",
    "fe_low_hz": "INTEGER",
    "fe_high_hz": "INTEGER",
    "fe_ppb": "REAL",
    "fe_delta_hz": "REAL",
    "fe_avg_hz": "REAL",
    "fe_min_hz": "REAL",
    "fe_max_hz": "REAL",
    "fe_stability_rms_hz": "REAL",
}

def parse_value(v: str):
    v = v.strip()
    if v == "":
        return None
    if v.lower() in ("true", "false"):
        return 1 if v.lower() == "true" else 0
    try:
        if "." in v or "e" in v.lower():
            return float(v)
        return int(v)
    except ValueError:
        return v

def parse_packet(line: str):
    out = {}
    for item in line.strip().split(","):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        out[k.strip()] = parse_value(v)
    return out

def sample_is_reasonable(sample: dict):
    err_ns = sample.get("err_ns")
    period_ns = sample.get("period_ns")
    tracking = sample.get("tracking")
    state = sample.get("state")
    pps_ok = sample.get("pps_ok")

    try:
        if err_ns is None or abs(float(err_ns)) > MAX_ABS_ERR_NS:
            return False
    except Exception:
        return False

    try:
        if period_ns is None:
            return False
        p = float(period_ns)
        if p < MIN_PERIOD_NS or p > MAX_PERIOD_NS:
            return False
    except Exception:
        return False

    if pps_ok in (0, False):
        return False

    if tracking in (0, False, None):
        if not (isinstance(state, str) and state == "TRACKING"):
            return False

    return True

def ensure_columns(conn: sqlite3.Connection, table: str, required: dict):
    cur = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    for col, coltype in required.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
    conn.commit()

def init_db(conn: sqlite3.Connection):
    conn.executescript(SCHEMA)
    conn.executescript(LATEST_SCHEMA)
    ensure_columns(conn, "samples", MIGRATION_COLUMNS)
    ensure_columns(conn, "latest_state", MIGRATION_COLUMNS)
    conn.commit()

def insert_sample(conn: sqlite3.Connection, sample: dict):
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    row = {field: sample.get(field) for field in FIELDS}
    row["repo_version"] = REPO_VERSION
    row["timestamp_utc"] = timestamp_utc

    cols = ["timestamp_utc"] + FIELDS + ["repo_version"]
    placeholders = ", ".join("?" for _ in cols)
    values = [row.get(c) for c in cols]

    conn.execute(
        f"INSERT INTO samples ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )

    latest_cols = ["singleton_id", "timestamp_utc"] + FIELDS + ["repo_version"]
    latest_vals = [1, timestamp_utc] + [row.get(c) for c in FIELDS] + [REPO_VERSION]
    latest_placeholders = ", ".join("?" for _ in latest_cols)

    conn.execute(
        f"""
        INSERT INTO latest_state ({', '.join(latest_cols)})
        VALUES ({latest_placeholders})
        ON CONFLICT(singleton_id) DO UPDATE SET
        {', '.join(f"{c}=excluded.{c}" for c in ['timestamp_utc'] + FIELDS + ['repo_version'])}
        """,
        latest_vals,
    )

    conn.commit()

def prune_old_rows(conn: sqlite3.Connection, keep_rows: int = 200000):
    cur = conn.execute("SELECT COUNT(*) FROM samples")
    count = cur.fetchone()[0]
    if count > keep_rows:
        delete_n = count - keep_rows
        conn.execute(
            f"DELETE FROM samples WHERE id IN (SELECT id FROM samples ORDER BY id ASC LIMIT {delete_n})"
        )
        conn.commit()

def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    init_db(conn)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))

    print(f"Collector listening on UDP {UDP_PORT}")
    last_prune = time.time()

    while True:
        data, addr = sock.recvfrom(8192)
        line = data.decode(errors="replace").strip()
        try:
            sample = parse_packet(line)

            if sample_is_reasonable(sample):
                insert_sample(conn, sample)

            if time.time() - last_prune > 300:
                prune_old_rows(conn)
                last_prune = time.time()
        except Exception as e:
            print(f"Parse/store error from {addr}: {e}")
            print(line)

if __name__ == "__main__":
    main()
