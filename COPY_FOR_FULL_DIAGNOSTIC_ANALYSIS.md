# COPY FOR FULL DIAGNOSTIC ANALYSIS

Paste this into a new ChatGPT session when you want full diagnostic analysis or precise code/config changes for my time server.

## What this system is

This is my Raspberry Pi + Teensy time server / timing analysis system.

## Primary design intent

- ZED-F9T is the primary GNSS/timing truth source
- ZED PPS is the primary PPS source
- ZED PPS feeds both Raspberry Pi and Teensy
- Raspberry Pi runs chrony and serves NTP
- Teensy is the timing measurement / analytics engine
- Piksi is retained only as a PPS comparison reference
- Piksi is **NOT** the GNSS truth source
- FE-5680A is planned for later holdover / discipline work

## Current architecture

### Timing path

- ZED-F9T PPS -> Raspberry Pi PPS input -> chrony -> NTP
- ZED-F9T PPS -> Teensy
- Piksi PPS -> Teensy comparison input

### Data path

- ZED USB -> Raspberry Pi
- Raspberry Pi `zed-monitor` -> `/home/pi/timing/zed_status.json`
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

## Important directory structure

```text
/home/pi/
├── teensy_dash2/
│   ├── app.py
│   ├── static/
│   │   └── app.js
│   └── templates/
│       └── index.html
├── teensy_appliance/
│   ├── collector.py
│   └── teensy_stats.db
├── timing/
│   └── zed_status.json
└── time-server/
    ├── pi/
    │   ├── teensy_dash2/
    │   │   ├── app.py
    │   │   ├── static/
    │   │   │   └── app.js
    │   │   └── templates/
    │   │       └── index.html
    │   ├── teensy_appliance/
    │   │   └── collector.py
    │   ├── send_zed_to_teensy.py
    │   └── timing/
    │       ├── send_timing_report.sh
    │       └── plot_timing_report.py
    ├── monitoring/
    │   └── zed_monitor.py
    ├── rebuild/
    │   └── dump_state.sh
    └── system_config/
        └── STATE_SNAPSHOT.txt
