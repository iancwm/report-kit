#!/usr/bin/env bash
# build-section.sh <manuscript-md-file>
# Build one manuscript section in isolation for focused visual QA.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <manuscript-md-file>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/guide-build.py" --mode section --section "$1"
