#!/usr/bin/env bash
# build-all.sh -- runs build-section.sh over every instructional section (1-9).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for md in "$ROOT"/manuscript/0[1-9]-*.md; do
  echo "== building $(basename "$md") ==" >&2
  bash "$ROOT/scripts/build-section.sh" "$md"
done
