#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
PROJECT_ROOT="${REPORTKIT_SOURCE_ROOT:-$PWD}"
VENV="${1:-$PROJECT_ROOT/build/.venv}"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --requirement "$ROOT/requirements.txt"
echo "ReportKit PDF environment ready: $VENV/bin/python"
