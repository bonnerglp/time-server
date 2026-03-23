#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta, UTC

DB = "/home/pi/timing/timing.db"

# Keep high-rate raw samples for this many days
RAW_KEEP_DAYS = 14

# Keep 10-minute summaries for this many days
AVG_KEEP_DAYS = 3650   # about 10 years

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    raw_cutoff = (datetime.now(UTC) - timedelta(days=RAW_KEEP_DAYS)).isoformat()
    avg_cutoff = (datetime.now(UTC) - timedelta(days=AVG_KEEP_DAYS)).isoformat()

    cur.execute("DELETE FROM teensy_telemetry WHERE timestamp < ?", (raw_cutoff,))
    raw_deleted = cur.rowcount

    cur.execute("DELETE FROM timing_10min WHERE bucket_start < ?", (avg_cutoff,))
    avg_deleted = cur.rowcount

    conn.commit()

    cur.execute("VACUUM")
    conn.commit()

    print(f"Deleted {raw_deleted} raw rows older than {raw_cutoff}")
    print(f"Deleted {avg_deleted} 10-minute rows older than {avg_cutoff}")

if __name__ == "__main__":
    main()
