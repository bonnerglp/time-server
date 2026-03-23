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
    pps INTEGER,
    state TEXT,
    pps_ok INTEGER,
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
    pdop REAL,
    cn0_avg REAL,
    fix_type TEXT,
    fe_mode TEXT,
    fe_control REAL,
    fe_phase_ns REAL,
    fe_holdover INTEGER
);

CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON samples(timestamp_utc);
"""

LATEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS latest_state (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    timestamp_utc TEXT NOT NULL,
    pps INTEGER,
    state TEXT,
    pps_ok INTEGER,
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
    pdop REAL,
    cn0_avg REAL,
    fix_type TEXT,
    fe_mode TEXT,
    fe_control REAL,
    fe_phase_ns REAL,
    fe_holdover INTEGER
);
"""

FIELDS = [
    "pps", "state", "pps_ok", "tcp_ok", "utc_ok", "gps_ok", "tracking",
    "period_ns", "err_ns", "rms_ns", "min_err_ns", "max_err_ns",
    "tcp_bytes", "sbp_frames", "crc_err",
    "gps_week", "gps_tow_ms", "gps_ns_res",
    "utc", "utc_ns", "utc_flags",
    "sats", "pdop", "cn0_avg", "fix_type",
    "fe_mode", "fe_control", "fe_phase_ns", "fe_holdover"
]

MAX_ABS_ERR_NS = 100000          # 100 us
MIN_PERIOD_NS = 900_000_000
MAX_PERIOD_NS = 1_100_000_000

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
    utc_ok = sample.get("utc_ok")
    gps_ok = sample.get("gps_ok")
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

    if tracking in (0, False) or utc_ok in (0, False) or gps_ok in (0, False) or pps_ok in (0, False):
        return False

    return True

def init_db(conn: sqlite3.Connection):
    conn.executescript(SCHEMA)
    conn.executescript(LATEST_SCHEMA)
    conn.commit()

def insert_sample(conn: sqlite3.Connection, sample: dict):
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    row = {field: sample.get(field) for field in FIELDS}
    row["timestamp_utc"] = timestamp_utc

    cols = ["timestamp_utc"] + FIELDS
    placeholders = ", ".join("?" for _ in cols)
    values = [row.get(c) for c in cols]

    conn.execute(
        f"INSERT INTO samples ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )

    latest_cols = ["singleton_id", "timestamp_utc"] + FIELDS
    latest_vals = [1, timestamp_utc] + [row.get(c) for c in FIELDS]
    latest_placeholders = ", ".join("?" for _ in latest_cols)

    conn.execute(
        f"""
        INSERT INTO latest_state ({', '.join(latest_cols)})
        VALUES ({latest_placeholders})
        ON CONFLICT(singleton_id) DO UPDATE SET
        {', '.join(f"{c}=excluded.{c}" for c in ['timestamp_utc'] + FIELDS)}
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
