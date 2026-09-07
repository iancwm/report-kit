# ReportKit — Outstanding Work

**Compiled:** 2026-09-06
**Method:** Every item below was checked against the working tree, the branch
graph, or a compiled probe — not taken from a spec's own status line. Where a
spec and reality disagreed, reality won and the spec is cited as wrong.

**Source documents (all under `docs/`):**

| Document | Status | Keep? |
|---|---|---|
| `data-engineering-guide-publication-review.md` | Evidence + release gate for the 56-page build | Keep — release gate |
| `superpowers/specs/2026-09-06-reportkit-tooling-hardening-design.md` | Approved, ReportKit tooling slice implemented; guide content still pending | Keep — active |
| `superpowers/specs/2026-09-06-data-engineering-guide-content-design.md` | Approved, **~60% implemented** | Keep — active |
| `superpowers/plans/2026-09-06-reportkit-visual-grammar.md` | Written, **unexecuted** | Keep — active |
| `ReportKit vNext — AI Publication System Minimal Implementation Spec.md` | Roadmap, unimplemented | Keep — P3 |
| `licensing.md` | Source for tooling spec §E, implemented | Keep — P1 |

## Implementation update — 2026-09-06

The current working tree now contains the ReportKit-side hardening slice:
strict guide diagnostics, static validation, atomic page rendering, run
manifests, locked PyMuPDF tooling, long-form/Pandoc packages, PDF metadata and
language, diagram sizing and alternatives, the three C2 primitives, licensing
metadata/notices, and rendered-geometry regression tests.

**2026-09-07 update:** the harness was renamed `data_engineering_guide/` →
`publication_pipeline/`, stripped of every book-specific default, and wired
to build against an external `--source-root`/`--output-root`. The
branch-merge integration model described below is retired — see
[references/repository-boundary.md](references/repository-boundary.md) and
[references/migrating-content-branches.md](references/migrating-content-branches.md).
The guide content branch (`data-engineering-guide-content`) still needs to be
extracted into its own consumer repository; it has not been deleted.

---

## P0 — Nothing can ship until these are resolved

### P0-1. No branch can build the guide — resolved by extracting content to a consumer repo, not by merging branches

The manuscript and the build scripts live on different branches, and neither
branch has both:

| Branch | manuscript | fragments | scripts | vs `main` |
|---|---|---|---|---|
| `main` | 0 | 0 | 0 | — |
| `tooling` | 0 | 0 | 5 | 0 ahead, **17 behind** |
| `data-engineering-guide` | 0 | 0 | 12 | 0 ahead, 2 behind |
| `data-engineering-guide-content` | 13 | 14 | 0 | 3 ahead, 0 behind |

`data-engineering-guide-content` has the content and no builder.
`data-engineering-guide` has the builder and no content.

**This is no longer resolved by merging branches together.** The previous
resolution — documented in `data_engineering_guide/README.md` — instructed
assembling the tooling tree with `data-engineering-guide-content` inside one
checkout. That is the long-lived-content-branch pattern
[references/repository-boundary.md](references/repository-boundary.md) now
forbids: report-kit is a reusable engine, and a publication's manuscript does
not belong in it, on any branch.

The correct resolution is to **extract `data-engineering-guide-content`'s
manuscript and fragments into their own consumer repository**, add the
structure `publication_build.py` expects (`publication.yaml`, etc.), and
build it against a report-kit clone with `--source-root`/`--output-root`. The
recipe is in
[references/migrating-content-branches.md](references/migrating-content-branches.md).
This has not been done yet — the branch still exists, unextracted. The
harness itself (`publication_pipeline/`) already builds any external
manuscript this way; it carries its own minimal fixture
(`example_publication/`) so the pipeline is exercised in this repo's tests
without pretending a real manuscript is present here.

### P0-2. `tooling` is 17 commits behind `main` and holds a stale script set

`docs/superpowers/plans/2026-09-06-reportkit-visual-grammar.md` states
"Branch: `tooling`, off `main`". That is **not true today** — `tooling` is
0 ahead / 17 behind, and carries 5 script files against
`data-engineering-guide`'s 12.

Re-cut `tooling` from `main` before executing that plan, or the plan's line
references into `latex_templates/` will not match the files it edits. Fix the
plan's Global Constraints block at the same time.

### P0-3. Figure alt text is discarded at build time — fixed

`latex_templates/reportkit-diagrams.sty:54,:64` store the `diagram`
environment's `description=` key and **never read it**. Verified: a probe
figure's description appeared in no page text and in no object stream, while
its caption and source rendered normally.

All **14 of 14** tracked fragments set `description=`. The content spec's §D5
requires it. `publication-guidelines.md:377-390` mandates it. None of it
reaches a reader.

The diagram wrapper now emits `description=` as a PDF `/ActualText` span and
warns when it is missing. The interim trade-off is documented: alternatives
replace extraction of labels inside the diagram until tagged-PDF support is
available. → Tooling spec **B7**.
Note the trade-off recorded in B7: an `/ActualText` span *replaces* the text
it wraps, so diagram labels stop being extractable. Only tagging (B8) gives
both.

`type=` has the identical defect at `:50,:60` — stored, read by nothing.
Resolve it or document it; a stored-and-unread key is a trap.

### P0-4. `reportnetwork` draws fused nodes and reversed arrows, silently — fixed

`rk node` renders **89.370pt** wide (`text width=28mm` + `inner xsep=5pt` × 2);
the grid step at `reportkit-process.sty:117` is 3.15cm = **89.291pt**. Nodes
are 0.079pt wider than their spacing, so a four-node chain renders as one
fused bar with every arrowhead pointing backwards — declared `n1→n2`, drawn
`n1←n2`.

**The build exits 0 with an empty warning list.** `scripts/acceptance_check.sh`
greps TeX logs and is structurally incapable of catching this.

The default grid step is now wider than `rk node`, both axes are configurable,
and the rendered-geometry suite asserts visible clearance. → Tooling spec
**C1-2**.

---

## P1 — Required before public distribution

### Tooling spec (`2026-09-06-reportkit-tooling-hardening-design.md`) — implementation slice landed

- **A. Build correctness gate** — implemented in the guide harness: strict log gate (`check-build-log.py`),
  commit hook covering guide paths, one canonical full-document build. The
  retained logs from the reviewed build contain four overfull boxes.
- **B1.** `reportkit-pandoc.sty` — implemented; the compatibility layer is shared.
  currently copied verbatim in `build-section.sh:37-112` and `combine.sh:32-96`.
- **B2.** `reportkit-longform.sty` — implemented: contents page, front matter, page breaks,
  before every H1, running heads that match the page. Covers review P0-01,
  P0-02, P1-05, P2-01, P2-03 at the class level.
- **B3.** `reportkit.cls` PDF metadata + document language — implemented.
- **B5.** Release identity out of `combine.sh` — implemented with CLI/environment configuration,
  `\setreportkitversion{draft}` at `combine.sh:26-31`).
- **B6.** `width=`/`scale=` key on the `diagram` environment — implemented.
- **C1-1.** *Already fixed* by `1c00be3` — needs only a regression test, not a
  fix. The spec was written against pre-fix code. → plan **Task 1**.
- **C2.** Three new primitives: `reportstate`, `reportcompare`,
  `reporttimeline` — implemented with acceptance tests.
- **D1.** Declared, locked toolchain — implemented with `requirements.txt`, setup, and version reporting.
- **D2.** `validate-guide.py` — implemented and covered by tests.
- **D3.** Atomic page rendering — implemented.
- **D4.** Run manifest (`build-report.json`) — implemented with hashes, tool versions, commands, exit codes, diagnostics, and page counts.
- **D5.** Pandoc feature fixtures — implemented for lists, tables, fenced code, links, and footnotes.
- **D6.** Visual QA as a result, **including the bounding-box check** the
  review's P0-03 requires. Use **PyMuPDF only** — poppler (`pdfinfo`,
  `pdffonts`, `pdftoppm`) and `pypdf`/`pdfplumber` are **not installed** on
  current dev machines, so the review's own evidence method is not
  reproducible today. Implemented in `inspect_pdf.py`, with an atomic page
  contact sheet and deterministic media-box check.
- **E. Licensing** — `metadata/licenses.yml`, `CONTENT-LICENSE.md`,
  `THIRD-PARTY-NOTICES.md`, contributor guidance, and rights-notice injection
  are implemented.
- **B8. PDF accessibility tagging spike** — a time-boxed no-go is recorded in
  `references/accessibility-tagging.md`; the installed format lacks
  `\DocumentMetadata` support. Tagged structure remains a known limitation.

### Content spec (`2026-09-06-data-engineering-guide-content-design.md`)

Already implemented on `data-engineering-guide-content`: §A front matter, §B
overflowing paths, §C tables, §D2 source statements, §D3 (5 of 8 figures),
§E1 references.

Still open now that the relevant tooling is available:

- **§D1.** Recompose the nine narrow vertical figures with `width=`.
- **§D3.** Author the three remaining Tier 1 figures — join cardinality, event
  vs processing time, task recovery — using C2.
- **§D4.** Author two Tier 2 figures (reconciliation flow, serving surfaces) to reach
  **19 figures**, the top of the review's 16–19 range.
- **§E2.** Glossary/references page separation using B2.
- **§F.** Reading-load polish — key-takeaway boxes in recovered whitespace.

### Content follow-ups once tooling lands

- Retire the `\RKNode` hand-placement workaround in
  `fragments/fig-sec01-lifecycle.tex` — C1-1 has been fixed since `1c00be3`.
- Retire the per-node `text width=24mm` workaround in
  `fragments/fig-sec07-lineage.tex` — fixed by P0-4.

### Distribution package

- **Cover asset.** The review asserts an A4 cover exists in the workspace;
  **it does not exist in any branch of this repo.** Either produce one or drop
  the claim. Review P0-04 / P2-03.

---

## P2 — Polish after correctness and structure are stable

- **B4.** Contrast audit — the `Muted` header/footer colour
  (`reportkit.cls:44`) and the syntax palette against contrast requirements
  and a grayscale proof. Review P2-02.
- **P2-01.** Page rhythm — rebalance after the structural page breaks land.
- **P1-06.** Keep short code listings together (`samepage`/minipage), mark
  unavoidable splits.
- **F1.** Strict modes are implemented; **F2** measure-before-optimising remains.

---

## P3 — Roadmap

`ReportKit vNext — AI Publication System Minimal Implementation Spec.md`
proposes a Typer CLI, `publication.yaml`, structured diagnostics, chapter
builds, PDF inspection, build manifest, link/visualization registries, and a
publication skill.

**Substantial overlap with the tooling spec** — vNext §7–8 (PDF inspection,
page rendering) is the tooling spec's D6; vNext §9 (build manifest) is D4;
vNext §12 (visualization registry) is C2 plus `SKILL.md`'s primitive table.
Do not implement twice. Reconcile the two documents before starting Phase 1,
or fold vNext Phase 1–2 into the tooling spec.

### Backlog: a Copier template for consumer projects — not yet, revisit after vNext §4

`shell_scripts/bootstrap.sh` currently scaffolds a new consumer project
imperatively (mkdir + heredocs). A [Copier](https://copier.readthedocs.io/)
template would make that declarative and, unlike bootstrap.sh, support
`copier update` — pushing a later structural change out to every
already-generated content repo, not just new ones.

Deliberately deferred, not rejected:

- Its variable schema would substantially duplicate `publication.yaml`'s
  schema, which vNext §4 has not yet formalized (Pydantic validation is
  still unimplemented). Building a template now risks a second migration
  once that schema lands.
- It adds a `pip install copier` dependency. `bootstrap.sh` is deliberately
  zero-dependency bash+python3 so it works in locked-down agent sandboxes
  with no network — a constraint documented at length in its own comments
  (font harvesting, avoiding `apt-get`, avoiding backgrounded processes).
- Its real payoff — keeping a *fleet* of content repos in sync — is
  speculative with only `data-engineering-guide` as a consumer repo so far.

Revisit once vNext §4 settles `publication.yaml`'s schema and there is more
than one content repo to keep in sync. The natural shape then: a
`copier-template/` directory mirroring
[references/repository-boundary.md](references/repository-boundary.md)'s
recommended structure, with `bootstrap.sh`'s scaffolding step retired in
favor of `copier copy`.

---

## Housekeeping

### Stale documents — deleted 2026-09-06

Verified implemented and superseded by the working tree, then removed. Four
were untracked (and therefore unrecoverable); the fifth was tracked and is
recoverable from git history.

| Document | Evidence it is done |
|---|---|
| `superpowers/specs/2026-09-04-reportkit-as-claude-skill-design.md` | `SKILL.md`, `shell_scripts/bootstrap.sh`, `scripts/acceptance_check.sh`, `references/`, `.githooks/pre-commit` all present |
| `superpowers/plans/2026-09-04-reportkit-as-claude-skill.md` | Paired plan for the above (32 unchecked boxes, but every deliverable exists) |
| `superpowers/specs/2026-09-05-data-engineering-guide-visuals-design.md` | All nine section anchor figures present in `data_engineering_guide/fragments/` |
| `superpowers/plans/2026-09-05-data-engineering-guide-visuals.md` | Paired plan for the above (66 unchecked boxes, all nine figures exist) |
| `2026-09-06-reportkit-build-regression-remediation-spec.md` | `\rkcode` at `reportkit-diagrams.sty:45`; failure-path directory copy in `guide-build.py`. **Was tracked in git** — recoverable from history |

`docs/` now contains exactly the six documents listed in the source table at
the top of this file. Note that the tracked spec was removed on `main` only;
`data-engineering-guide-content` still carries it until that branch merges.

Note both older plans have **zero ticked checkboxes** despite their
deliverables existing. Plans in this repo are not being updated as they are
executed, which is why staleness had to be established from the working tree.
Worth fixing as a habit, or the same audit repeats next time.

### `docs/tooling-improvement-spec-draft.md` is gone and unrecoverable

Present at the start of the 2026-09-06 session (14,404 bytes, dated
2026-09-05), absent now. It is in **no git object on any branch** and **no
copy exists anywhere on the filesystem** — `docs/` is gitignored
(`.gitignore:223`), so an untracked deletion leaves nothing behind.

This matters because the tooling spec cites it as the source for its findings
1–11, which is most of sections A, D, and F. Those sections now have no
traceable origin document. Either reconstruct it from the tooling spec's own
summaries or accept the spec as the new source of record and stop citing it.

### `docs/` is gitignored by design

`.gitignore:223` excludes `docs/` as "Superpowers process docs (brainstorming
specs, plans) — planning scaffolding, not part of the shipped skill." One file
was force-added as an exception. Consequences to keep in mind:

- Specs and plans are **not backed up by git**. A deletion is permanent.
- This `TODOS.md` is at repo root and therefore **is** tracked.

Consider whether the specs that drive active work should stay unversioned.

### Toolchain gaps on the current dev machine

- `pdfinfo`, `pdffonts`, `pdftoppm` (poppler-utils): **not installed**
- `pypdf`, `pdfplumber`, PyMuPDF: **not installed** system-wide
- `accsupp.sty`: **not installed**, and `tlmgr install` fails — this checkout
  is TinyTeX on TL2025 against a TL2026 remote. Plan Task 4 has a hard stop
  for this.
- Libertinus fonts were not installed at session start; they were installed to
  `TEXMFHOME` (`~/.TinyTeX/texmf-local`) from
  `font_data/reportkit-libertinus-fonts.tar.gz` to run the probes.
