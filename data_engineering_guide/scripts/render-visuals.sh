#!/usr/bin/env bash
# render-visuals.sh <manuscript.md> <fragments-dir> <output.tex>
#
# Converts one manuscript Markdown file to a LaTeX body fragment with
# Pandoc, then replaces every REPORTKIT-VISUAL sentinel line with the
# verbatim contents of its matching fragment file. Files with no sentinel
# pass through unchanged.
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <manuscript.md> <fragments-dir> <output.tex>" >&2
  exit 1
fi

manuscript="$1"
fragments_dir="$2"
output="$3"

mkdir -p "$(dirname "$output")"
: > "$output"

# Capture pandoc output to a temp file to check its exit code explicitly.
# Process substitution doesn't propagate pandoc failures to set -e.
pandoc_output=$(mktemp)
trap "rm -f '$pandoc_output'" EXIT

if ! pandoc -f markdown -t latex "$manuscript" > "$pandoc_output"; then
  echo "render-visuals.sh: pandoc failed to process $manuscript" >&2
  exit 1
fi

while IFS= read -r line; do
  # Trim leading and trailing whitespace using parameter expansion.
  trimmed="${line#"${line%%[![:space:]]*}"}"
  trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
  if [[ "$trimmed" =~ ^\{\[\}\{\[\}REPORTKIT-VISUAL:fig:([a-z0-9-]+)\{\]\}\{\]\}$ ]]; then
    slug="${BASH_REMATCH[1]}"
    fragment="$fragments_dir/fig-${slug}.tex"
    if [[ ! -f "$fragment" ]]; then
      echo "render-visuals.sh: missing fragment for fig:$slug at $fragment" >&2
      exit 1
    fi
    cat "$fragment" >> "$output"
  else
    printf '%s\n' "$line" >> "$output"
  fi
done < "$pandoc_output"

echo "render-visuals.sh: wrote $output" >&2
