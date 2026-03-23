#!/usr/bin/env bash
set -euo pipefail

cd ~/time-server || exit 1

./rebuild/update_version.sh
./rebuild/dump_state.sh > STATE_SNAPSHOT.txt

VERSION_LINE="$(cat VERSION.txt)"

python3 - <<'PY'
from pathlib import Path

p = Path("/home/pi/time-server/STATE_SNAPSHOT.txt")
text = p.read_text(encoding="utf-8")

block = f"""[ REPOSITORY VERSION ]
Git version:
  {Path('/home/pi/time-server/VERSION.txt').read_text(encoding='utf-8').strip()}

Version files:
  /home/pi/time-server/VERSION.txt
  /home/pi/time-server/teensy/generated/git_version.h

"""

if "[ REPOSITORY VERSION ]" in text:
    start = text.index("[ REPOSITORY VERSION ]")
    next_hdr = text.find("\n[ ", start + 1)
    if next_hdr == -1:
        text = text[:start].rstrip() + "\n\n" + block
    else:
        text = text[:start].rstrip() + "\n\n" + block + text[next_hdr+1:]
else:
    marker = "[ GIT ]"
    if marker in text:
        idx = text.index(marker)
        text = text[:idx] + block + text[idx:]
    else:
        text = text.rstrip() + "\n\n" + block

teensy_block = """[ TEENSY FIRMWARE ]
Location:
  /home/pi/time-server/teensy/firmware/teensy_telemetry

Generated version header:
  /home/pi/time-server/teensy/generated/git_version.h

Build environment:
  Arduino IDE with Teensy support

Target:
  Teensy 4.1

Current role:
  Analytics / telemetry / measurement (no discipline yet)

Planned future role:
  FE-5680A discipline and precision timing measurement

"""

if "[ TEENSY FIRMWARE ]" not in text:
    git_marker = "[ GIT ]"
    if git_marker in text:
        idx = text.index(git_marker)
        text = text[:idx] + teensy_block + text[idx:]
    else:
        text = text.rstrip() + "\n\n" + teensy_block

p.write_text(text, encoding="utf-8")
PY

echo "Updated STATE_SNAPSHOT.txt with repository version block"
