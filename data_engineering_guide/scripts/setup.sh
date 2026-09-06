#!/usr/bin/env bash
# setup.sh -- create the locked local environment used by guide builds.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

"$PYTHON" -m venv "$ROOT/build/.venv"
"$ROOT/build/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/build/.venv/bin/python" -m pip install --requirement "$ROOT/requirements.txt"
echo "Guide tooling ready: $ROOT/build/.venv/bin/python"
