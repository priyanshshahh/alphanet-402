#!/bin/sh
set -e
cd /app
python -c "from app.database import init_db; init_db()"
python seed_demo.py
python seed_history.py
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
