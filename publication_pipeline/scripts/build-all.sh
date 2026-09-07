#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/publication_build.py" --mode sections --workers "${REPORTKIT_BUILD_WORKERS:-2}"
