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
  "latex_templates/examples/algorithm_acceptance_test.tex"
  "latex_templates/examples/algorithm_visuals_acceptance_test.tex"
  "latex_templates/examples/algorithm_visuals_linear_acceptance_test.tex"
  "latex_templates/examples/algorithm_visuals_graph_acceptance_test.tex"
  "latex_templates/examples/algorithm_visuals_order_acceptance_test.tex"
  "latex_templates/examples/algorithm_visuals_dp_acceptance_test.tex"
)

echo "== ReportKit acceptance check =="

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# Exercise the documented clone -> init -> build path in a disposable
# consumer project. The compile portion is conditional below, but scaffolding
# and static validation still catch a stale quick-start command on machines
# without TeX.
FRESH_PROJECT="$WORKDIR/fresh-publication"
if ! "$ROOT/reportkit" init "$FRESH_PROJECT" > "$WORKDIR/init.log" 2>&1; then
  echo "FAIL: reportkit init fresh-project dry run failed:" >&2
  cat "$WORKDIR/init.log" >&2
  hit=1
else
  cp -a "$ROOT/publication_pipeline/example_publication/." "$FRESH_PROJECT/"
  if ! "$ROOT/reportkit" check --source-root "$FRESH_PROJECT" > "$WORKDIR/check.log" 2>&1; then
    echo "FAIL: initialized project did not pass reportkit check:" >&2
    cat "$WORKDIR/check.log" >&2
    hit=1
  else
    echo "-- fresh-project init/check dry run: OK --"
  fi
fi

if ! command -v pdflatex >/dev/null 2>&1; then
  echo "WARN: pdflatex not found on PATH -- skipping acceptance check (not blocking)." >&2
  echo "      Real enforcement happens the next time this runs somewhere with TeX installed." >&2
  if [[ "${hit:-0}" -ne 0 ]]; then
    exit 1
  fi
  [[ "$require_tex" -eq 0 ]] && exit 0
  echo "FAIL: --require-tex was requested but pdflatex is unavailable." >&2
  exit 1
fi

hit="${hit:-0}"

# python_scripts/** also triggers this check via the pre-commit hook, so
# make sure the Python files actually import cleanly.
if command -v python3 >/dev/null 2>&1; then
  if ! PYTHONPATH="$ROOT/python_scripts${PYTHONPATH:+:$PYTHONPATH}" python3 -c "
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
TEST_VENV="${REPORTKIT_TEST_VENV:-}"

# Auto-detect test venv at build/.venv-tests if not explicitly set
if [[ -z "$TEST_VENV" && -d "$ROOT/build/.venv-tests" ]]; then
  TEST_VENV="$ROOT/build/.venv-tests"
fi

if [[ -z "$TEST_PYTHON" && -n "$TEST_VENV" && -x "$TEST_VENV/bin/python" ]] \
   && "$TEST_VENV/bin/python" -c 'import pytest' >/dev/null 2>&1; then
  TEST_PYTHON="$TEST_VENV/bin/python"
fi
if [[ -z "$TEST_PYTHON" ]] && command -v python3 >/dev/null 2>&1 \
  && python3 -c 'import pytest' >/dev/null 2>&1; then
  TEST_PYTHON="$(command -v python3)"
fi
if [[ -n "$TEST_PYTHON" ]]; then
  if ! "$TEST_PYTHON" -m pytest "$ROOT/tests" "$ROOT/publication_pipeline/tests" -q > "$WORKDIR/pytest.log" 2>&1; then
    echo "FAIL: rendered-geometry or publication-pipeline tests failed:" >&2
    tail -40 "$WORKDIR/pytest.log" >&2
    hit=1
  else
    echo "-- rendered-geometry tests: OK --"
  fi
elif [[ "$require_tex" -eq 1 ]]; then
  echo "FAIL: strict acceptance requires the geometry-test environment." >&2
  echo "      Install it in a consumer project: python3 -m venv <publication-project>/build/.venv-tests && <publication-project>/build/.venv-tests/bin/pip install -r <report-kit-clone>/tests/requirements.txt" >&2
  hit=1
else
  echo "WARN: no geometry-test environment -- skipping rendered-geometry tests (not blocking)." >&2
fi

# template_files() is the single canonical TeX input list. It includes the
# themes/ and publication_types/ directories, then flattens them into
# WORKDIR so \documentclass{reportkit} can resolve every selected component.
if ! PYTHONPATH="$ROOT/python_scripts:$ROOT/publication_pipeline/scripts${PYTHONPATH:+:$PYTHONPATH}" \
  python3 -c 'from publication_build import template_files; print("\n".join(str(path) for path in template_files()))' \
  > "$WORKDIR/template-files.txt"; then
  echo "FAIL: could not resolve the canonical TeX template list." >&2
  hit=1
else
  mapfile -t template_files < "$WORKDIR/template-files.txt"
  if [[ "${#template_files[@]}" -eq 0 ]]; then
    echo "FAIL: canonical TeX template list is empty." >&2
    hit=1
  else
    cp "${template_files[@]}" "$WORKDIR"/
  fi
fi
if [[ -d "$ROOT/font_data" ]]; then
  mkdir -p "$WORKDIR/font_data"
  cp "$ROOT"/font_data/GoogleSans-*.ttf "$WORKDIR/font_data"/
fi
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

if command -v pandoc >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 \
  && python3 -c 'import pymupdf' >/dev/null 2>&1; then
  if ! "$ROOT/reportkit" build --source-root "$FRESH_PROJECT" --json > "$WORKDIR/fresh-build.json" 2> "$WORKDIR/fresh-build.err"; then
    echo "FAIL: fresh-project build dry run failed:" >&2
    cat "$WORKDIR/fresh-build.err" >&2
    hit=1
  elif ! python3 -c 'import json, sys; payload=json.load(open(sys.argv[1])); assert payload.get("passed")' "$WORKDIR/fresh-build.json"; then
    echo "FAIL: fresh-project build dry run did not pass:" >&2
    cat "$WORKDIR/fresh-build.json" >&2
    hit=1
  else
    echo "-- fresh-project full build dry run: OK --"
  fi
else
  echo "WARN: pandoc or PyMuPDF unavailable -- skipping fresh-project full build dry run." >&2
fi

# The institutional-research theme requires lualatex (spec section 4 /
# open question 1) -- it cannot be added to TEST_TEXES above, which
# compiles everything with pdflatex and would hit that theme's own
# \ifPDFTeX engine guard immediately, a correct failure that would look
# indistinguishable from a real regression. Compile it separately, with
# lualatex, same non-blocking-when-the-engine-is-missing convention as the
# pdflatex block above. latex_templates/examples/equity-research/ (the
# full four-page fictional publication) is deliberately not compiled
# here -- see scripts/visual_qa_equity_research.py, which also renders and
# pixel-diffs it against a checked-in baseline; this block only covers the
# fast primitive-smoke-test fixture.
LUALATEX_TEST_TEXES=(
  "latex_templates/examples/institutional_equity_acceptance_test.tex"
  # Phase B (slide renderer and presentation semantics): the executive
  # theme also requires lualatex (same engine guard as institutional-
  # research, same reason). This is a compile smoke test exercising every
  # reportkit-presentation.sty composition once, not a real deck.
  "latex_templates/examples/presentation_acceptance_test.tex"
)
lua_status=0
if command -v lualatex >/dev/null 2>&1; then
  : > "$WORKDIR/lualatex-compile.log"
  for test_tex in "${LUALATEX_TEST_TEXES[@]}"; do
    cp "$ROOT/$test_tex" "$WORKDIR"/
    test_name="$(basename "$test_tex")"
    if ! (
      cd "$WORKDIR"
      lualatex -interaction=nonstopmode -halt-on-error "$test_name"
      lualatex -interaction=nonstopmode -halt-on-error "$test_name"
    ) >> "$WORKDIR/lualatex-compile.log" 2>&1; then
      lua_status=1
    fi
  done
  echo "-- lualatex compile exit status: $lua_status --"
  cat "$WORKDIR/lualatex-compile.log" >> "$WORKDIR/compile.log"
else
  echo "WARN: lualatex not found on PATH -- skipping institutional-research/equity-research acceptance check (not blocking)." >&2
  if [[ "$require_tex" -eq 1 ]]; then
    echo "FAIL: --require-tex was requested but lualatex is unavailable." >&2
    lua_status=1
  fi
fi

# B4: the slide fixture's accessibility contract is checked against the
# compiled PDF, not inferred from a successful TeX run. The status is kept
# truthful: ReportKit currently ships metadata/language/bookmarks/links and
# diagram ActualText, while tagged PDF remains explicitly unsupported until
# the documented tagging spike succeeds in a compatible TeX format.
slide_accessibility_status=0
slide_inspect_python="${TEST_PYTHON:-$(command -v python3 2>/dev/null || true)}"
if [[ "$lua_status" -eq 0 && -n "$slide_inspect_python" ]] \
  && "$slide_inspect_python" -c 'import pymupdf' >/dev/null 2>&1; then
  if ! PYTHONPATH="$ROOT/python_scripts:$ROOT/publication_pipeline/scripts${PYTHONPATH:+:$PYTHONPATH}" \
    "$slide_inspect_python" "$ROOT/publication_pipeline/scripts/inspect_pdf.py" \
      "$WORKDIR/presentation_acceptance_test.pdf" \
      --slide-accessibility \
      --expected-title "Every presentation composition, once - Phase B compile coverage, not a real deck" \
      --expected-author "Test build" \
      --expected-subject "Presentation accessibility acceptance" \
      --expected-keywords "ReportKit, presentation, accessibility" \
      --expected-language "en-US" \
      --minimum-bookmarks 1 \
      --expected-bookmark-title "Message and evidence" \
      --expected-bookmark-title "Visuals" \
      --expected-bookmark-title "Structure" \
      --expected-bookmark-title "Appendix: Chart, table, and architecture aliases" \
      --minimum-meaningful-links 1 \
      --expected-actual-text 3 \
      --tagged-pdf-status unsupported \
      --tagged-pdf-reason "The pinned LaTeX format has not yet passed the documented tagging spike." \
      --json "$WORKDIR/presentation-accessibility.json"; then
    echo "FAIL: slide accessibility inspection failed." >&2
    slide_accessibility_status=1
  else
    echo "-- slide accessibility inspection: OK --"
  fi
else
  echo "WARN: slide accessibility inspection skipped because PyMuPDF is unavailable (not blocking)." >&2
  if [[ "$require_tex" -eq 1 && "$lua_status" -eq 0 ]]; then
    echo "FAIL: --require-tex was requested but the slide accessibility inspector is unavailable." >&2
    slide_accessibility_status=1
  fi
fi

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

# Exercise the documented consumer setup from a clone-shaped checkout. The
# diagnostic acceptance mode remains useful on hosts without the full Python
# and TeX toolchain, so skip this integration run there rather than turning a
# missing optional environment into a source regression.
if command -v git >/dev/null 2>&1 && command -v pandoc >/dev/null 2>&1 \
  && command -v pdflatex >/dev/null 2>&1 \
  && python3 -c 'import matplotlib, numpy, pandas, pymupdf' >/dev/null 2>&1; then
  FRESH_CLONE="$(mktemp -d)"
  FRESH_PROJECT="$(mktemp -d)"
  if ! git clone --quiet --no-local "$ROOT" "$FRESH_CLONE"; then
    echo "FAIL: could not create fresh-clone acceptance checkout." >&2
    hit=1
  elif ! "$FRESH_CLONE/reportkit" init "$FRESH_PROJECT" --install-fonts > "$WORKDIR/fresh-init.log" 2>&1; then
    echo "FAIL: documented reportkit init failed:" >&2
    cat "$WORKDIR/fresh-init.log" >&2
    hit=1
  else
    # The initializer creates an empty consumer; use the repository's generic
    # fixture as content so this check reaches the full publication build.
    cp -R "$FRESH_CLONE/publication_pipeline/example_publication/." "$FRESH_PROJECT/"
    if ! "$FRESH_CLONE/reportkit" doctor --require full-build > "$WORKDIR/fresh-doctor.log" 2>&1 \
      || ! grep -q "MODE: FULL BUILD" "$WORKDIR/fresh-doctor.log"; then
      echo "FAIL: fresh-clone doctor did not reach MODE: FULL BUILD:" >&2
      cat "$WORKDIR/fresh-doctor.log" >&2
      hit=1
    elif ! "$FRESH_CLONE/reportkit" build --source-root "$FRESH_PROJECT" \
      --output-root "$FRESH_PROJECT/build" > "$WORKDIR/fresh-build.log" 2>&1; then
      echo "FAIL: fresh-clone publication build failed:" >&2
      tail -80 "$WORKDIR/fresh-build.log" >&2
      hit=1
    else
      echo "-- fresh-clone init/doctor/build: OK --"
    fi
  fi
  rm -rf "$FRESH_CLONE" "$FRESH_PROJECT"
else
  echo "WARN: full Python/TeX publication environment unavailable -- skipping fresh-clone dry run (not blocking)." >&2
fi

if [ "$status" -ne 0 ] || [ "$lua_status" -ne 0 ] || [ "$slide_accessibility_status" -ne 0 ] || [ "$hit" -ne 0 ]; then
  echo "FAIL: acceptance check did not pass. Full log:" >&2
  cat "$WORKDIR/compile.log" >&2
  exit 1
fi

echo "PASS: legacy, visual-grammar, and institutional-research/equity-research acceptance tests compiled cleanly."
exit 0
