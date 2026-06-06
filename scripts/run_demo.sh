#!/usr/bin/env bash
# Deprecated path: use repo-root ./run_demo.sh
set -euo pipefail
exec "$(cd "$(dirname "$0")/.." && pwd)/run_demo.sh"
