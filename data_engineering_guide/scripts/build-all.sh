#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/guide-build.py" --mode sections --workers "${GUIDE_BUILD_WORKERS:-2}"
