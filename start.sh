#!/usr/bin/env bash
set -euo pipefail
# Default PORT if not provided by environment
: "${PORT:=8000}"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
