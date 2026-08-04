#!/usr/bin/env bash
set -euo pipefail

# If no args provided, fall back to a safe default start command.
# Replace `main:app` with your actual WSGI/ASGI entrypoint if different.
if [ $# -eq 0 ]; then
  exec gunicorn main:app --bind 0.0.0.0:${PORT:-8000}
else
  exec "$@"
fi
