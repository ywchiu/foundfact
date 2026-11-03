#!/bin/sh
# Starts the hunch proxy (local stage-1 student) in the background, then the API in the foreground.
# hunch's teacher is this same API's /teacher/v1/answer, reachable only from 127.0.0.1.
set -e
python -m hunch serve --db /app/data/hunch.db --layer "${HUNCH_LAYER:-12}" --port 8765 \
  --backend "http://127.0.0.1:${PORT}/teacher/v1/answer" &
cd /app/backend
exec uvicorn app.api:app --host 0.0.0.0 --port "${PORT}" --proxy-headers --forwarded-allow-ips='*'
