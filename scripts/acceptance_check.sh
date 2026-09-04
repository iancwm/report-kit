#!/usr/bin/env bash
# ReportKit acceptance check -- compiles the primitive acceptance test and
# greps the log for known failure signatures. Intended to run from
# .githooks/pre-commit before a commit touching latex_templates/** or
# python_scripts/**, and by hand before tagging a release.
#
# Exit codes:
#   0 - clean compile, OR pdflatex not installed (warns, does not block)
#   1 - compile failed, or the log matched a known failure signature
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TEX="latex_templates/examples/primitive_acceptance_test.tex"

echo "== ReportKit acceptance check =="

if ! command -v pdflatex >/dev/null 2>&1; then
  echo "WARN: pdflatex not found on PATH -- skipping acceptance check (not blocking)." >&2
  echo "      Real enforcement happens the next time this runs somewhere with TeX installed." >&2
  exit 0
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

hit=0

# python_scripts/** also triggers this check via the pre-commit hook, so
# make sure the Python files actually import cleanly.
if command -v python3 >/dev/null 2>&1; then
  if ! python3 -c "
import sys
sys.path.insert(0, '$ROOT/python_scripts')
import reportkit_viz
import reportkit_doctor
" > "$WORKDIR/python-check.log" 2>&1; then
    echo "FAIL: python_scripts/ failed to import cleanly:" >&2
    cat "$WORKDIR/python-check.log" >&2
    hit=1
  else
    echo "-- python_scripts/ import check: OK --"
  fi
else
  echo "WARN: python3 not found -- skipping python_scripts/ import check (not blocking)." >&2
fi

cp "$ROOT"/latex_templates/*.cls "$ROOT"/latex_templates/*.sty "$WORKDIR"/
cp "$ROOT/$TEST_TEX" "$WORKDIR"/

(
  cd "$WORKDIR"
  pdflatex -interaction=nonstopmode -halt-on-error primitive_acceptance_test.tex
) > "$WORKDIR/compile.log" 2>&1
status=$?

echo "-- compile exit status: $status --"

# Known failure signatures -- see references/known-fixes.md for the defects
# these correspond to.
SIGNATURES=(
  "Illegal unit of measure"
  "Undefined control sequence"
  "cannot be found"
  "Emergency stop"
)

for sig in "${SIGNATURES[@]}"; do
  if grep -q "$sig" "$WORKDIR/compile.log"; then
    echo "FAIL: log matched known failure signature: \"$sig\"" >&2
    hit=1
  fi
done

if [ "$status" -ne 0 ] || [ "$hit" -ne 0 ]; then
  echo "FAIL: acceptance check did not pass. Full log:" >&2
  cat "$WORKDIR/compile.log" >&2
  exit 1
fi

echo "PASS: primitive acceptance test compiled cleanly."
exit 0
