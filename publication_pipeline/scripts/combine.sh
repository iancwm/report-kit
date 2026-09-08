#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$(cd "$ROOT/.." && pwd)/reportkit" build --mode combined "$@"
