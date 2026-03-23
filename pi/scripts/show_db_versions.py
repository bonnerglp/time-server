#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DBS = [
    Path("/home/pi/timing/timing.db"),
    Path("/home/pi/teensy_appliance/teensy_stats.db"),
]

for db in DBS:
    print(f"\n=== {db} ===")
    if not db.exists():
        print("missing")
        continue
    conn = sqlite3.connect(db)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
        print("tables:", ", ".join(tables))
        for t in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
            if "repo_version" in cols:
                row = conn.execute(
                    f"SELECT repo_version, COUNT(*) FROM {t} "
                    f"WHERE repo_version IS NOT NULL AND TRIM(repo_version) <> '' "
                    f"GROUP BY repo_version ORDER BY COUNT(*) DESC LIMIT 5"
                ).fetchall()
                print(f"\nTable: {t}")
                print("repo_version column: yes")
                if row:
                    for version, count in row:
                        print(f"  {version} -> {count} rows")
                else:
                    print("  no populated repo_version rows yet")
        if "repo_metadata" in tables:
            rows = conn.execute(
                "SELECT recorded_at, repo_version, note "
                "FROM repo_metadata ORDER BY id DESC LIMIT 5"
            ).fetchall()
            print("\nRecent repo_metadata:")
            for r in rows:
                print(f"  {r[0]} | {r[1]} | {r[2]}")
    finally:
        conn.close()
