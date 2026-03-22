#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

./rebuild/install_packages.sh
./rebuild/deploy_snapshot.sh
./rebuild/enable_services.sh

echo
echo "Rebuild complete."
