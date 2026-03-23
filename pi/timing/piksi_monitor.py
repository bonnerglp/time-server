# VERSION_HELPER_AVAILABLE
#!/usr/bin/env python3
import os
import socket
import sqlite3
import time
from datetime import datetime, timezone

PIKSI_HOST = os.environ.get("PIKSI_HOST", "10.0.0.243")
PIKSI_PORT = int(os.environ.get("PIKSI_PORT", "55555"))
DB_PATH = "/home/pi/timing/timing.db"
LOG_PATH = "/home/pi/timing/piksi_monitor.log"

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 10
RECONNECT_DELAY = 5
MIN_REBOOT_GAP_SEC = 15

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def log_line(msg):
    line = f"{utc_now()} {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS piksi_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()

def add_event(event_type, detail=""):
    conn = db()
    try:
        conn.execute(
            "INSERT INTO piksi_events (event_time, event_type, detail) VALUES (?, ?, ?)",
            (utc_now(), event_type, detail)
        )
        conn.commit()
    finally:
        conn.close()

def read_last_event(event_type):
    conn = db()
    try:
        cur = conn.execute("""
            SELECT event_time, detail
            FROM piksi_events
            WHERE event_type = ?
            ORDER BY id DESC
            LIMIT 1
        """, (event_type,))
        return cur.fetchone()
    finally:
        conn.close()

def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def extract_possible_boot_markers(text):
    t = text.lower()
    markers = []
    if "boot" in t:
        markers.append("boot")
    if "startup" in t:
        markers.append("startup")
    if "reset" in t:
        markers.append("reset")
    if "acq" in t or "acquiring" in t:
        markers.append("acquiring")
    return ",".join(sorted(set(markers)))

def main():
    init_db()
    log_line(f"Starting Piksi monitor for {PIKSI_HOST}:{PIKSI_PORT}")
    add_event("monitor_started", f"{PIKSI_HOST}:{PIKSI_PORT}")

    connected = False
    loss_time = None
    first_data_after_connect = False
    last_reboot_report_ts = 0.0

    while True:
        sock = None
        try:
            log_line(f"Connecting to {PIKSI_HOST}:{PIKSI_PORT}")
            sock = socket.create_connection((PIKSI_HOST, PIKSI_PORT), timeout=CONNECT_TIMEOUT)
            sock.settimeout(READ_TIMEOUT)

            connected = True
            first_data_after_connect = True
            log_line("Stream connected")
            add_event("stream_connected", f"{PIKSI_HOST}:{PIKSI_PORT}")

            if loss_time is not None:
                outage = time.time() - loss_time
                detail = f"stream restored after {outage:.1f} s"
                add_event("stream_restored", detail)
                log_line(detail)
                if outage >= 2:
                    now_ts = time.time()
                    if now_ts - last_reboot_report_ts >= MIN_REBOOT_GAP_SEC:
                        add_event("piksi_reboot_suspected", f"disconnect/reconnect cycle, outage {outage:.1f} s")
                        log_line(f"Reboot suspected: disconnect/reconnect cycle, outage {outage:.1f} s")
                        last_reboot_report_ts = now_ts
                loss_time = None

            buf = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    raise ConnectionError("socket closed by peer")

                buf += chunk

                if first_data_after_connect:
                    add_event("first_data_after_connect", f"{len(chunk)} bytes")
                    first_data_after_connect = False

                if len(buf) > 32768:
                    buf = buf[-32768:]

                try:
                    text = buf.decode("utf-8", errors="ignore")
                except Exception:
                    text = ""

                markers = extract_possible_boot_markers(text)
                if markers:
                    now_ts = time.time()
                    if now_ts - last_reboot_report_ts >= MIN_REBOOT_GAP_SEC:
                        add_event("piksi_startup_marker", f"markers={markers}")
                        log_line(f"Startup marker detected: {markers}")
                        last_reboot_report_ts = now_ts

        except Exception as e:
            if connected:
                connected = False
                loss_time = time.time()
                add_event("stream_lost", str(e))
                log_line(f"Stream lost: {e}")
            else:
                log_line(f"Connect/read failure: {e}")

            try:
                if sock is not None:
                    sock.close()
            except Exception:
                pass

            time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    main()
