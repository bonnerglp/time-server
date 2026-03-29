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
```

## Database

- Main DB: `/home/pi/teensy_appliance/teensy_stats.db`

### Main table/state of interest

- `latest_state`
- `samples`

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

Important fields expected in DB / API pipeline:

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

## Dashboard API routes currently in use

- `/api/latest`
- `/api/history`
- `/api/allan`
- `/api/histogram`
- `/api/frequency`
- `/api/holdover`
- `/api/live_stats`
- `/api/raw/latest`
- `/api/zed_status`

**Note:** `/api/live` is **not** the correct endpoint on this build.

## Dashboard design intent

The dashboard should show:

- GNSS health from ZED-driven DB values
- timing quality from Teensy-driven DB values
- PPS comparison between Piksi and ZED
- no duplicate GNSS panels
- no mixed-source confusion
- cards and graphs should reflect the DB pipeline, not stale side channels

## Current dashboard behavior that should be preserved

### Timing summary / calibration

The dashboard now has a dedicated top timing summary group emphasizing corrected timing, not just raw offset.

Important interpretation:

- raw phase error may sit around roughly `-3 us`
- that raw offset is expected to be learned out by auto-cal
- the meaningful corrected value is the calibrated phase error / residual

### Auto-cal behavior

Backend computes:

- `auto_cal_state`
- `auto_cal_ns`
- `auto_calibrated_phase_ns`
- `auto_cal_rms_ns`
- `auto_cal_samples`
- `auto_cal_valid`

Interpretation:

- `auto_cal_state = VALID` means bias learning has converged
- corrected phase can be near `0 ns` even while raw phase remains around `-3 us`

### Current preferred top timing summary emphasis

Top summary should emphasize things like:

- `Calibrated phase err ns`
- `10m RMS jitter ns`
- `Raw phase err ns`
- `Phase bias ns`
- `Auto-cal state`
- `Piksi-ZED RMS ns`

### Narrative Analysis panel

The dashboard now includes a rule-based **Narrative Analysis** panel.

It should remain:

- deterministic and rule-based, not freeform AI text
- driven from the same fetched dashboard values
- based on:
  - overall status
  - timing
  - bias correction
  - reference comparison
  - GNSS
  - holdover

### GNSS chart behavior

The **GNSS / Front End** chart now should show a native dashboard version of the email-style GNSS plot:

- `sats`
- `sats_visible`
- `pdop`

Important:

- PDOP must be shown on its own meaningful scale
- a dual-axis style is preferred so PDOP is not visually crushed by satellite counts

### Allan deviation chart behavior

The Allan chart is dashboard-native and should remain sourced from `/api/allan`.

Preferred behavior:

- actual tau scaling on x-axis
- useful ADEV scaling on y-axis
- faint horizontal grid lines
- readable log/log interpretation

### PPS comparison chart behavior

The PPS comparison chart should be readable and must not be dominated by bogus sentinel values.

Important:

- backend and/or frontend should sanitize absurd `piksi_minus_zed_ns` values
- impossible values like huge negative sentinels should be filtered out
- chart should show the real comparison band, typically:
  - mean in the few hundred ns
  - RMS in the tens of ns
  - min/max in the few hundred ns range

## Known good healthy system behavior

When healthy, I expect to see:

- `state = TRACKING`
- `ZED_OK = 1`
- `PPS_OK = 1`
- `fix_type = 3D`
- sats used and sats visible populated
- PDOP around `~1` in good conditions
- Piksi minus ZED around a few hundred ns
- Piksi minus ZED RMS in tens of ns
- ZED constellation counts populated
- dashboard cards consistent with DB values
- auto-cal state becomes `VALID`
- calibrated phase error near zero or tens of ns
- 10-minute RMS jitter as the best single overall timing-quality number

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
```

Typical git workflow:

```bash
cd ~/time-server
git add .
git commit -m "Describe change"
git push
```

## Important practical notes for future chats

- If dashboard numbers look contradictory, check whether the view is showing **raw** phase or **calibrated** phase
- Do not mistake raw phase offset for corrected timing error
- If a plot looks wrong, verify whether the issue is:
  - bad scaling
  - stale browser JS cache
  - invalid/sentinel values not filtered
  - wrong API endpoint
- Prefer improving backend sanitation when data contains bogus values, while keeping frontend defensive rendering too
