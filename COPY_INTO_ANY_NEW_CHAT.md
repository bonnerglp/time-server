# COPY INTO ANY NEW CHAT

Use this as the starting context for any new ChatGPT session working on my time server.

## Project identity

This is my Raspberry Pi / Teensy time server project.

Current architecture is:

- ZED-F9T is the primary GNSS/timing source
- ZED PPS feeds Raspberry Pi and Teensy
- ZED USB feeds Raspberry Pi
- Raspberry Pi runs chrony and serves NTP
- Teensy is the timing measurement / analytics engine
- Piksi is retained only as a PPS comparison reference
- FE-5680A is planned for later holdover / discipline phase

## Current signal/data flow

- ZED-F9T PPS -> Raspberry Pi PPS input -> chrony -> NTP service
- ZED-F9T PPS -> Teensy PPS input
- Piksi PPS -> Teensy comparison PPS input
- ZED USB -> Raspberry Pi
- Raspberry Pi zed-monitor -> zed_status.json
- Raspberry Pi send_zed_to_teensy.py -> UDP telemetry bridge to Teensy
- Teensy -> UDP telemetry -> Raspberry Pi collector -> SQLite DB
- Dashboard reads from SQLite DB

## Source-of-truth rules

These are critical:

- ZED is the single GNSS truth source
- Teensy is the PPS measurement / comparison source
- Piksi is only a PPS comparison reference, not GNSS truth
- Dashboard should use DB-driven values, not mixed direct JSON values, unless explicitly intended
- Repo copy and live runtime copy are sometimes different; always check which path systemd is using before editing

## Important live/runtime paths

### Dashboard live files
- `/home/pi/teensy_dash2/app.py`
- `/home/pi/teensy_dash2/static/app.js`
- `/home/pi/teensy_dash2/templates/index.html`

### Collector live file
- `/home/pi/teensy_appliance/collector.py`

### Repo copies
- `/home/pi/time-server/pi/teensy_dash2/app.py`
- `/home/pi/time-server/pi/teensy_dash2/static/app.js`
- `/home/pi/time-server/pi/teensy_dash2/templates/index.html`
- `/home/pi/time-server/pi/teensy_appliance/collector.py`

### Bridge / monitor / snapshot files
- `/home/pi/time-server/pi/send_zed_to_teensy.py`
- `/home/pi/time-server/monitoring/zed_monitor.py`
- `/home/pi/time-server/rebuild/dump_state.sh`
- `/home/pi/time-server/system_config/STATE_SNAPSHOT.txt`

## Service model

Important services in this system:

- `chrony.service`
- `zed-monitor.service`
- `zed-to-teensy.service`
- `teensy-collector.service`
- `teensy-dash2.service`
- `zed-splitter.service`
- `gpsd-direct.service`
- `ser2net.service`

## Database

Primary live database:

- `/home/pi/teensy_appliance/teensy_stats.db`

Key table:

- `latest_state`

Important fields that should exist and be used correctly:

- `sats`
- `sats_visible`
- `fix_type`
- `pdop`
- `hdop`
- `vdop`
- `cn0_avg`
- `cn0_max`
- `gps_count`
- `gal_count`
- `glo_count`
- `bds_count`
- `qzss_count`
- `zed_status`
- `piksi_minus_zed_ns`
- `piksi_minus_zed_rms_ns`
- `piksi_minus_zed_valid`
- `piksi_minus_zed_rejected`
- `piksi_minus_zed_min_ns`
- `piksi_minus_zed_max_ns`

## Dashboard design intent

The dashboard should show:

- GNSS health from ZED-driven DB values
- timing performance from Teensy-driven DB values
- PPS comparison between Piksi and ZED
- no duplicate or conflicting GNSS panels
- no mixed-source ambiguity

## Current known good behavior

When the system is healthy, I expect to see things like:

- state = TRACKING
- ZED_OK = 1
- PPS_OK = 1
- fix type = 3D
- sats used and sats visible both populated
- PDOP around ~1 in good conditions
- Piksi minus ZED around a few hundred ns
- Piksi minus ZED RMS in tens of ns

## Workflow rules for edits

When helping me edit this system, always be careful about live vs repo paths.

Preferred workflow:

1. determine live file path from systemd or current runtime use
2. edit the live file if needed for immediate effect
3. copy live file back into repo copy
4. regenerate snapshot
5. commit and push

## Snapshot / git workflow

Refresh snapshot with:

```bash
~/time-server/rebuild/dump_state.sh > ~/time-server/system_config/STATE_SNAPSHOT.txt
