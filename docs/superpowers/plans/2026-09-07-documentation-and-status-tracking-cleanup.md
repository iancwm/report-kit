# Documentation and Status-Tracking Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Done — merged to `main` via PR #7 (`965443b`) on 2026-09-07.
**Last updated:** 2026-09-07

**Goal:** Consolidate `references/`, `documentation/`, `docs/`, and `TODOS.md` into one tracked structure where specs/plans carry their own trustworthy status and `TODOS.md` is a cheap index instead of a from-scratch audit.

**Architecture:** Four sequential, independently-committable tasks: (1) fix the `references/`↔`documentation/` licensing duplication, (2) stop gitignoring `docs/` and drop a stray superseded file, (3) normalize and add status headers across the four existing specs/plans (correcting two now-false claims found along the way) and move them into git, (4) rewrite `TODOS.md` as the thin index. No code changes; every verification step is a shell command, not a test suite.

**Tech Stack:** Git, bash. No application code is touched.

**Spec:** `docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md` — read it first; this plan implements it section-for-section (A→structure, B→status mechanism, C→migration steps).

## Global Constraints

- Do not touch `references/*.md` content except the licensing merge and the one `repository-boundary.md` table cell named in Task 1.
- Do not touch any file outside `docs/`, `documentation/`, `references/licensing.md`, `references/repository-boundary.md`, `README.md`, `.gitignore`, and `TODOS.md`.
- Every status line you write must come from a claim already verified in `TODOS.md` or from a `git`/`grep` check you run yourself in this plan — never guess or carry forward a spec's own unverified claim (this is the exact failure mode this plan fixes).
- Commit after each task. Use the attribution footer already established for this repo:
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`

---

### Task 1: Fix the `references/` ↔ `documentation/` licensing duplication

**Files:**
- Modify: `references/licensing.md` (replace stub with the merged model)
- Delete: `documentation/licensing.md`, then remove the now-empty `documentation/` directory
- Modify: `README.md:90-91`
- Modify: `references/repository-boundary.md:26`

**Interfaces:** N/A — documentation-only.

- [ ] **Step 1: Confirm the current duplication**

Run:
```bash
cat references/licensing.md
cat documentation/licensing.md
```
Expected: `references/licensing.md` is a 7-line stub pointing at `../documentation/licensing.md`; `documentation/licensing.md` holds the real model (the scope table, contributor guidance, `metadata/licenses.yml` note).

- [ ] **Step 2: Replace `references/licensing.md` with the merged content**

Overwrite `references/licensing.md` with:

```markdown
# Licensing reference

ReportKit separates three things that travel together in a repository but do
not share one licence:

| Scope | Default terms |
|---|---|
| Source code and build tooling | GPL-3.0-or-later; see `LICENSE` |
| Original publication prose and diagrams | CC BY 4.0; see `CONTENT-LICENSE.md` |
| Code examples and third-party assets | The terms stated by their author or upstream source |

Contributors adding publication content should identify whether it is original
or adapted, provide the source and attribution for adaptations, and avoid
presenting third-party material as CC BY content. For a new font, image,
dataset, template, or code sample, add its licence and required attribution to
`THIRD-PARTY-NOTICES.md` and keep the notice close to the asset where practical.

The machine-readable defaults live in `metadata/licenses.yml`. Publication
builds validate that file and inject a rights notice into generated front
matter. A generated notice covers original content only; it does not relicense
code examples or third-party material.

New assets need a source, licence, attribution text, and any restrictions
recorded before they enter a publication.
```

- [ ] **Step 3: Delete `documentation/licensing.md` and the directory**

Use `git rm`, not plain `rm` — a plain `rm` here would make the `git rm` in
Step 7 fail with "no such file" since the working-tree copy would already
be gone.

Run:
```bash
git rm documentation/licensing.md
rmdir documentation
```
Expected: `git rm` prints `rm 'documentation/licensing.md'` and removes it
from disk; `rmdir` then succeeds because the directory is empty;
`test -d documentation` now exits 1.

- [ ] **Step 4: Fix `README.md`'s dangling reference**

In `README.md`, find:
```markdown
The machine-readable defaults are in `metadata/licenses.yml`; contributor
requirements are documented in `documentation/licensing.md`.
```
Replace with:
```markdown
The machine-readable defaults are in `metadata/licenses.yml`; contributor
requirements are documented in `references/licensing.md`.
```

- [ ] **Step 5: Fix `references/repository-boundary.md`'s table row**

In `references/repository-boundary.md`, find:
```markdown
| `references/`, `documentation/`, `metadata/` | `publication.yaml` — title, author, version, identity |
```
Replace with:
```markdown
| `references/`, `metadata/` | `publication.yaml` — title, author, version, identity |
```

- [ ] **Step 6: Verify**

Run:
```bash
test ! -d documentation && echo "documentation/ gone"
grep -rn "documentation/" --include="*.md" . || echo "no remaining references"
grep -n "New assets need a source" references/licensing.md
```
Expected: `documentation/ gone`; the grep for `documentation/` prints `no remaining references` (or only unrelated matches you inspect and confirm are unrelated); the last grep finds one line.

- [ ] **Step 7: Commit**

```bash
git add references/licensing.md references/repository-boundary.md README.md
git commit -m "docs: merge documentation/licensing.md into references/licensing.md

Both files were added in the same commit (4b79642) with references/
holding only a stub pointer. Consolidate into the one tracked
reference-docs location and drop the now-redundant documentation/ dir.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Stop gitignoring `docs/` and drop the stray superseded file

**Files:**
- Modify: `.gitignore:220-223`
- Delete: `docs/licensing.md`

**Interfaces:** N/A — documentation-only.

- [ ] **Step 1: Confirm `docs/licensing.md` is superseded and untracked**

Run:
```bash
git log --all --oneline -- docs/licensing.md
git status --short --ignored docs/licensing.md
```
Expected: the log is empty (never committed); status shows `!!` (ignored, untracked). Its content is a one-off task brief whose every requested deliverable already exists: `CONTENT-LICENSE.md`, `THIRD-PARTY-NOTICES.md`, `metadata/licenses.yml`, `references/licensing.md` (fixed in Task 1).

- [ ] **Step 2: Delete it**

```bash
rm "docs/licensing.md"
```

- [ ] **Step 3: Update `.gitignore`**

Find:
```
# Superpowers process docs (brainstorming specs, plans) — planning
# scaffolding, not part of the shipped skill. Skill-facing reference docs
# live in tracked references/, not here.
docs/
```
Replace with:
```
# docs/ (Superpowers specs and plans, plus roadmap/review docs) is tracked
# in git — see
# docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md
# for why. Anything genuinely disposable gets its own narrow ignore rule
# here instead of a blanket docs/ ignore.
```

- [ ] **Step 4: Verify**

Run:
```bash
test ! -f "docs/licensing.md" && echo "stray file gone"
```
Expected: `stray file gone`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: stop gitignoring docs/, drop superseded licensing task-brief

docs/licensing.md was an untracked, never-committed task brief; every
deliverable it asked for already exists. Un-ignoring docs/ is step 1 of
tracking specs/plans in git instead of losing them (see
docs/tooling-improvement-spec-draft.md's fate in TODOS.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Normalize status headers, move the vNext spec, and track everything under `docs/`

**Files:**
- Modify: `docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md:1-5`
- Rename: `docs/ReportKit vNext — AI Publication System Minimal Implementation Spec.md` → `docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md`, then modify its header
- (already tracked, no change needed) `docs/superpowers/specs/2026-09-07-documentation-and-status-tracking-cleanup-design.md`
- (already tracked, no change needed) `docs/superpowers/plans/2026-09-07-documentation-and-status-tracking-cleanup.md` (this file)

**Interfaces:** N/A — documentation-only.

- [ ] **Step 1: Normalize the tooling-hardening spec's status header**

In `docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md`, find:
```markdown
# ReportKit Tooling Hardening

**Status:** Approved design (scope confirmed with user 2026-09-06); amended
2026-09-06 — see Amendments below. Not yet implemented: `git log main..tooling`
is empty.
```
Replace with:
```markdown
# ReportKit Tooling Hardening

**Status:** Approved, implementation slice landed on `main` (not the
`tooling` branch named below — see `TODOS.md`'s P0-2 for why that branch is
stale).
**Last updated:** 2026-09-07

Amended 2026-09-06 — see Amendments below.
```
(This drops the old "Not yet implemented" claim, which `git log main..tooling` being empty never actually disproved — the work landed on `main` directly, not on `tooling`. This is the exact kind of stale, unverified status line the cleanup spec exists to fix.)

- [ ] **Step 2: Move and rename the vNext spec**

```bash
mv "docs/ReportKit vNext — AI Publication System Minimal Implementation Spec.md" \
   "docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md"
```

- [ ] **Step 3: Add a status header to the moved vNext spec**

In `docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md`, find:
```markdown
# ReportKit vNext — AI Publication System

## Objective
```
Replace with:
```markdown
# ReportKit vNext — AI Publication System

**Status:** Draft / roadmap, not started. Substantial overlap with the
tooling-hardening spec (vNext §7–8 ≈ tooling D6, §9 ≈ tooling D4, §12 ≈
tooling C2 plus `SKILL.md`'s primitive table) — reconcile the two before
starting Phase 1.
**Last updated:** 2026-09-07

## Objective
```

- [ ] **Step 4: Verify the header edits**

Run:
```bash
grep -A1 "^\*\*Status:\*\*" \
  docs/superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md \
  docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md
```
Expected: each file prints a `**Status:**` line immediately followed by a `**Last updated:** 2026-09-07` line (or the line directly after it in the plan's case — confirm each visually).

- [ ] **Step 5: Track everything under `docs/`**

```bash
git add docs/
git status --short
```
Expected: every active file under `docs/` shows as staged (`A`), including the renamed vNext spec (shown as a rename if git detects it). Nothing under `docs/` remains untracked.

- [ ] **Step 6: Commit**

```bash
git commit -m "docs: normalize spec/plan status headers, track docs/ in git

- Tooling-hardening spec: correct the 'not yet implemented' claim — the
  work landed on main, not the (stale) tooling branch.
- Move the vNext spec into docs/superpowers/specs/ for consistency and
  give it a status header.
- git add docs/ now that it's no longer ignored (see previous commit).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Rewrite `TODOS.md` as a thin index

**Files:**
- Modify: `TODOS.md` (full replacement)

**Interfaces:** N/A — documentation-only.

- [ ] **Step 1: Replace `TODOS.md`**

Overwrite `TODOS.md` with:

```markdown
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
| [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](docs/superpowers/specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md) | Draft / roadmap, not started | P3 |

## Open work

### P0

- **P0-1 — re-cut `tooling` from `main`.** It's 0 ahead / 17 behind `main`. Re-cut before the next tooling implementation slice.

### P1

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
```

- [ ] **Step 2: Verify**

Run:
```bash
wc -l TODOS.md
grep -c "^###" TODOS.md
```
Expected: a much shorter file than the ~307-line original; at least 6 `###` headings (P0/P1/P2/P3 plus Documents/Open work/Environment/History level-2 headings — adjust the count check by eye, the point is the file is scannable, not exhaustive).

- [ ] **Step 3: Commit**

```bash
git add TODOS.md
git commit -m "docs: rewrite TODOS.md as a thin index

Replaces the from-scratch working-tree audit with a table of doc ->
status -> priority plus a short open-work rollup, sourced from the
now-authoritative status headers on each spec/plan (see previous
commits) instead of re-verifying everything by hand.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final check

- [ ] Run `git log --oneline -5` and confirm four new commits (plus the earlier spec commit) on `chore/docs-and-status-tracking-cleanup`.
- [ ] Run `git status` and confirm a clean working tree.
- [ ] Run `git diff main --stat` to review the full shape of the change before opening a PR.
