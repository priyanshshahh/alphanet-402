#!/bin/sh
set -e
cd /app
python seed_demo.py 2>/dev/null || true
python seed_history.py 2>/dev/null || true
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
