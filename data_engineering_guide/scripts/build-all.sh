#!/usr/bin/env bash
# build-all.sh -- build instructional sections with bounded parallelism.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workers="${GUIDE_BUILD_WORKERS:-2}"
exec python3 "$ROOT/scripts/guide-build.py" --mode sections --workers "$workers"
