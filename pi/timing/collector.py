#!/usr/bin/env python3
import sqlite3
import subprocess
import time
import re
from datetime import datetime, UTC
from pathlib import Path

DB_PATH = Path.home() / "timing" / "timing.db"

SYSTEM_TIME_RE = re.compile(r"System time\s*:\s*([+-]?\d+(?:\.\d+)?)\s*seconds\s*(fast|slow)")
RMS_OFFSET_RE = re.compile(r"RMS offset\s*:\s*([+-]?\d+(?:\.\d+)?)\s*seconds")
FREQUENCY_RE = re.compile(r"Frequency\s*:\s*([+-]?\d+(?:\.\d+)?)\s*ppm")
SKEW_RE = re.compile(r"Skew\s*:\s*([+-]?\d+(?:\.\d+)?)\s*ppm")


def parse_tracking():
    out = subprocess.check_output(["chronyc", "tracking"], text=True, stderr=subprocess.STDOUT)

    system_offset_ns = None
    rms_offset_ns = None
    frequency_ppm = None
    skew_ppm = None

    for line in out.splitlines():
        m = SYSTEM_TIME_RE.search(line)
        if m:
            val_s = float(m.group(1))
            direction = m.group(2)
            if direction == "slow":
                val_s = -val_s
            system_offset_ns = val_s * 1e9

        m = RMS_OFFSET_RE.search(line)
        if m:
            rms_offset_ns = float(m.group(1)) * 1e9

        m = FREQUENCY_RE.search(line)
        if m:
            frequency_ppm = float(m.group(1))

        m = SKEW_RE.search(line)
        if m:
            skew_ppm = float(m.group(1))

    return system_offset_ns, rms_offset_ns, frequency_ppm, skew_ppm


def main():
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()

    while True:
        try:
            timestamp = datetime.now(UTC).isoformat()
            system_offset_ns, rms_offset_ns, frequency_ppm, skew_ppm = parse_tracking()

            c.execute(
                "INSERT INTO timing_data VALUES (?,?,?,?,?)",
                (timestamp, system_offset_ns, rms_offset_ns, frequency_ppm, skew_ppm),
            )
            db.commit()

            print(
                f"{timestamp}  offset_ns={system_offset_ns:.1f}  "
                f"rms_ns={rms_offset_ns:.1f}  freq_ppm={frequency_ppm:.3f}  skew_ppm={skew_ppm:.3f}"
            )

        except Exception as e:
            print("error:", e)

        time.sleep(60)


if __name__ == "__main__":
    main()
