#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=.
# No --reload: file-watch restarts kill in-flight research jobs.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
