#!/usr/bin/env bash
# AlphaNet-402 — start the React dev server (default http://localhost:5173 → API :8000).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/alphanet-core/frontend"
npm install
exec npm run dev
