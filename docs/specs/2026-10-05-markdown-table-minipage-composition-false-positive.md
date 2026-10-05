# Spec — composition audit false-positive on Pandoc-emitted table `minipage`

- **Date:** 2026-10-05
- **Area:** `python_scripts/reportkit/composition_audit.py`, `publication_pipeline/filters/table-widths.lua`
- **Severity:** blocking (exit 3) for any Markdown publication containing a table
- **Status:** implemented

## Summary

`reportkit check` and `reportkit build` fail for a Markdown-source publication that
contains an ordinary Markdown pipe table, because the composition audit rejects the
`\begin{minipage}` that ReportKit's own Pandoc pipeline emits for sized table cells.

```
error RK_LOCAL_STYLE Local styling command \begin{minipage} bypasses the target theme.
```

This reproduces for `technical-report × default` and `technical-report × operator`,
and therefore blocks table-heavy reports from producing a PDF.

## Reproduction

1. Create a Markdown project (`source_mode: markdown`, `technical-report`, any theme).
2. Add a chapter with a standard pipe table.
3. `reportkit check --source-root .` → blocking `RK_LOCAL_STYLE`; `reportkit build` → exit 3.

Minimal confirmation that the `minipage` is engine output, not author styling:

```sh
pandoc -f markdown-raw_tex -t latex \
  --lua-filter=publication_pipeline/filters/table-widths.lua chapter.md | grep -c minipage
```

## Root cause

1. `publication_pipeline/filters/table-widths.lua` assigns every table column an explicit
   width fraction so that Pandoc's LaTeX writer emits wrapping `p{…}` columns.
2. Given sized columns, Pandoc 3.1.x wraps each cell in
   `\begin{minipage}[b]{\linewidth}\raggedright … \end{minipage}` inside a `longtable`.
3. `composition_audit._universal_diagnostics` scans the generated TeX for
   `_DEFAULT_LOCAL_STYLE`, which includes `\\begin\{minipage\}`, and raises a blocking
   `RK_LOCAL_STYLE` error.

The `minipage` is table furniture produced by the engine after Pandoc parsing. Raw TeX is
disabled in Markdown source mode, so a `minipage` cannot have been authored by the
manuscript. The check is a false positive for Markdown projects; it also triggers the
`RK_PATH`/`RK_TITLE_PAGE` warnings from the generated entrypoint.

## Proposed fix (minimal)

Exclude engine-generated table bodies from the local-style scan, so an author-authored
`minipage` outside a table is still caught:

```python
body = source.split(r"\begin{document}", 1)[-1]
# Pandoc wraps sized table cells in minipage inside longtable; that is
# engine-generated table furniture, not author local styling.
scan_body = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", "", body, flags=re.S)
forbidden = next((p for p in _DEFAULT_LOCAL_STYLE if re.search(p, scan_body)), None)
```

The same `scan_body` should be used for the diagnostic's `.group()` call.

## Acceptance criteria

- [x] A Markdown report with ordinary pipe tables passes `reportkit check` and
      `reportkit build` for `technical-report × {default, operator}` with no `RK_LOCAL_STYLE`.
- [x] A `minipage` authored outside a table (direct-TeX or trusted fragment) is still flagged.
- [x] A regression test covers both cases (table passes; stray `minipage` fails).

Verified with 77 focused tests and separate consumer-project PDF builds for both
themes. Build-report target selections were checked; all rendered pages were
visually inspected, including the tables. The table audit regression fails against
the original implementation for both themes.

## Out of scope

- The non-blocking `RK_PRIMITIVE_OFF_TARGET` warnings for `RKPath`/`RKTitlePage` emitted by
  the generated `publication.tex` entrypoint. Recommended follow-up: run `_used_off_target`
  against author-provided source (fragments/direct TeX), not the generated entrypoint, so
  inactive conditional branches are not scanned.
- `RK_COMPOSITION_REFERENCE_MISSING` for an empty `visual_reference` (by design; record that
  no visual reference was supplied).
- **Related, same root area:** a Pandoc `longtable` with sized `p`-columns can, at a page
  break, emit the recoverable TeX condition `Infinite glue shrinkage found in box being
  split`, which `check_build_log.py` classifies as a blocking `ignored_error`. A consumer can
  accept it per publication via `build-log-allowlist.json`. A durable engine fix would keep
  table rows from splitting at page boundaries (or emit a non-splitting table environment).
