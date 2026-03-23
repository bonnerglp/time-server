# VERSION_HELPER_AVAILABLE
#!/usr/bin/env python3
import json
import sqlite3
import time
import urllib.request
from datetime import datetime, UTC

BASE = "http://127.0.0.1:8082"
DB = "/home/pi/timing/timing.db"
POLL_SECONDS = 2


def fetch_json(path: str):
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        return json.loads(r.read().decode())


def b(v):
    if v is None:
        return None
    return 1 if bool(v) else 0


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    while True:
        try:
            latest = fetch_json("/api/latest")
            live = fetch_json("/api/live_stats")
            hold = fetch_json("/api/holdover")

            ts = datetime.now(UTC).isoformat()

            cur.execute("""
                INSERT INTO teensy_telemetry (
                    timestamp,
                    online, state, utc, utc_ns, utc_flags, pps, pps_ok, tcp_ok, utc_ok, gps_ok,
                    tracking, gps_week, gps_tow_ms, gps_ns_res,
                    current_phase_err_ns, rms_60s_ns, rms_10m_ns, p2p_60s_ns, adev_1s,
                    period_ns, err_ns, rms_ns, min_err_ns, max_err_ns,
                    tcp_bytes, sbp_frames, crc_err, sats, pdop, cn0_avg,
                    fix_type, fe_mode, fe_control, fe_phase_ns, fe_holdover,
                    age_s, holdover_slope_ns_per_s, predicted_drift_1h_ns
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                ts,
                b(latest.get("online")),
                latest.get("state"),
                latest.get("utc"),
                latest.get("utc_ns"),
                latest.get("utc_flags"),
                latest.get("pps"),
                b(latest.get("pps_ok")),
                b(latest.get("tcp_ok")),
                b(latest.get("utc_ok")),
                b(latest.get("gps_ok")),
                b(latest.get("tracking")),
                latest.get("gps_week"),
                latest.get("gps_tow_ms"),
                latest.get("gps_ns_res"),
                live.get("current_phase_err_ns"),
                live.get("rms_60s_ns"),
                live.get("rms_10m_ns"),
                live.get("p2p_60s_ns"),
                live.get("adev_1s"),
                latest.get("period_ns"),
                latest.get("err_ns"),
                latest.get("rms_ns"),
                latest.get("min_err_ns"),
                latest.get("max_err_ns"),
                latest.get("tcp_bytes"),
                latest.get("sbp_frames"),
                latest.get("crc_err"),
                latest.get("sats"),
                latest.get("pdop"),
                latest.get("cn0_avg"),
                latest.get("fix_type"),
                latest.get("fe_mode"),
                latest.get("fe_control"),
                latest.get("fe_phase_ns"),
                b(latest.get("fe_holdover")),
                latest.get("age_s"),
                hold.get("slope_ns_per_s"),
                hold.get("drift_1h_ns"),
            ))
            conn.commit()

            print(
                f"{ts}  phase={live.get('current_phase_err_ns')} ns  "
                f"rms60={live.get('rms_60s_ns')}  sats={latest.get('sats')}  "
                f"pdop={latest.get('pdop')}"
            )

        except Exception as e:
            print("error:", e)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
