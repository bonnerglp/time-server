#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta, UTC
from math import sqrt

DB = "/home/pi/timing/timing.db"

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    now = datetime.now(UTC).replace(second=0, microsecond=0)
    bucket_end = now - timedelta(minutes=now.minute % 10)
    bucket_start = bucket_end - timedelta(minutes=10)

    cur.execute("""
        SELECT
            AVG(current_phase_err_ns),
            AVG(current_phase_err_ns * current_phase_err_ns),
            AVG(rms_60s_ns),
            AVG(adev_1s),
            AVG(sats),
            AVG(pdop),
            COUNT(*)
        FROM teensy_telemetry
        WHERE timestamp >= ? AND timestamp < ?
    """, (bucket_start.isoformat(), bucket_end.isoformat()))

    row = cur.fetchone()
    if not row or row[6] == 0:
        print("No samples in bucket", bucket_start.isoformat(), "to", bucket_end.isoformat())
        return

    avg_phase = row[0]
    avg_square = row[1]
    avg_rms60 = row[2]
    avg_adev = row[3]
    avg_sats = row[4]
    avg_pdop = row[5]
    samples = row[6]

    variance = avg_square - (avg_phase * avg_phase)
    if variance < 0:
        variance = 0.0
    rms_phase = sqrt(variance)

    cur.execute("DELETE FROM timing_10min WHERE bucket_start = ?", (bucket_start.isoformat(),))
    cur.execute("""
        INSERT INTO timing_10min (
            bucket_start,
            avg_phase_ns,
            rms_phase_ns,
            avg_rms60_ns,
            avg_adev_1s,
            avg_sats,
            avg_pdop,
            samples
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        bucket_start.isoformat(),
        avg_phase,
        rms_phase,
        avg_rms60,
        avg_adev,
        avg_sats,
        avg_pdop,
        samples
    ))
    conn.commit()

    print(f"Stored 10-minute bucket starting {bucket_start.isoformat()} with {samples} samples")

if __name__ == "__main__":
    main()
