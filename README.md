# time-server

Raspberry Pi time server project with Chrony, PPS, Teensy telemetry collection, dashboard, logging, daily reporting, and backup automation.

## Current baseline
- Chrony with PPS selected as primary time reference
- Teensy telemetry collector service
- Teensy dashboard 2 service on port 8082
- Teensy logger service
- Piksi monitor service
- Cron-based aggregation, plotting, pruning, backup, and email reporting

## Repository structure
- `snapshot/` = baseline capture of the currently working system
- `snapshot/systemd/` = active service files
- `snapshot/chrony/` = chrony configuration
- `snapshot/scripts/` = key support scripts
- `snapshot/timing/` = timing/reporting source code
- `snapshot/teensy_appliance/` = telemetry collector/dashboard source
- `snapshot/teensy_dash2/` = active dashboard source

## Notes
This repository currently stores source/configuration snapshots, not runtime databases, logs, plots, or virtual environments.
