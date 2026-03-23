#!/usr/bin/env bash
set -euo pipefail

cd ~/time-server || exit 1

VERSION="$(git describe --always --dirty --tags 2>/dev/null || git rev-parse --short HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
FULL_VERSION="${VERSION} [${BRANCH}]"

echo "$FULL_VERSION" > VERSION.txt

mkdir -p teensy/generated
cat > teensy/generated/git_version.h <<EOV
#pragma once
#define GIT_VERSION "${FULL_VERSION}"
EOV

echo "Updated VERSION.txt:"
cat VERSION.txt
echo
echo "Updated teensy/generated/git_version.h"
