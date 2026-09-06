#!/usr/bin/env bash
# combine.sh -- canonical full-document build driven by manuscript/order.txt.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/guide-build.py" --mode combined
