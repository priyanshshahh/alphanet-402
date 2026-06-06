#!/usr/bin/env bash
# AlphaNet-402 — start the FastAPI backend (default http://localhost:8000).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/alphanet-core/backend"

if [[ ! -d .venv ]]; then
  echo "Creating Python venv in alphanet-core/backend/.venv …"
  python3 -m venv .venv
  ./.venv/bin/pip install -U pip
  ./.venv/bin/pip install -r requirements.txt
fi

export PORT="${PORT:-8000}"
exec ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
