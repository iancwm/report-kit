# Documentation and status-tracking cleanup

**Status:** Approved
**Last updated:** 2026-09-07

## Problem

Documentation is split across four places with overlapping, drifted roles:

- `references/` — tracked, meant to be permanent "skill-facing reference
  docs" per the `.gitignore` comment (font-setup, known-fixes,
  troubleshooting, `repository-boundary.md`, licensing, etc.).
- `documentation/` — tracked, but holds exactly one file
  (`licensing.md`) that duplicates `references/licensing.md`. Both were
  added in the same commit (`4b79642`): `references/licensing.md` is a
  stub that points at `documentation/licensing.md` instead of containing
  the content itself. Not drift over time — a one-off mistake.
- `docs/` — gitignored ("Superpowers process docs ... planning
  scaffolding, not part of the shipped skill"). Holds specs, plans, a
  roadmap doc, a review-gate doc, and a stray untracked task-brief
  (`docs/licensing.md`). Three files have needed manual force-adds past
  the ignore rule as one-off exceptions. Being gitignored has already
  cost real work: `tooling-improvement-spec-draft.md` was permanently
  lost this way — no git object, no filesystem copy, unrecoverable — and
  it was the cited source for most of the tooling spec's own findings.
- `TODOS.md` — tracked at repo root, but not really a work-item tracker.
  It is a from-scratch audit ("every item checked against the working
  tree ... not taken from a spec's own status line") because specs and
  plans under `docs/` never carry trustworthy status themselves. The
  file explicitly flags plans with every checkbox unticked despite being
  fully implemented, and calls this out as a habit that needs fixing.

There is also no GitHub Issues usage — only merged PRs — so there is no
live "what's outstanding" view anywhere except `TODOS.md`'s manual
audits.

## Goals

- One tracked, permanent location for reference material
  (`references/`), with the licensing duplication fixed.
- Specs and plans tracked in git, so nothing can be silently lost again.
- Specs and plans carry their own trustworthy status, updated at the
  workflow checkpoints that already exist (brainstorming → approval →
  execution → merge), so aggregate status is a cheap read, not an
  expensive audit.
- A single, small index of outstanding work, kept current incrementally
  instead of rebuilt from scratch.

## Design

### A. Directory structure

| Location | Purpose | Change |
|---|---|---|
| `references/` | Permanent, tracked, skill-facing reference docs | No change in role. Licensing duplication fixed (below). |
| `docs/superpowers/specs/` | Dated design specs | Un-gitignore. Tracked from now on. |
| `docs/superpowers/plans/` | Dated implementation plans | Un-gitignore. Tracked from now on. |
| `docs/` (loose files directly in it) | Roadmap/review docs that aren't spec- or plan-shaped | Un-gitignore. Stays tracked at this level, not nested further. |
| `documentation/` | — | Deleted. Its one file merges into `references/licensing.md`. |
| `TODOS.md` (root) | Work-item status | Same name/location — it's already the discoverable convention — but its contents change (see B). |

This keeps the paths the `brainstorming` and `writing-plans` skills
already default to (`docs/superpowers/specs/`, `docs/superpowers/plans/`),
so no per-project path override is needed — we only stop gitignoring
them.

### B. Status tracking mechanism

Every spec and plan gets a status line near the top:

```
**Status:** Draft | Approved | In Progress | Done | Superseded | Abandoned
**Last updated:** YYYY-MM-DD
```

This is updated at checkpoints the Superpowers workflow already has:
`Draft` when brainstorming writes it, `Approved` on sign-off,
`In Progress` once `writing-plans`/execution starts, `Done` when
`finishing-a-development-branch` merges it. Plans already tick per-task
checkboxes as they execute; the status line is the one-line summary of
that.

`TODOS.md` becomes a thin index, not an audit: a table of
doc → type → status → priority → one-line pointer, plus a short "still
open" section filtered from that table. When a spec/plan's status line
changes, `TODOS.md` gets a one-line edit to match — it is not rebuilt
from scratch again. The current `TODOS.md` content is not wasted: it is
already the correct, verified answer as of 2026-09-06/07, so migrating
it is a reformat of existing, already-audited findings, not new audit
work.

### C. Migration steps

1. **Fix the licensing duplication.** Merge `documentation/licensing.md`'s
   content into `references/licensing.md` (currently a stub pointing at
   it), delete `documentation/licensing.md` and the now-empty
   `documentation/` directory, update `README.md`'s reference to
   `documentation/licensing.md`.
2. **Delete `docs/licensing.md`.** An untracked, superseded one-off task
   brief — everything it asked for already exists (`CONTENT-LICENSE.md`,
   `THIRD-PARTY-NOTICES.md`, `metadata/licenses.yml`,
   `references/licensing.md`). **Correction (2026-09-07, found by the final
   whole-branch review):** this was wrong — the tooling-hardening spec's own
   scope paragraph cites it. That citation is now annotated instead, since
   the file itself is unrecoverable (no git object, no filesystem copy).
3. **Un-gitignore `docs/`**: remove the `docs/` line and the now-redundant
   force-add negations from `.gitignore`, then add and commit:
   - `docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md`
   - the active engine tooling and vNext specs
   - `ReportKit vNext — AI Publication System Minimal Implementation Spec.md`, renamed with a date prefix and moved into `docs/superpowers/specs/` for consistency
   - this spec itself
4. **Add status headers** to the active specs/plans, using
   `TODOS.md`'s own already-verified assessments (transcription, not a
   new audit):
   - tooling-hardening spec → `Approved, implementation slice landed`
   - vNext spec → `Draft / roadmap, not started`
5. **Rewrite `TODOS.md`** as the thin index from section B, seeded from
   its current (already-correct) content.
6. **Update `.gitignore`'s comment** to state the new policy: specs and
   plans are tracked; anything genuinely disposable gets its own
   narrow ignore rule instead of a blanket `docs/` ignore.

Nothing here touches `references/*.md` besides the licensing merge, and
nothing touches code.

## Non-goals

- No change to how `references/` content is authored or organized
  beyond the licensing merge.
- No adoption of GitHub Issues for work-item tracking (considered,
  deferred — no issues are in use today and this would be a bigger
  process shift than the immediate cleanup needs).
- No changes to the Superpowers skill files themselves (e.g. wiring a
  status-update step into `finishing-a-development-branch`). The
  convention is documented and followed by hand for now; formalizing it
  in the skill is a separate, later decision.

## Testing

This is a documentation/process change with no executable behavior.
Verification is: `docs/` files are tracked (`git ls-files` shows them),
`documentation/` no longer exists, `references/licensing.md` contains
the full licensing model (not a stub), `README.md` no longer points at
a deleted file, and `TODOS.md` matches the table format in section B.
