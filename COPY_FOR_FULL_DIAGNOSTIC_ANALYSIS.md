# COPY FOR FULL DIAGNOSTIC ANALYSIS

Paste this into a new ChatGPT session when you want full diagnostic analysis or precise code/config changes for my time server.

## What this system is

This is my Raspberry Pi + Teensy time server / timing analysis system.

Primary design intent:

- ZED-F9T is the primary GNSS/timing truth source
- ZED PPS is the primary PPS source
- ZED PPS feeds both Raspberry Pi and Teensy
- Raspberry Pi runs chrony and serves NTP
- Teensy is the timing measurement / analytics engine
- Piksi is retained only as a PPS comparison reference
- Piksi is NOT the GNSS truth source
- FE-5680A is planned for later holdover / discipline work

## Current architecture

### Timing path
- ZED-F9T PPS -> Raspberry Pi PPS input -> chrony -> NTP
- ZED-F9T PPS -> Teensy
- Piksi PPS -> Teensy comparison input

### Data path
- ZED USB -> Raspberry Pi
- Raspberry Pi zed-monitor -> `/home/pi/timing/zed_status.json`
- Raspberry Pi `send_zed_to_teensy.py` -> UDP bridge -> Teensy
- Teensy -> UDP telemetry -> Raspberry Pi collector
- Collector -> SQLite database
- Dashboard -> reads SQLite database

## Source-of-truth rules

These are critical and should not be violated unless I explicitly ask:

- ZED is the single GNSS truth source
- Teensy is the timing measurement source
- Piksi is only a PPS comparison reference
- Dashboard should prefer DB-driven values
- Avoid mixed-source GNSS telemetry
- Do not reintroduce direct Piksi GNSS telemetry into the dashboard
- Always confirm live runtime paths before editing files

## Important runtime paths

### Live dashboard files
- `/home/pi/teensy_dash2/app.py`
- `/home/pi/teensy_dash2/static/app.js`
- `/home/pi/teensy_dash2/templates/index.html`

### Live collector
- `/home/pi/teensy_appliance/collector.py`

### Repo copies
- `/home/pi/time-server/pi/teensy_dash2/app.py`
- `/home/pi/time-server/pi/teensy_dash2/static/app.js`
- `/home/pi/time-server/pi/teensy_dash2/templates/index.html`
- `/home/pi/time-server/pi/teensy_appliance/collector.py`

### Bridge / monitor / snapshot
- `/home/pi/time-server/pi/send_zed_to_teensy.py`
- `/home/pi/time-server/monitoring/zed_monitor.py`
- `/home/pi/time-server/rebuild/dump_state.sh`
- `/home/pi/time-server/system_config/STATE_SNAPSHOT.txt`

### Database
- `/home/pi/teensy_appliance/teensy_stats.db`

## Important services

These services matter to current operation:

- `chrony.service`
- `zed-monitor.service`
- `zed-to-teensy.service`
- `teensy-collector.service`
- `teensy-dash2.service`
- `zed-splitter.service`
- `gpsd-direct.service`
- `ser2net.service`

## Database expectations

Main DB:
- `/home/pi/teensy_appliance/teensy_stats.db`

Main table/state of interest:
- `latest_state`
- `samples`

Important fields expected in DB:

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
- `period_ns`
- `err_ns`
- `rms_ns`
- `piksi_minus_zed_ns`
- `piksi_minus_zed_rms_ns`
- `piksi_minus_zed_valid`
- `piksi_minus_zed_rejected`
- `piksi_minus_zed_min_ns`
- `piksi_minus_zed_max_ns`

## Dashboard design intent

The dashboard should show:

- GNSS health from ZED-driven DB values
- timing quality from Teensy-driven DB values
- PPS comparison between Piksi and ZED
- no duplicate GNSS panels
- no mixed-source confusion
- cards and graphs should reflect the DB pipeline, not stale side channels

## Known good healthy system behavior

When healthy, I expect to see:

- `state = TRACKING`
- `ZED_OK = 1`
- `PPS_OK = 1`
- `fix_type = 3D`
- sats used and sats visible populated
- PDOP around ~1 in good conditions
- Piksi minus ZED around a few hundred ns
- Piksi minus ZED RMS in tens of ns
- ZED constellation counts populated
- dashboard cards consistent with DB values

## Important workflow rules for edits

Always assume there may be a difference between:

- live runtime copy
- repo copy

Preferred workflow:

1. confirm live file path from systemd or runtime usage
2. edit live file if immediate runtime change is needed
3. copy live file back into repo path
4. regenerate snapshot
5. commit and push

## Snapshot / git workflow

Refresh snapshot with:

```bash
~/time-server/rebuild/dump_state.sh > ~/time-server/system_config/STATE_SNAPSHOT.txt
