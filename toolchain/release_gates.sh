#!/usr/bin/env bash
# In-image release gates for one image reference (local candidate or pushed
# digest). Usage: toolchain/release_gates.sh <image-ref> <summary.json>
set -euo pipefail
image="$1"
summary="$2"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker run --rm --network none --platform linux/amd64 --entrypoint /bin/bash "$image" -lc '
  set -euo pipefail
  export PATH="/opt/reportkit/.venv/bin:$PATH"
  ./reportkit doctor --require pinned-toolchain --json
  ./reportkit docs --check --json
  bash scripts/acceptance_check.sh --require-tex
  python scripts/contract_acceptance.py --json'

unpinned=()
[[ "$image" == *@sha256:* ]] || unpinned=(--allow-unpinned-image)
python3 "$root/scripts/cross_host_gate.py" run --image "$image" "${unpinned[@]}" \
  --work-dir "${RUNNER_TEMP:-$(mktemp -d)}/gate" --summary "$summary" --commit HEAD
