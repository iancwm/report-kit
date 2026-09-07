#!/usr/bin/env bash
# ReportKit acceptance check -- compiles legacy and visual-grammar acceptance
# tests and greps their logs for known failure signatures. Intended to run from
# .githooks/pre-commit before a commit touching latex_templates/** or
# python_scripts/**, and by hand before tagging a release.
#
# Exit codes:
#   0 - clean compile, OR pdflatex not installed in diagnostic mode
#   1 - compile failed, log matched a known failure signature, or strict mode
#       was requested but TeX is unavailable
set -uo pipefail

require_tex=0
if [[ "${1:-}" == "--require-tex" ]]; then
  require_tex=1
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--require-tex]" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TEXES=(
  "latex_templates/examples/primitive_acceptance_test.tex"
  "latex_templates/examples/primitive_additions_acceptance_test.tex"
  "latex_templates/examples/visual_grammar_acceptance_test.tex"
  "latex_templates/examples/longform_acceptance_test.tex"
)

echo "== ReportKit acceptance check =="

if ! command -v pdflatex >/dev/null 2>&1; then
  echo "WARN: pdflatex not found on PATH -- skipping acceptance check (not blocking)." >&2
  echo "      Real enforcement happens the next time this runs somewhere with TeX installed." >&2
  [[ "$require_tex" -eq 0 ]] && exit 0
  echo "FAIL: --require-tex was requested but pdflatex is unavailable." >&2
  exit 1
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

# Rendered-geometry tests catch defects that leave no trace in a TeX log. The
# reportnetwork collision compiled successfully while reversing every arrow,
# so log-grep alone cannot be the visual grammar gate.
TEST_PYTHON="${REPORTKIT_TEST_PYTHON:-}"
if [[ -z "$TEST_PYTHON" && -x "$ROOT/build/.venv-tests/bin/python" ]]; then
  TEST_PYTHON="$ROOT/build/.venv-tests/bin/python"
fi
if [[ -n "$TEST_PYTHON" ]]; then
  if ! "$TEST_PYTHON" -m pytest "$ROOT/tests" -q > "$WORKDIR/pytest.log" 2>&1; then
    echo "FAIL: rendered-geometry tests failed:" >&2
    tail -40 "$WORKDIR/pytest.log" >&2
    hit=1
  else
    echo "-- rendered-geometry tests: OK --"
  fi
elif [[ "$require_tex" -eq 1 ]]; then
  echo "FAIL: strict acceptance requires the geometry-test environment." >&2
  echo "      Install it: python3 -m venv build/.venv-tests && build/.venv-tests/bin/pip install -r tests/requirements.txt" >&2
  hit=1
else
  echo "WARN: no geometry-test environment -- skipping rendered-geometry tests (not blocking)." >&2
fi

cp "$ROOT"/latex_templates/*.cls "$ROOT"/latex_templates/*.sty "$WORKDIR"/
status=0
: > "$WORKDIR/compile.log"
for test_tex in "${TEST_TEXES[@]}"; do
  cp "$ROOT/$test_tex" "$WORKDIR"/
  test_name="$(basename "$test_tex")"
  if ! (
    cd "$WORKDIR"
    pdflatex -interaction=nonstopmode -halt-on-error "$test_name"
    pdflatex -interaction=nonstopmode -halt-on-error "$test_name"
  ) >> "$WORKDIR/compile.log" 2>&1; then
    status=1
  fi
done

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

echo "PASS: legacy and visual-grammar acceptance tests compiled cleanly."
exit 0
