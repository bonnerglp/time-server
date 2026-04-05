COPY FOR FULL DIAGNOSTIC ANALYSIS

Paste this into a new ChatGPT session when you want full diagnostic analysis or precise code/config changes for my time server.

WHAT THIS SYSTEM IS
This is my Raspberry Pi + Teensy time server / timing analysis system.

PRIMARY DESIGN INTENT

ZED-F9T is the primary GNSS/timing truth source
ZED PPS is the primary PPS source
ZED PPS feeds both Raspberry Pi and Teensy
Raspberry Pi runs chrony and serves NTP
Teensy is the timing measurement / analytics engine
Piksi is retained only as a PPS comparison reference
Piksi is NOT the GNSS truth source
FE-5680A is being integrated as an additive frequency / holdover / future discipline subsystem
Do not violate the ZED-first source-of-truth model unless I explicitly ask

CURRENT ARCHITECTURE

Timing path

ZED-F9T PPS -> Raspberry Pi PPS input -> chrony -> NTP
ZED-F9T PPS -> Teensy
Piksi PPS -> Teensy comparison input
FE-5680A 10 MHz sine -> TLV squaring stage -> Teensy pin 9 frequency input

Data path

ZED USB -> Raspberry Pi
Raspberry Pi zed-monitor -> /home/pi/timing/zed_status.json
Raspberry Pi send_zed_to_teensy.py -> UDP bridge -> Teensy
Teensy -> UDP telemetry -> Raspberry Pi collector
Collector -> SQLite database
Dashboard -> reads SQLite database

SOURCE-OF-TRUTH RULES
These are critical and should not be violated unless I explicitly ask:

ZED is the single GNSS truth source
Teensy is the timing measurement source
Piksi is only a PPS comparison reference
Dashboard should prefer DB-driven values
Avoid mixed-source GNSS telemetry
Do not reintroduce direct Piksi GNSS telemetry into the dashboard
Always confirm live runtime paths before editing files

IMPORTANT RUNTIME PATHS

Live dashboard files

/home/pi/teensy_dash2/app.py
/home/pi/teensy_dash2/static/app.js
/home/pi/teensy_dash2/templates/index.html

Live collector

/home/pi/teensy_appliance/collector.py

Repo copies

/home/pi/time-server/pi/teensy_dash2/app.py
/home/pi/time-server/pi/teensy_dash2/static/app.js
/home/pi/time-server/pi/teensy_dash2/templates/index.html
/home/pi/time-server/pi/teensy_appliance/collector.py

Bridge / monitor / snapshot

/home/pi/time-server/pi/send_zed_to_teensy.py
/home/pi/time-server/monitoring/zed_monitor.py
/home/pi/time-server/rebuild/dump_state.sh
/home/pi/time-server/system_config/STATE_SNAPSHOT.txt

IMPORTANT DIRECTORY STRUCTURE
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

DATABASE
Main DB:

/home/pi/teensy_appliance/teensy_stats.db

Main table/state of interest:

latest_state
samples

DATABASE EXPECTATIONS
Important fields expected in DB / API pipeline:

sats
sats_visible
fix_type
pdop
hdop
vdop
cn0_avg
cn0_max
gps_count
gal_count
glo_count
bds_count
qzss_count
zed_status
period_ns
err_ns
rms_ns
piksi_minus_zed_ns
piksi_minus_zed_rms_ns
piksi_minus_zed_valid
piksi_minus_zed_rejected
piksi_minus_zed_min_ns
piksi_minus_zed_max_ns

New active FE fields now in DB / API pipeline:

fe_hz
fe_mhz
fe_valid
fe_sanity_ok
fe_low_hz
fe_high_hz
fe_ppb
fe_delta_hz
fe_avg_hz
fe_min_hz
fe_max_hz
fe_stability_rms_hz

Legacy FE fields may still exist in the DB schema but are not active telemetry in the current FE integration stage:

fe_mode
fe_control
fe_phase_ns
fe_holdover

IMPORTANT SERVICES
These services matter to current operation:

chrony.service
zed-monitor.service
zed-to-teensy.service
teensy-collector.service
teensy-dash2.service
zed-splitter.service
gpsd-direct.service
ser2net.service

DASHBOARD API ROUTES CURRENTLY IN USE

/api/latest
/api/history
/api/allan
/api/histogram
/api/frequency
/api/holdover
/api/live_stats
/api/raw/latest
/api/zed_status

Note:

/api/live is not the correct endpoint on this build

DASHBOARD DESIGN INTENT
The dashboard should show:

GNSS health from ZED-driven DB values
timing quality from Teensy-driven DB values
PPS comparison between Piksi and ZED
FE frequency / stability telemetry as an additive subsystem
no duplicate GNSS panels
no mixed-source confusion
cards and graphs should reflect the DB pipeline, not stale side channels

CURRENT FE INTEGRATION STATUS

FE-5680A 10 MHz is now connected and being measured successfully
FE 10 MHz is squared / conditioned through a TLV stage before Teensy input
Teensy pin 9 is used for FE 10 MHz counting
Teensy uses FreqCount on pin 9 with a 1 second gate on Teensy 4.1
Collector stores FE stability metrics
Dashboard API exposes FE metrics
Dashboard cards now display FE metrics

CURRENT FE METRICS MEANING

Current FE telemetry is frequency / short-term stability telemetry only
It does NOT yet represent phase difference to ZED PPS
It does NOT yet represent UTC error
It does NOT yet represent FE discipline state
It does NOT yet represent FE holdover model quality

Interpretation of current FE fields:

fe_hz = measured 10 MHz count over the gate interval
fe_mhz = same measurement expressed in MHz
fe_valid = FE reading present recently
fe_sanity_ok = FE reading is within the configured sanity window
fe_ppb = instantaneous offset from nominal 10 MHz in ppb based on the gated count
fe_delta_hz = change from previous FE reading
fe_avg_hz = running average FE frequency
fe_min_hz / fe_max_hz = observed bounds over the current accumulation
fe_stability_rms_hz = RMS wander of the gated FE frequency readings

CURRENT DASHBOARD BEHAVIOR THAT SHOULD BE PRESERVED

Timing summary / calibration
The dashboard now has a dedicated top timing summary group emphasizing corrected timing, not just raw offset.

Important interpretation:

raw phase error may sit around roughly -3 us
that raw offset is expected to be learned out by auto-cal
the meaningful corrected value is the calibrated phase error / residual

Auto-cal behavior
Backend computes:

auto_cal_state
auto_cal_ns
auto_calibrated_phase_ns
auto_cal_rms_ns
auto_cal_samples
auto_cal_valid

Interpretation:

auto_cal_state = VALID means bias learning has converged
corrected phase can be near 0 ns even while raw phase remains around -3 us

Current preferred top timing summary emphasis
Top summary should emphasize:

Calibrated phase err ns
10m RMS jitter ns
Raw phase err ns
Phase bias ns
Auto-cal state
Piksi-ZED RMS ns

Narrative Analysis panel
The dashboard includes a rule-based Narrative Analysis panel. It should remain:

deterministic and rule-based
not freeform AI text
driven from the same fetched dashboard values
based on: overall status, timing bias correction, reference comparison, GNSS, holdover

GNSS chart behavior
The GNSS / Front End chart should show a native dashboard version of the email-style GNSS plot:

sats
sats_visible
pdop

Important:

PDOP must be shown on its own meaningful scale
a dual-axis style is preferred so PDOP is not visually crushed by satellite counts

Allan deviation chart behavior
The Allan chart is dashboard-native and should remain sourced from /api/allan.

Preferred behavior:

actual tau scaling on x-axis
useful ADEV scaling on y-axis
faint horizontal grid lines
readable log/log interpretation

PPS comparison chart behavior
The PPS comparison chart should be readable and must not be dominated by bogus sentinel values.

Important:

backend and/or frontend should sanitize absurd piksi_minus_zed_ns values
impossible values like huge negative sentinels should be filtered out
chart should show the real comparison band, typically:
mean in the few hundred ns
RMS in the tens of ns
min/max in the few hundred ns range

CURRENT FE DASHBOARD BEHAVIOR

Dashboard cards now show FE summary values such as:

FE MHz
FE sanity
FE ppb
FE delta Hz
FE avg Hz
FE min Hz
FE max Hz
FE RMS Hz

Legacy FE cards may still exist in the frontend layout if not yet cleaned up:

FE mode
FE control
FE phase ns
FE holdover

These legacy cards are not populated by the current FE telemetry path and may show blank/null.

KNOWN GOOD HEALTHY SYSTEM BEHAVIOR
When healthy, I expect to see:

state = TRACKING
ZED_OK = 1
PPS_OK = 1
fix_type = 3D
sats used and sats visible populated
PDOP around ~1 in good conditions
Piksi minus ZED around a few hundred ns
Piksi minus ZED RMS in tens of ns
ZED constellation counts populated
dashboard cards consistent with DB values
auto-cal state becomes VALID
calibrated phase error near zero or tens of ns
10-minute RMS jitter as the best single overall timing-quality number

For current FE integration stage, healthy FE behavior looks like:

fe_valid = 1
fe_sanity_ok = 1
fe_mhz very near 10.000000
fe_delta_hz small
fe_min_hz / fe_max_hz tightly bounded
fe_stability_rms_hz low and stable
dashboard FE cards consistent with DB / API values

CURRENT STABLE BASELINE AFTER RECOVERY
This is the current known-good operational state and should be treated as the rollback-safe baseline unless I explicitly choose to resume chrony coarse-time engineering.

Chrony / NTP state

chrony is currently operating in a PPS-only configuration for stable production use
chrony is selecting PPS as the reference source
Raspberry Pi is back at stratum 1 when healthy
chrony may briefly show unsynchronised or a network source immediately after restart, then reacquire PPS after a short settling period
current stable chrony intent is operational reliability, not coarse-time experimentation

Important chrony note

the original paired configuration using a coarse GNSS source plus PPS was broken because the coarse-time feed into chrony was not being populated in a usable way
for now, the stable operational choice is PPS-only chrony
do not casually reintroduce lock NMEA / SHM / SOCK refclock edits unless specifically working on the coarse-time project

Current PPS-only chrony is an operational baseline, not the final architecture. FE and TimeHAT code should be written as additive subsystems that preserve a smooth path to later integrated timing modes.

CURRENT DASHBOARD / GNSS MONITOR BASELINE

gpsd-direct.service should be running
zed-monitor.service should be running
zed-splitter.service should be running
zed-monitor should write healthy data to /home/pi/timing/zed_status.json
dashboard GNSS cards should be populated from the restored ZED monitor path

If dashboard GNSS suddenly shows UNKNOWN / NO_DATA / zero satellites, first check:

whether gpsd-direct.service is running
whether zed-monitor.service is running
whether zed_status.json is updating

CURRENT SPLIT-PORT / MONITOR PATH UNDERSTANDING

zed-splitter.service owns the real ZED serial device
gpsd-direct.service consumes the splitter output path for dashboard / zed-monitor purposes
this dashboard / monitor gpsd path is separate from the currently stable chrony PPS-only path
do not assume dashboard gpsd experiments are safe for chrony, or vice versa

IMPORTANT GPSD CONFLICT / RECOVERY NOTE
A known failure mode was confirmed:

stock gpsd.service and gpsd.socket can bind port 2947
that can prevent gpsd-direct.service from starting
when that happens, zed-monitor.service times out
zed_status.json goes stale
dashboard GNSS plots can appear flat or stale even while timing data is still updating

Current intended steady state for this system:

gpsd.service should remain disabled
gpsd.socket should remain disabled
gpsd-direct.service should be the intended gpsd instance for /tmp/zed_gpsd

Important troubleshooting rule:

if dashboard GNSS goes stale, first check for a port 2947 conflict before assuming the DB is broken

STATUS OF ZED COARSE-TIME INTEGRATION PROJECT
Goal remains:

PPS + ZED coarse-time for chrony

That project is NOT yet the current production baseline.

ZED data into gpsd is working for monitor/dashboard use
PPS into chrony is working for time-server use
but the attempted gpsd-to-chrony coarse-time export path did not produce usable chrony coarse-time samples in the tested split-port arrangement

Therefore the system currently remains on PPS-only chrony until coarse-time integration is intentionally resumed.

STATUS OF FE INTEGRATION PROJECT

Current stage completed:

safe FE hardware connection to Teensy achieved
TLV-conditioned FE 10 MHz successfully measured on Teensy pin 9
collector / DB / API / dashboard pipeline updated for FE frequency and stability metrics
dashboard FE cards now visible and working

Current stage NOT yet completed:

FE vs ZED phase comparison
FE-derived PPS comparison path
FE steering / control loop
discipline state machine
holdover estimation based on FE
rubidium control output path
TimeHAT integration

IMPORTANT TROUBLESHOOTING INTERPRETATION

if chrony looks healthy but dashboard GNSS is broken: likely gpsd-direct / zed-monitor path issue
if dashboard GNSS looks healthy but chrony is wrong: likely chrony / PPS / refclock issue
do not assume one automatically proves the other
if FE cards disappear but DB values exist: likely frontend / browser cache / app.js issue
if FE API fields are null in old history rows: likely expected because those samples predate FE collector fields
if FE latest values are null: likely collector / DB / Teensy telemetry issue
if FE sanity fails but FE frequency still exists: likely out-of-window frequency reading rather than missing signal

IMPORTANT WORKFLOW RULES FOR EDITS
Always assume there may be a difference between:

live runtime copy
repo copy

Preferred workflow:

confirm live file path from systemd or runtime usage
edit live file if immediate runtime change is needed
copy live file back into repo path
regenerate snapshot
commit and push

SNAPSHOT / GIT WORKFLOW

Refresh snapshot with:
~/time-server/rebuild/dump_state.sh > ~/time-server/system_config/STATE_SNAPSHOT.txt

Typical git workflow:
cd ~/time-server
git add .
git commit -m "Describe change"
git push

IMPORTANT PRACTICAL NOTES FOR FUTURE CHATS

if dashboard numbers look contradictory, check whether the view is showing raw phase or calibrated phase
do not mistake raw phase offset for corrected timing error
if a plot looks wrong, verify whether the issue is:
bad scaling
stale browser JS cache
invalid/sentinel values not filtered
wrong API endpoint
stale gpsd / zed-monitor path
prefer improving backend sanitation when data contains bogus values, while keeping frontend defensive rendering too

For FE telemetry specifically:

FE frequency metrics are not FE phase metrics
FE frequency metrics do not yet prove UTC alignment
the trend / stability of FE readings is more meaningful than over-interpreting a single ppb value
1-second gated counting introduces quantization effects
use current FE telemetry as a health / stability monitor, not yet as a discipline-error signal

ADDITIONAL CURRENT-STATE NOTE
The current safe rollback point is:

chrony PPS-only working
dashboard GNSS restored via zed-splitter + gpsd-direct + zed-monitor
gpsd.service and gpsd.socket disabled to avoid conflict with gpsd-direct
collector updated for FE stability metrics
dashboard backend and frontend updated for FE metrics
FE 10 MHz live telemetry visible on dashboard

Do not replace this baseline without intentionally testing and confirming a better integrated state.
