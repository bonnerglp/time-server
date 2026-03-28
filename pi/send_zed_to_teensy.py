#!/usr/bin/env python3
import json
import socket
import time
from pathlib import Path

TEENSY_IP = "10.0.0.116"
TEENSY_PORT = 55557
ZED_STATUS_PATH = Path("/home/pi/timing/zed_status.json")
SEND_INTERVAL_S = 1.0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def load_zed_status():
    with ZED_STATUS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def clean_value(v):
    if v is None:
        return ""
    return str(v)

def build_packet(z):
    fields = {
        "src": "zed",
        "ts_utc": z.get("ts_utc", ""),
        "gps_time_utc": z.get("gps_time_utc", ""),
        "fix_type": z.get("fix_type", ""),
        "sats_used": z.get("sats_used", 0),
        "sats_visible": z.get("sats_visible", 0),
        "pdop": z.get("pdop", 0.0),
        "hdop": z.get("hdop", 0.0),
        "vdop": z.get("vdop", 0.0),
        "avg_cn0": z.get("avg_cn0", 0.0),
        "max_cn0": z.get("max_cn0", 0.0),
        "gps_count": z.get("gps_count", 0),
        "gal_count": z.get("gal_count", 0),
        "glo_count": z.get("glo_count", 0),
        "bds_count": z.get("bds_count", 0),
        "qzss_count": z.get("qzss_count", 0),
        "status": z.get("status", ""),
    }
    return ",".join(f"{k}={clean_value(v)}" for k, v in fields.items())

def main():
    print(f"Sending ZED status to {TEENSY_IP}:{TEENSY_PORT}")
    while True:
        try:
            z = load_zed_status()
            payload = build_packet(z).encode("utf-8")
            sock.sendto(payload, (TEENSY_IP, TEENSY_PORT))
        except Exception as e:
            print(f"send_zed_to_teensy error: {e}")
        time.sleep(SEND_INTERVAL_S)

if __name__ == "__main__":
    main()
