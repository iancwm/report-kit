#!/usr/bin/env bash
# Fast staged-file gate for guide changes. CI runs the full PDF build separately.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
changed="$(git -C "$REPO_ROOT" diff --cached --name-only)"

python3 "$ROOT/scripts/validate-guide.py" --root "$ROOT"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "WARN: pandoc not found; static guide validation passed, render checks deferred to CI." >&2
  exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
while IFS= read -r path; do
  [[ "$path" == data_engineering_guide/manuscript/*.md ]] || continue
  manuscript="$REPO_ROOT/$path"
  bash "$ROOT/scripts/render-visuals.sh" "$manuscript" "$ROOT/fragments" "$tmp/$(basename "$manuscript" .md).tex" >/dev/null
done <<< "$changed"

if [[ "${GUIDE_PRECOMMIT_BUILD:-0}" == "1" ]]; then
  while IFS= read -r path; do
    [[ "$path" == data_engineering_guide/manuscript/*.md ]] || continue
    bash "$ROOT/scripts/build-section.sh" "${path#data_engineering_guide/}"
  done <<< "$changed"
fi

echo "PASS: staged guide validation and Pandoc checks"
