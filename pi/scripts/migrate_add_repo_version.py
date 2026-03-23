#!/usr/bin/env python3
from pathlib import Path

from pi.utils.db_versioning import ensure_db_versioning

TARGETS = [
    (Path("/home/pi/timing/timing.db"), ["timing_data", "timing_10min", "piksi_events"]),
    (Path("/home/pi/teensy_appliance/teensy_stats.db"), ["samples", "latest_state"]),
]

for db_path, tables in TARGETS:
    if not db_path.exists():
        print(f"SKIP missing: {db_path}")
        continue
    ensure_db_versioning(db_path, tables, note="migration")
    print(f"UPDATED: {db_path}")
