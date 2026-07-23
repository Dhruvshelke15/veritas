#!/bin/bash
# Always runs the server with the project's own venv (Python 3.12, has TensorFlow),
# never whatever "python3" happens to resolve to on PATH.
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/python -m uvicorn app.main:app --port 8000 "$@"
