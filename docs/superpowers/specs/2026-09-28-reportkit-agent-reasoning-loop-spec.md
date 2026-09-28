# ReportKit agent reasoning loop: target lock, scoped context, and target-aware gates

Status: proposed (open questions resolved 2026-09-28)
Date: 2026-09-28
Owner: engine

## 1. Problem

In cloud and mobile coding agents (ChatGPT Work, Claude Code on mobile/web,
Codex cloud), agents ask for a magazine feature, brief, book, or deck and get
back one of two things:

- **Default fallback.** A `technical-report/default` PDF. Sometimes it comes
  from a copied `REPORT_TEMPLATE.tex`, sometimes from a `theme=editorial`
  document that pdfLaTeX could not compile and the agent "fixed" by removing
  the theme.
- **Style mixing.** The correct class options, but the wrong grammar: a
  `feature-article` built from `\maketitle`, `redflag`/`decisionpoint`
  callouts, and `reportmatrix` diagrams, with no `featurecolumns`,
  `pullquote`, or exhibits. Or a slide deck built from report primitives.

`python_scripts/reportkit/editorial_audit.py` (PR #66) fixes the second
failure after the fact, and only for one target. This spec fixes the loop that
produces both failures, for every target.

Design premise: **an agent's context is not a reliable store of state.**
Cloud hosts truncate large files, compact conversations, reset sandboxes
between sessions (`references/troubleshooting.md` §Environment notes), and
often load only a skill's frontmatter until the model decides to read more.
Anything the loop depends on must therefore live on disk in the consumer
project, and the CLI must restate it on every call.

## 2. Diagnosis: where context is lost

Each finding cites the code or document that causes it.

### F1. The skill trigger describes only one target

`SKILL.md:3` describes the skill as "technical or analytical PDF reports and
slide decks". `SKILL.md:8-10` restates it as "technical reports". The
description never mentions magazine features, books, equity research, or
briefs. Hosts that load only the frontmatter, or that decide from it whether
to read further, frame the whole task as a technical report before the
selection table is ever read.

### F2. The selection table is buried under reference material for other targets

`SKILL.md` is 43.9 KB and 616 lines. The selection table is at lines 69–77.
Lines 140–611 (about 75% of the file) are diagram, algorithm, and chart
reference whose examples are all in the default-theme grammar
(`reportmatrix`, `reportflow`, `arraystate`, callouts). There are dozens of
worked LaTeX examples, and not one uses a feature, brief, or slide primitive.
Models imitate examples more than rules, so the long tail pulls authoring
toward the technical-report grammar whatever the table says.

### F3. The default target is silent, and the CLI reports it as a choice

- `reportkit init` writes a `publication.yaml` stub with no `document:` block
  (`python_scripts/reportkit/initialization.py:19-31`). The first-run step
  "record `publication_type` and `theme`" (AGENTS.md step 1) has no
  placeholder to fill in.
- `resolve_document` silently falls back to `technical-report` / `default`
  (`python_scripts/reportkit/config.py:373-376`). No diagnostic separates
  "declared" from "defaulted".
- The always-loaded quickstart slice says *"The current target is
  technical-report/default/paged."* An agent reads that as a decision, not
  as the absence of one.

### F4. Two build paths, and only the Markdown one is gated

- `reportkit build` is the Markdown pipeline. It always generates
  `publication.tex` from `publication_pipeline/templates/<type>.tex`.
  `document.main: report.tex` is defaulted (`config.py:371`) but the build
  never reads it.
- Feature articles, equity research, and briefs are documented as
  hand-authored `.tex` (`SKILL.md:122`, `:581`, `:585`), yet no documented
  ReportKit command builds a direct `.tex` file through the gates.
- The fallback agents do find is `references/troubleshooting.md:46-50`, which
  prescribes `pdflatex report.tex` twice. Under pdfLaTeX, editorial,
  institutional-research, and executive documents fail (they need LuaLaTeX),
  and the cheapest "fix" an agent sees is deleting the theme option. The
  SKILL.md sentence about the regression suite (`:611`) says the same thing:
  pdflatex is the normal engine.
- Neither `\documentclass` options nor `publication.yaml` is checked against
  the other, so they can drift apart without any diagnostic.

### F5. The source mode each target needs is never stated

The Markdown directive surface (`python_scripts/reportkit/markdown_directives.py`)
has no directives for `featurecolumns`, `pullquote`, `featuresidebar`,
`featureexhibit`, or `openingvisual`. A feature article written in Markdown
therefore gets a `featureopening` followed by plain Pandoc prose: exactly the
editorial-in-name-only result the audit catches. No document says "this
target needs direct TeX" or "this target works in Markdown".

### F6. "Filtered" context still presents the whole engine as valid

- `reportkit context --slice primitives --publication-type feature-article
  --theme editorial` returns about 176 primitives (about 50k estimated
  tokens). Only 15 are feature primitives. The rest include every callout,
  every diagram and algorithm primitive, `RKTitlePage`, and
  `risk_reward_chart`. The contract itself therefore tells the agent that
  mixing styles is valid.
- `references/feature-article-authoring.md` is 71 KB. Its actual guidance is
  lines 1–99. Everything from line 100 on is the generated contract for all
  primitives. `references/institutional-research-theme.md` has the same
  problem (72 KB, generated tail from line 182). On hosts that truncate or
  chunk reads, the "authoring reference" the selection table points to is
  mostly irrelevant, and the important part competes with it.

### F7. The authoring template is the same for every target

`context.py:183-187` emits the same skeleton for every target:
`\documentclass[...]` + `\title` + `\maketitle`. For a feature article,
brief, or equity note, this is the default-LaTeX opening that the target's
own opening primitive (`featureopening`, `briefheader`,
`researchfrontpage`) is meant to replace.

### F8. Nothing persists the user's intent

The user's exact request ("like the attached Economist PDF", "a
consulting deck") exists only in the conversation. After a compaction, a
sandbox reset, or a new mobile session, the agent re-derives the target from
whatever files remain, and those files default to technical-report (F3).
The only intent record on disk is `editorial-brief.json`, and only
feature articles have one.

### F9. Verification is after the fact, specific to one target, and optional

- The composition audit exists only for `feature-article`.
- `build-report.json`'s `selection` is recorded but never checked against
  anything. AGENTS.md step 4 asks the agent to "inspect" it.
- Visual review assumes the host can render and view images. Many mobile
  hosts cannot, and nothing tells the agent to say so instead of claiming
  a match.

### F10. The instructions are negative, scattered, and contradictory

The rule against using the default template appears in four places:
AGENTS.md, `SKILL.md:62-67`, `SKILL.md:83-86`, and implicitly in
troubleshooting. Some are phrased as prohibitions ("Do not copy
`REPORT_TEMPLATE.tex` …"), which prime the forbidden file. The engine
guidance also conflicts: troubleshooting says pdflatex; SKILL.md says the
theme picks the engine.

### F11. "Type" and "theme" read as synonyms

`publication_type` (the structure: which primitives and page grammar) and
`theme` (the look: typography, colour, spacing tokens) are orthogonal, but
the names do not say so. Users and agents conflate "editorial" with
"feature article". Yet `editorial` also styles `book`, and
`feature-article` is written so that another theme could restyle it
(`tests/test_editorial_theme.py`). Asked for "an editorial report", an
agent can reasonably produce `technical-report` + `theme=editorial`
(rejected by the registry) or `book/editorial`. Or it can produce a
feature-article source using report primitives because "the theme styles
them". This conflation is also why theme-level styling of callouts is
mistaken for permission to use them in a feature.

Remedy (folded into §4.5 and §4.6): the selection table and the quickstart
slice present each row as **"format (structure) × look (theme)"**, with
one line explaining the distinction. Every diagnostic names both axes
(`structure=feature-article look=editorial`). `target set` accepts
natural-language aliases (`magazine`, `feature`, `editorial article`) and
maps them to the pair, echoing the mapping for confirmation.

### Root cause

The target is a *decision*, but ReportKit treats it as a *default*. Nothing
records the decision durably, nothing restates it at each step, and nothing
rejects work that contradicts it. Every downstream document and command then
leans toward the default grammar.

## 3. Goals and non-goals

Goals

1. The publication target is declared once, persisted in the consumer
   project, and restated by every CLI command.
2. An undeclared or contradicted target fails the build before TeX runs,
   with a remediation that names the command to fix it.
3. The context an agent loads for a target contains only that target's
   grammar.
4. Direct `.tex` and Markdown both build through `reportkit build`, with the
   same gates.
5. Every target has a composition check, not just `feature-article`.
6. An agent that loses its context can recover the loop's state from one
   command.

Non-goals

- Judging rendered aesthetics automatically. Manual visual review stays
  required and is reported honestly when the host cannot do it.
- Adding Markdown directives for every feature primitive. This spec only
  requires that each target *declare* its supported source modes. Adding
  directives is a separate spec.
- Changing any theme's visual output.

## 4. Design

### 4.1 The reasoning loop as an explicit state machine

```
SELECT → LOCK → SCAFFOLD → AUTHOR → CHECK → BUILD → REVIEW → DELIVER
            ↑__________________ status (re-hydrate) _______________|
```

| Step | Command | Persisted artefact | Gate |
| --- | --- | --- | --- |
| SELECT | `reportkit context --slice quickstart --json` | — | The agent maps the request to a row. If more than one row plausibly fits, it asks the user. |
| LOCK | `reportkit target set --publication-type T --theme H --source-mode tex\|markdown --request "<verbatim user ask>" [--reference PATH]` | `publication.yaml` `document:` block + `.reportkit/intent.json` | Rejects incompatible type/theme pairs and unsupported source modes. |
| SCAFFOLD | `reportkit init … --publication-type T --theme H` (or `reportkit scaffold`) | Target-specific starter + composition brief stub | Refuses to overwrite existing manuscript. |
| AUTHOR | Agent edits using `reportkit context --slice primitives` (target-scoped) | Source files | — |
| CHECK | `reportkit check --json` (runs the composition audit for the target) | — | `RK_TARGET_UNDECLARED`, `RK_TARGET_MISMATCH`, `RK_PRIMITIVE_OFF_TARGET`, composition diagnostics |
| BUILD | `reportkit build --json` (Markdown **or** direct TeX) | `build-report.json` with `selection.declared_by` | Same gates as CHECK, plus the log gate |
| REVIEW | `reportkit render` + `reportkit review --json` | `build/review.json` checklist | Records `visual_review: done\|unavailable` |
| DELIVER | `reportkit status --json` | — | The delivery message must quote the status's target line |

Every command's human and JSON output **starts with one target line**:

```
TARGET feature-article/editorial/paged  source=tex  declared=publication.yaml  intent=.reportkit/intent.json
```

and ends with `next_step`: the next command in the table. Agents obey
local, repeated signals more reliably than one instruction read at the start
of the session, so the loop lives in the tool output, not in the prose.

### 4.2 Target lock (fixes F3, F8)

- New `reportkit target set|show` subcommand. `set` writes:
  - the `document:` block in `publication.yaml` (`publication_type`,
    `theme`, `source_mode`, and `main` for TeX mode);
  - `.reportkit/intent.json`:
    ```json
    {
      "schema_version": "1.0.0",
      "request": "Magazine-style feature on port automation, like the attached QA PDF",
      "publication_type": "feature-article",
      "theme": "editorial",
      "source_mode": "tex",
      "visual_reference": "assets/reference/qa.pdf",
      "composition_brief": "composition-brief.json",
      "decided_by": "user-confirmed | agent-inferred",
      "locked_at": "2026-09-28T10:00:00Z"
    }
    ```
- `reportkit init` gains `--publication-type`, `--theme`, and `--source-mode`.
  Without them, it writes an explicit placeholder that `check` rejects:
  ```yaml
  document:
    publication_type:   # REQUIRED: run `reportkit target set` (see SKILL.md selection table)
    theme:
  validation:
    require_declared_target: true
  ```
- `resolve_document` records `declared_by: publication.yaml | tex-class-options | default`.
  When `require_declared_target` is true and `declared_by == default`, `check`
  and `build` fail with `RK_TARGET_UNDECLARED` (exit 3).
  **Compatibility:** projects without the key keep today's behaviour and get
  a non-blocking warning. Only new `init` output opts in. This is a minor,
  additive contract change.
- The quickstart slice replaces "The current target is …" with one of:
  - `TARGET feature-article/editorial (declared in publication.yaml)`, or
  - `TARGET NOT DECLARED — the build will refuse. Pick a row below and run reportkit target set.`

### 4.3 One gated build for direct TeX (fixes F4)

- `reportkit build` honours `document.source_mode: tex` and `document.main`.
  It stages the file, sets `TEXINPUTS` to the engine's `latex_templates/`,
  selects the engine from the theme, and runs the same log gate, render, and
  manifest steps as the Markdown path.
- `RK_TARGET_MISMATCH` (exit 3) is raised before TeX runs when the
  `\documentclass` options in `document.main` disagree with
  `publication.yaml`, or when the class options are missing.
- `RK_ENGINE_DOWNGRADE` (blocking) is raised when a theme that requires
  LuaLaTeX is invoked with pdflatex. Its remediation says: "install LuaLaTeX
  / run setup_tex.sh; do not change the theme".
- Replace the raw `pdflatex` steps in `references/troubleshooting.md` and the
  engine sentence in `SKILL.md` with `reportkit build`. Keep raw engine
  commands only in an "engine developers" section.

### 4.4 Source-mode contract per target (fixes F5)

Add `source_modes` to each `PUBLICATION_TYPES` entry and expose it in the
selection and quickstart slices:

| Target | `tex` | `markdown` | Notes |
| --- | --- | --- | --- |
| technical-report | yes | yes | |
| equity-research | yes | yes (fragments) | |
| executive-brief | yes | yes | |
| feature-article | **yes (required for editorial composition)** | opening only | Markdown lacks feature layout directives |
| book | yes | yes | |
| presentation | yes | yes (directives) | |

`target set --source-mode markdown` for `feature-article` fails with
`RK_SOURCE_MODE_UNSUPPORTED`. The remediation points to TeX mode, so the
limitation surfaces at LOCK time instead of in the rendered PDF.

### 4.5 Target-scoped context (fixes F2, F6, F7)

- **Primitive scoping.** Each primitive gets a `targets` field (publication
  types plus a role: `native`, `allowed`, or `discouraged`). The primitives
  slice returns only `native` and `allowed` primitives for the resolved
  target. For feature-article, that is the feature primitives, `featuretable`,
  `diagram` with a curated subset, and charts via `rkv.apply_theme("editorial")`.
  Callouts become `discouraged` for feature-article. `reportkit-theme-editorial.sty`
  does style them (lines 91–100, for `book/editorial`), so they render
  correctly, but they belong to the report grammar, not the feature
  grammar. `featuresidebar` covers the feature role.
  Target budget: **≤ 8k estimated tokens** per target slice, enforced by a
  test.
- **Authoring template per target.** The `authoring.document_template` field
  comes from the target's canonical example skeleton (preamble plus opening
  primitive plus one example of each native role). The current `\maketitle`
  body stays only for `technical-report`.
- **Generated tails.** `docs --check` regenerates the contract tables in
  `feature-article-authoring.md`, `institutional-research-theme.md`, and
  `presentation-authoring.md` **filtered to that target's `native`
  primitives**. The full inventory lives only in
  `references/primitive-contract.md`. Budget: each target authoring
  reference ≤ 20 KB, enforced by a test.

### 4.6 SKILL.md restructured as a router (fixes F1, F2, F10)

- Frontmatter `description` names every target: *"…technical reports,
  equity research, executive briefs, magazine-style feature articles, books,
  and consulting/venture slide decks…"*.
- Body ≤ 12 KB, in this order:
  1. **The loop** (the §4.1 table, as commands).
  2. **Selection table**, extended with `source_mode`, engine, worked
     example, composition brief, and "reference to read next".
  3. **Stop rules**, stated positively and exactly once:
     - "The build refuses an undeclared target. Declare it; do not accept the default."
     - "If LuaLaTeX is missing, fix the environment; keep the theme."
     - "Use only primitives listed by `context --slice primitives` for your target."
     - "If you cannot view rendered pages, say so in the delivery message."
  4. **Writing for the decision** (unchanged, target-neutral).
  5. A pointer table to per-target and per-topic references.
- Move the diagram, algorithm, visual-grammar, and chart reference
  (current lines 140–611) into `references/diagrams-and-algorithms.md`,
  `references/charts.md`, and `references/visual-grammar.md`. Mark them as
  technical-report/book/brief grammar. Feature and presentation references
  link to them only for the specific allowed subset.
- AGENTS.md shrinks to about 10 lines: "read SKILL.md; the loop is
  enforced by the CLI; follow each command's `next_step`." The duplicated
  selection rules are removed.

### 4.7 Composition briefs for every target (fixes F9; generalises `editorial_audit.py`)

- Rename the concept to **composition brief** (`composition-brief.json`),
  keyed by publication type. `editorial-brief.json` stays accepted as an
  alias.
- Refactor `editorial_audit.py` into `composition_audit.py` with a
  per-target role registry. It uses the same inventory, required-roles,
  local-style, and manual-review structure:

  | Target | Example roles |
  | --- | --- |
  | feature-article | `openingvisual`, `dropcap`, `featurecolumns`, `pullquote`, `featuresidebar`, `graphic-exhibit`, `full-width-exhibit` (existing) |
  | equity-research | `researchfrontpage`, `ratingstrip`, `whatschanged`, `exhibit`, `financialtable`, `scenario-cases` |
  | executive-brief | `briefheader`, `decisionpoint`, `exhibit`, `briefactions`, `briefsources` |
  | presentation | `titleslide`, `assertionslide`, `evidenceslide`, `sectiondivider`, `closingslide`, dense-layout mix |
  | book | `bookdetails`, `bookpart`, `bookappendix`, `bookreferences` |
  | technical-report | optional; `diagram`/callout counts |

- Add two universal checks to every audit, both reading the Markdown
  pipeline's generated TeX or the direct `.tex`:
  - `RK_PRIMITIVE_OFF_TARGET`: a primitive marked `discouraged` or not
    listed for the target (for example `\maketitle` or `redflag` in a
    feature article, or `reportmatrix` bare on a slide). Warning by default;
    blocking when the brief sets `"strict": true`.
  - `RK_LOCAL_STYLE`: the existing forbidden-command scan, applied to every
    target.
- `reportkit check` runs the audit automatically when the brief referenced
  from `intent.json` exists. `scaffold` writes a brief stub copied from the
  target's worked example, with `visual_reference` blank. A blank reference
  gives a warning that names the field.

### 4.8 Re-hydration and delivery (fixes F8, F9)

- `reportkit status --json` prints the target line, the intent (the
  verbatim request and reference), the brief's pass/fail status, the last
  successful step with its timestamp from `build/` artefacts, open
  diagnostics, `visual_review` state, and `next_step`. SKILL.md says: *"After
  any context reset, or before your final message, run `reportkit status`."*
- `reportkit review --json` writes `build/review.json`. It holds a
  per-page checklist derived from the brief's manual-review items, plus
  `visual_review: done | unavailable`. The agent sets `unavailable` when
  it cannot view images. `status` then prints a mandatory delivery caveat.
- `build-report.json` gains `selection.declared_by` and
  `selection.matches_intent`. `inspect` fails when the built target differs
  from `intent.json`.

### 4.9 Agent-behaviour evaluation

Add `tests/agent_evals/` with a scripted, host-neutral harness. It runs a
small set of prompts through a CLI-driven agent loop. It is optional in CI
and runs on demand:

- "Write a magazine-style feature about X, like this reference" → the
  resulting `build-report.json` `selection` must be
  `feature-article/editorial`, and the audit must pass.
- "A 4-page decision brief for the CFO" → `executive-brief/*`.
- "A 10-slide consulting deck" → `presentation/executive`.
- A context-reset variant: stop after AUTHOR, start a fresh agent with only
  "continue the publication in <dir>". The result must keep the same target.

Deterministic unit tests cover everything the harness relies on (§5), so
releases do not depend on model runs.

## 5. Acceptance criteria

1. `reportkit init <dir>` without target flags produces a project whose
   `reportkit check` exits 3 with `RK_TARGET_UNDECLARED`. With flags, the
   check passes the target gate.
2. Projects created before this change (no `require_declared_target`) build
   exactly as today and emit one non-blocking `RK_TARGET_IMPLICIT` warning.
3. The quickstart slice never says "current target is …" for an undeclared
   project. It stays ≤ 2,000 estimated tokens and includes the selection
   table with source modes.
4. A direct `.tex` project with `source_mode: tex` builds via `reportkit
   build`, and its `build-report.json` `selection` matches the class options.
   Changing the class option to `theme=default` without changing
   `publication.yaml` fails with `RK_TARGET_MISMATCH` before TeX runs.
5. Forcing pdflatex on an editorial document yields `RK_ENGINE_DOWNGRADE`,
   and the remediation does not suggest changing the theme.
6. `context --slice primitives` for `feature-article/editorial` is ≤ 8k
   estimated tokens and lists no callout or algorithm primitive as `native`.
7. `feature-article-authoring.md` and `institutional-research-theme.md` are
   each ≤ 20 KB. `docs --check` enforces their target-filtered generated
   tables.
8. SKILL.md is ≤ 12 KB, its description names all six publication types,
   and the selection table appears in the first 60 lines.
9. The composition audit runs for every publication type. The existing
   `tests/test_editorial_audit.py` passes against the renamed module and
   the `editorial-brief.json` alias.
10. `reportkit status --json` reconstructs target, intent, and `next_step`
    from disk alone. A test deletes all in-memory state between calls.
11. `inspect` fails when `build-report.json` selection ≠ `intent.json`.
12. `adapters/openai/tools.json` is regenerated and exposes `target_set`,
    `status`, and `review`. The existing contract tests pass.

## 6. Phasing

| Phase | Scope | Fixes | Risk |
| --- | --- | --- | --- |
| P1 | Target lock, `init` flags, `RK_TARGET_UNDECLARED/IMPLICIT`, target line + `next_step` on all commands, quickstart wording, `status` | F3, F8 | Low: additive, opt-in blocking |
| P2 | Direct-TeX build path, `RK_TARGET_MISMATCH`, `RK_ENGINE_DOWNGRADE`, troubleshooting rewrite, `source_modes` | F4, F5 | Medium: touches `publication_build.py` staging |
| P3 | Primitive `targets` metadata, scoped slices, per-target authoring templates, filtered generated tails | F6, F7 | Medium: registry and contract minor bump (1.3.0) |
| P4 | SKILL.md router rewrite (structure × look framing), reference split, AGENTS.md trim, `target set` aliases | F1, F2, F10, F11 | Low code risk; high doc-drift risk, so gate with `docs --check` size tests |
| P5 | `composition_audit.py` generalisation, `RK_PRIMITIVE_OFF_TARGET`, `review` command, `matches_intent` | F9 | Medium: role registries per target need fixture validation |
| P6 | Agent-behaviour eval harness | Regression | Low |

Do P1 first. On its own, it removes the silent default that most failures
start from.

## 7. Decisions

1. **Feature articles written in Markdown are rejected** with
   `RK_SOURCE_MODE_UNSUPPORTED` until feature layout directives exist. This
   is decided (2026-09-28).
2. **Callouts are `discouraged` in `feature-article`.** A strict brief
   raises `RK_PRIMITIVE_OFF_TARGET` as blocking; otherwise it is a warning.
   They stay `allowed` in `book/editorial`. The editorial theme styles
   callouts for books, and that styling is not permission to use them in
   a feature. `featuresidebar` is the feature-grammar equivalent. See F11.
3. **`intent.json` stores the user's verbatim request.** It is decided
   (2026-09-28). The file lives only in the consumer project and never
   enters the engine repository.
