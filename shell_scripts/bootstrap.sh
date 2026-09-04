#!/usr/bin/env bash
# ReportKit session bootstrap.
#
# Run this once at the start of any ReportKit task, before writing or
# compiling anything. It replaces the several separate steps in
# references/font-setup.md and references/troubleshooting.md with one idempotent command.
#
# Usage:
#   bash bootstrap.sh [project_dir] [work_dir]
#   bash bootstrap.sh /mnt/project /home/claude/report
#
# What it does, and why each step is ordered this way:
#   1. Copies core ReportKit files into a writable working directory
#      (/mnt/project is read-only).
#   2. Installs the Libertinus fonts into a SYSTEM texmf location
#      (TEXMFLOCAL, normally /usr/local/share/texmf) rather than TEXMFHOME.
#      This matters: TEXMFHOME-via-export only lasts for the single
#      bash_tool call that set it, since environment variables do not
#      persist across separate tool calls in this sandbox, but the
#      filesystem does. Installing to TEXMFLOCAL + mktexlsr means every
#      later call -- and every later pdflatex invocation -- just finds the
#      fonts with no export, no sourcing, nothing to remember.
#   3. Falls back to apt-get only if no bundle is present, and prints
#      guidance for the multi-call polling pattern that fallback needs
#      (a single bash_tool call's timeout does not equal process death;
#      see references/font-setup.md for what was actually observed).
#   4. Runs the environment doctor and prints its verdict plainly, so nothing
#      about the build mode is assumed rather than confirmed.
set -uo pipefail

PROJECT_DIR="${1:-/mnt/project}"
WORK_DIR="${2:-/home/claude/report}"
BUNDLE="$PROJECT_DIR/font_data/reportkit-libertinus-fonts.tar.gz"
TEXMFLOCAL="$(kpsewhich -var-value TEXMFLOCAL 2>/dev/null || echo /usr/local/share/texmf)"

echo "== ReportKit bootstrap =="
echo "project dir : $PROJECT_DIR"
echo "work dir    : $WORK_DIR"
echo

echo "-- [1/4] core files --"
mkdir -p "$WORK_DIR"
LATEX_REQUIRED=(reportkit.cls reportkit-boxes.sty reportkit-code.sty reportkit-diagrams.sty)
PYTHON_REQUIRED=(reportkit_doctor.py reportkit_viz.py)
missing=0
for f in "${LATEX_REQUIRED[@]}"; do
  if [ ! -f "$PROJECT_DIR/latex_templates/$f" ]; then
    echo "  MISSING: $PROJECT_DIR/latex_templates/$f" >&2
    missing=1
  fi
done
for f in "${PYTHON_REQUIRED[@]}"; do
  if [ ! -f "$PROJECT_DIR/python_scripts/$f" ]; then
    echo "  MISSING: $PROJECT_DIR/python_scripts/$f" >&2
    missing=1
  fi
done
if [ "$missing" = "1" ]; then
  echo "  One or more core files are absent from $PROJECT_DIR -- stopping." >&2
  echo "  This is a real gap, not something to route around silently." >&2
  exit 1
fi
cp "${LATEX_REQUIRED[@]/#/$PROJECT_DIR/latex_templates/}" "$WORK_DIR/"
cp "${PYTHON_REQUIRED[@]/#/$PROJECT_DIR/python_scripts/}" "$WORK_DIR/"
echo "  copied $((${#LATEX_REQUIRED[@]} + ${#PYTHON_REQUIRED[@]})) core files to $WORK_DIR"
echo

echo "-- [2/4] fonts --"
if kpsewhich libertinus.sty >/dev/null 2>&1 && kpsewhich libertinust1math.sty >/dev/null 2>&1; then
  echo "  already resolvable (nothing to do): $(kpsewhich libertinus.sty)"
elif [ -f "$BUNDLE" ]; then
  echo "  installing portable bundle to $TEXMFLOCAL (no network)"
  mkdir -p "$TEXMFLOCAL"
  tar -xzf "$BUNDLE" -C "$TEXMFLOCAL"
  mktexlsr "$TEXMFLOCAL" >/dev/null 2>&1 || mktexlsr >/dev/null 2>&1
  if kpsewhich libertinus.sty >/dev/null 2>&1 && kpsewhich libertinust1math.sty >/dev/null 2>&1; then
    echo "  OK, resolves with no env var needed: $(kpsewhich libertinus.sty)"
  else
    echo "  bundle extracted but kpsewhich still can't find it -- inspect $TEXMFLOCAL by hand." >&2
  fi
else
  echo "  no bundle at $BUNDLE and no system copy found." >&2
  echo "  Fallback: apt-get update && apt-get install -y --no-install-recommends texlive-fonts-extra" >&2
  echo "  This is a large (~1.7GB) package. Run it as a PLAIN FOREGROUND command," >&2
  echo "  not 'nohup ... &' -- backgrounded processes do not survive across separate" >&2
  echo "  bash_tool calls here. If it runs long, it is safe to let the call return and" >&2
  echo "  poll for completion from a later call with a wait loop; do not assume it died." >&2
  echo "  Consider harvesting a bundle afterward (references/font-setup.md) so" >&2
  echo "  future sessions skip this path -- offer that to the person, don't do it silently." >&2
fi
echo

echo "-- [3/4] figures directory --"
mkdir -p "$WORK_DIR/figures"
echo "  $WORK_DIR/figures ready"
echo

echo "-- [4/4] environment doctor --"
( cd "$WORK_DIR" && python3 reportkit_doctor.py )
echo
echo "== bootstrap complete =="
echo "Working directory: $WORK_DIR"
