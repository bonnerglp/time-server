# time-server

Raspberry Pi time server project with Chrony, PPS, Teensy telemetry collection, dashboard, logging, daily reporting, and backup automation.

## Hardware

- Raspberry Pi 5
- Teensy
- SparkFun GNSS ZED-F9T
- Swift Piksi
- FE-5680A rubidium standard
- TimeHAT
- Cisco IE-2000-4TS-B

## Current baseline

- Chrony is currently operating in a **stable PPS-only configuration**
- PPS is selected as the active Chrony reference source
- Raspberry Pi is serving as a **stratum 1** time server when healthy
- ZED-F9T is the primary GNSS/timing truth source
- ZED PPS feeds both Raspberry Pi and Teensy
- Teensy is the timing measurement and telemetry engine
- Piksi is retained only as a PPS comparison reference
- Dashboard ZED/GNSS data is restored through `gpsd-direct.service` and `zed-monitor.service`
- Teensy telemetry collector service is active
- Teensy Dashboard 2 service runs on port `8082`
- Teensy logger service is active
- Cron-based aggregation, plotting, pruning, backup, and email reporting are in place

CURRENT STABLE BASELINE AFTER RECOVERY
This is the current known-good operational state and should be treated as the rollback-safe baseline unless I explicitly choose to resume Chrony coarse-time engineering.

Chrony / NTP state
chrony is currently operating in a PPS-only configuration for stable production use
chrony is selecting PPS as the reference source
Raspberry Pi is back at stratum 1 when healthy
chrony may briefly show unsynchronised or a network source immediately after restart, then reacquire PPS after a short settling period
Current stable chrony intent is operational reliability, not coarse-time experimentation

Important chrony note
The original paired configuration using a coarse GNSS source plus PPS was broken because the coarse-time feed into chrony was not being populated in a usable way
For now, the stable operational choice is PPS-only chrony
Do not casually reintroduce lock NMEA / SHM / SOCK refclock edits unless specifically working on the coarse-time project

Current PPS-only chrony is an operational baseline, not the final architecture; FE and TimeHAT code should be written as additive subsystems that preserve a smooth path to later integrated timing modes.

## Current operational note

The current safe rollback baseline is:

- **Chrony PPS-only stable**
- **Dashboard GNSS/ZED feed restored**
- **ZED coarse-time integration for Chrony is still under development**

At present, the production-stable timing path is PPS-only in Chrony.  
The attempted paired **PPS + ZED coarse-time** Chrony configuration is not yet the current baseline and should be treated as an engineering workstream, not the default runtime configuration.

## Architecture summary

### Timing path

- ZED-F9T PPS -> Raspberry Pi PPS input -> Chrony -> NTP service
- ZED-F9T PPS -> Teensy
- Piksi PPS -> Teensy comparison input

### Data path

- ZED USB -> Raspberry Pi
- `zed-monitor` -> `/home/pi/timing/zed_status.json`
- `send_zed_to_teensy.py` -> UDP bridge -> Teensy
- Teensy -> UDP telemetry -> collector
- Collector -> SQLite database
- Dashboard -> reads SQLite-backed API data

## Source-of-truth rules

- ZED is the single GNSS truth source
- Teensy is the timing measurement source
- Piksi is only a PPS comparison reference
- Dashboard should prefer DB-driven values
- Avoid mixed-source GNSS telemetry
- Do not reintroduce direct Piksi GNSS telemetry into the dashboard

## Repository structure

- `snapshot/` = baseline capture of the currently working system
- `snapshot/systemd/` = active service files
- `snapshot/chrony/` = Chrony configuration
- `snapshot/scripts/` = key support scripts
- `snapshot/timing/` = timing/reporting source code
- `snapshot/teensy_appliance/` = telemetry collector/dashboard source
- `snapshot/teensy_dash2/` = active dashboard source

## Important services

- `chrony.service`
- `zed-monitor.service`
- `gpsd-direct.service`
- `zed-splitter.service`
- `zed-to-teensy.service`
- `teensy-collector.service`
- `teensy-dash2.service`
- `teensy_logger.service`
- `ser2net.service`

## Notes

- This repository stores source/configuration snapshots, not runtime databases, logs, plots, or virtual environments.
- Always confirm live runtime paths before editing files.
- There may be differences between live runtime files and repo copies.
- Preferred workflow is:
  1. confirm live file path from systemd/runtime usage
  2. edit live file if an immediate runtime change is needed
  3. copy the live file back into the repo path
  4. regenerate the snapshot
  5. commit and push

## Snapshot refresh

```bash
~/time-server/rebuild/dump_state.sh > ~/time-server/system_config/STATE_SNAPSHOT.txt
