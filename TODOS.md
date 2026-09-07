# ReportKit — Outstanding Work

**Last updated:** 2026-09-07

This is an index, not an audit. Each spec/plan under `docs/superpowers/`
carries its own `**Status:**` line, updated at the workflow checkpoint that
changed it (approval, execution start, merge). This file is a one-line
pointer per document plus a rollup of what's still open — edited
incrementally when a status changes, never rebuilt from scratch. See
[docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md)
for why.

## Documents

| Document | Status | Priority |
|---|---|---|
| [data-engineering-guide-publication-review.md](docs/data-engineering-guide-publication-review.md) | Evidence / release gate for the 56-page build | Gate |
| [2026-09-06-reportkit-tooling-hardening-design.md](docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md) | Approved, implementation slice landed; guide content still pending | P1 |
| [2026-09-06-data-engineering-guide-content-design.md](docs/superpowers/specs/2026-09-06-data-engineering-guide-content-design.md) | Approved, ~60% implemented | P1 |
| [2026-09-06-reportkit-visual-grammar.md](docs/superpowers/plans/2026-09-06-reportkit-visual-grammar.md) | Approved, unexecuted — blocked on P0-2 | P1 |
| [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md) | Draft / roadmap, not started | P3 |

## Open work

### P0

- **P0-1 — extract the guide content branch.** `data-engineering-guide-content` has the manuscript; no branch has both manuscript and builder. Resolution is to extract it into its own consumer repo per [references/migrating-content-branches.md](references/migrating-content-branches.md) — not yet done, branch still unextracted.
- **P0-2 — re-cut `tooling` from `main`.** It's 0 ahead / 17 behind `main` and blocks executing the visual-grammar plan. Re-cut before starting that plan's Task 1.

### P1

- Content spec §D1, §D3 (3 remaining figures), §D4 (2 figures), §E2, §F — remaining manuscript work; the tooling to support it now exists.
- Content follow-ups: retire the `\RKNode` workaround in `fig-sec01-lifecycle.tex` and the `text width=24mm` workaround in `fig-sec07-lineage.tex` (both fixed upstream, workarounds now unnecessary).
- Distribution: no A4 cover asset exists in any branch — produce one or drop the claim.

### P2

- B4 contrast audit (`reportkit.cls:44` Muted colour, syntax palette) — not started.
- P2-01 page-rhythm rebalance, P1-06 keep short code listings together — not started.
- F2 measure-before-optimising — not started.

### P3

- vNext roadmap (Typer CLI, `publication.yaml`, structured diagnostics, chapter builds, PDF inspection, build manifest, registries, a publication skill) — substantial overlap with the tooling spec; reconcile before starting Phase 1.
- Backlog: a Copier template for consumer projects — deliberately deferred until vNext §4 settles `publication.yaml`'s schema and there's more than one content repo to keep in sync.

## Environment notes

- `pdfinfo`, `pdffonts`, `pdftoppm` (poppler-utils): not installed on the current dev machine.
- `pypdf`, `pdfplumber`, system-wide PyMuPDF: not installed.
- `accsupp.sty`: not installed; `tlmgr install` fails (this checkout is TinyTeX on TL2025 against a TL2026 remote).
- Libertinus fonts: installed to `TEXMFHOME` (`~/.TinyTeX/texmf-local`) from `font_data/reportkit-libertinus-fonts.tar.gz`.

## History

- 2026-09-06: five stale spec/plan documents verified implemented and deleted (four untracked, one tracked — recoverable from git history at the parent of `49af053`).
- `docs/tooling-improvement-spec-draft.md` was lost permanently in 2026-09-06 while `docs/` was gitignored and untracked — the reason specs/plans are tracked in git from 2026-09-07 onward.
