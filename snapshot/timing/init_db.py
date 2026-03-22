import sqlite3

db = sqlite3.connect("timing.db")
c = db.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS timing_data (
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
