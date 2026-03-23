#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 \"commit message\""
  exit 1
fi

cd ~/time-server || exit 1

./rebuild/update_snapshot_with_version.sh

git add VERSION.txt teensy/generated/git_version.h STATE_SNAPSHOT.txt
git add .

git commit -m "$1"
