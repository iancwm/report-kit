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
| [2026-09-06-reportkit-tooling-hardening-design.md](docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md) | Approved, implementation slice landed; tooling follow-up remains | P1 |
| [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md) | Draft / roadmap — reconciled; implement from the plan, not this | P3 |
| [2026-09-07-reportkit-vnext-implementation-plan.md](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md) | Phase 1–4 implementation landed on `vnext-release`; follow-up remains | P3 |
| [2026-09-07-documentation-and-status-tracking-cleanup-design.md](docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md) | Approved | Process |
| [2026-09-07-documentation-and-status-tracking-cleanup.md](docs/superpowers/plans/2026-09-07-documentation-and-status-tracking-cleanup.md) | Done — merged via PR #7 (`965443b`) | Process |

## Open work

### P0

- **P0-1 — delete `tooling`, don't re-cut it.** `git rev-list --left-right
  --count main...tooling` returns `34 0` (verified 2026-09-07): the branch has
  no unique commits, so there is nothing to preserve, and
  [references/migrating-content-branches.md](references/migrating-content-branches.md)
  already dispositions it as "Superseded and stale… then delete". Branch the
  next tooling slice fresh from `main`.

### P1

- Continue the tooling-hardening implementation slices and reconcile them with the vNext roadmap before starting new phases.

### P3

- vNext — **reconciled 2026-09-07**; the overlap with the tooling spec is now
  audited section by section in
  [the implementation plan](docs/superpowers/plans/2026-09-07-reportkit-vnext-implementation-plan.md).
  Six of seventeen sections are already implemented. The real Phase 1 is seven
  work items: an importable package, a nested `publication.yaml`, typed
  diagnostics carrying source locations and ownership, a generated capability
  registry, a stdlib CLI facade, manifest history, and wiring up the
  `publication_pipeline/tests/` suite that nothing currently runs.
- Backlog: a Copier template for consumer projects — deliberately deferred until vNext §4 settles `publication.yaml`'s schema and there's more than one content repo to keep in sync.

## Environment notes

- `pdfinfo`, `pdffonts`, `pdftoppm` (poppler-utils): not installed on the current dev machine.
- `pypdf`, `pdfplumber`, system-wide PyMuPDF: not installed.
- `accsupp.sty`: not installed; `tlmgr install` fails (this checkout is TinyTeX on TL2025 against a TL2026 remote).
- Libertinus fonts: installed to `TEXMFHOME` (`~/.TinyTeX/texmf-local`) from `font_data/reportkit-libertinus-fonts.tar.gz`.

## History

- 2026-09-07: docs-cleanup plan completed and merged to `main` via PR #7 (`965443b`); status flipped to Done per the plan's own completion rule (none of its 26 checklist items were ever checked off inline, but the doc's explicit "Flips to Done when this branch merges" criterion was satisfied).
- 2026-09-06: five stale spec/plan documents verified implemented and deleted (four untracked, one tracked — recoverable from git history at the parent of `49af053`).
- `docs/tooling-improvement-spec-draft.md` was lost permanently in 2026-09-06 while `docs/` was gitignored and untracked — the reason specs/plans are tracked in git from 2026-09-07 onward.
