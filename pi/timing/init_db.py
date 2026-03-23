from pathlib import Path
import sys

REPO_ROOT = "/home/pi/time-server"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pi.utils.version import get_version
REPO_VERSION = get_version()

import sqlite3
from pi.utils.version import get_version

db = sqlite3.connect("timing.db")
c = db.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS timing_data (
            repo_version TEXT,

    timestamp TEXT,
    system_offset REAL,
    rms_offset REAL,
    frequency REAL,
    skew REAL
)
""")

db.commit()
db.close()

print("Timing database initialized.")
