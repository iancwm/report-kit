# ReportKit Agent Reasoning Loop Implementation Plan (multi-agent)

**Status:** The Wave 0 contract and lanes A–F are merged to `main` via PR #77.
Lane G's agent-evaluation harness and the full acceptance matrix remain open.
**Last updated:** 2026-09-30

> **For agentic workers:** this plan is built for parallel execution. One
> agent lands **Wave 0** alone. After it merges, the **Wave 1 lanes** run
> concurrently, each in its own git worktree and branch. **Wave 2** is one
> integration agent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the publication target a persisted, restated, enforced decision
instead of a silent default, for every publication type. This covers target
lock, a gated direct-TeX build, target-scoped context, composition audits for
every target, and re-hydration from disk.

**Spec:** `docs/superpowers/specs/2026-09-28-reportkit-agent-reasoning-loop-spec.md`
(§ numbers below refer to it; F1–F11 are its findings; AC1–AC12 are its
acceptance criteria.)

**Tech stack:** Python 3.11+, argparse CLI (`python_scripts/reportkit/cli.py`),
PyYAML, pytest, ruff, LuaLaTeX/pdfLaTeX via `publication_pipeline/scripts/publication_build.py`.

## Implementation status

`main` contains the implementation and documentation work for lanes A–F, on
top of the merged Wave 0 contract. Lane G's deterministic oracle
harness and the four §4.9 scenarios are not implemented. The pytest/ruff suite,
AC1–AC12 matrix, fresh-project TeX builds, and legacy build comparison have no
recorded result here, so the plan's acceptance checklists remain open until
that evidence is recorded.

---

## 1. Why the plan is shaped this way

The spec's six phases (§6) touch a small set of **hotspot files** again and
again. If lanes edit them concurrently, most of the merge work is conflict
resolution:

| Hotspot | Touched by spec phases | Why it collides |
| --- | --- | --- |
| `python_scripts/reportkit/cli.py` (820 lines) | P1, P2, P5 | New subcommands, `check`/`build`/`inspect` gates, target line on every command |
| `python_scripts/reportkit/registry.py` `COMMAND_CONTRACT` | P1, P5 | New commands `target`, `status`, `review`; new `init` flags |
| `python_scripts/reportkit/diagnostics.py` `DIAGNOSTIC_DEFINITIONS` | P1, P2, P5 | Eight new `RK_*` codes |
| `python_scripts/reportkit/publications.py` `PUBLICATION_TYPES` | P2, P3, P4 | `source_modes`, aliases, per-target template pointer |
| `python_scripts/reportkit/version.py` | P3 | `CONTRACT_VERSION` 1.2.0 → 1.3.0 |
| `schemas/*.json` | P1, P2, P5 | `target`/`next_step` envelope fields, `selection.declared_by`, `matches_intent` |
| `adapters/openai/tools.json` | P1, P5 | Generated from `COMMAND_CONTRACT` |
| `SKILL.md`, `AGENTS.md` | P2, P4 | Rewritten wholesale in P4, edited piecemeal in P2 |

**The strategy is interface-first:**

1. **Wave 0 (one agent, serial).** Land every shared contract edit at once:
   diagnostic codes, command contract entries, schema fields, registry
   fields, and the CLI wiring. The wiring calls **stub hook modules** that
   return "no-op" values. After Wave 0, every hotspot above is frozen.
2. **Wave 1 (seven agents, parallel).** Each lane owns a disjoint set of
   files, mostly new modules behind the Wave 0 hooks. A lane may not edit a
   file it does not own. If a lane needs a contract change, it asks the
   coordinator (see §6), who lands it on `main` for everyone.
3. **Wave 2 (one agent, serial).** Regenerate generated artefacts, bump the
   contract version, run the full acceptance matrix, and update the CHANGELOG.

This departs from the spec's phase order on purpose. The spec's "do P1 first"
holds for *release* order. Lane A (P1) is the first lane to merge in Wave 1,
and it can ship on its own (§5).

---

## 2. Global constraints (every lane)

- Exit codes stay as in `cli.py:49-54`: `0` ok, `2` config, `3` validation,
  `4` compile, `5` environment, `70` internal. `RK_TARGET_UNDECLARED`,
  `RK_TARGET_MISMATCH`, and `RK_SOURCE_MODE_UNSUPPORTED` exit **3**.
  `RK_ENGINE_DOWNGRADE` exits **5** (environment; the fix is setup, not source).
- **Backward compatibility (AC2).** A `publication.yaml` without
  `validation.require_declared_target` builds exactly as today, plus one
  `RK_TARGET_IMPLICIT` warning. Nothing may turn a passing legacy project red.
- **All state lives on disk** in the consumer project: `publication.yaml`,
  `.reportkit/intent.json`, `composition-brief.json`, and `build/*.json`. No
  module may cache target state across CLI invocations.
- `intent.json` and composition briefs never enter this repository
  (`references/repository-boundary.md`). Test fixtures create them under
  `tmp_path`.
- Diagnostics are built with `make_diagnostic(kind, message, code=...)`.
  They are never hand-built dicts.
- Every lane's done condition includes:
  `python3 -m pytest -q` (the lane's tests plus the full suite, no TeX-marked
  skips turned into failures) and
  `ruff check python_scripts publication_pipeline scripts tests adapters toolchain`.
- No lane edits `SKILL.md`, `AGENTS.md`, or `references/troubleshooting.md`
  except **Lane F**, and no lane regenerates `adapters/openai/tools.json`
  except **Wave 0** and **Wave 2**.

---

## 3. Wave 0 — contract freeze (single agent, serial)

**Branch:** `loop/w0-contract`. **Estimated size:** medium, mostly
declarative. **Must merge before any Wave 1 lane starts.**

### 3.1 Files owned

`cli.py`, `registry.py` (the `COMMAND_CONTRACT` only), `diagnostics.py`,
`publications.py`, `schemas/*.json`, `adapters/openai/tools.json`, and the
new stub modules listed in 3.3.

### 3.2 Shared contract edits

- [ ] **Diagnostics.** Add a `target_contract` kind to `DIAGNOSTIC_DEFINITIONS`,
      and an `off_target` kind for composition findings. Register these codes
      with their remediation text, taken verbatim from the spec:
      `RK_TARGET_UNDECLARED`, `RK_TARGET_IMPLICIT` (warning),
      `RK_TARGET_MISMATCH`, `RK_ENGINE_DOWNGRADE`, `RK_SOURCE_MODE_UNSUPPORTED`,
      `RK_PRIMITIVE_OFF_TARGET`, `RK_LOCAL_STYLE`, and `RK_INTENT_MISMATCH`
      (for `inspect`, AC11). Each remediation names a command
      (`reportkit target set …`). `RK_ENGINE_DOWNGRADE`'s remediation must not
      suggest changing the theme (AC5).
- [ ] **Command contract.** In `COMMAND_CONTRACT`:
  - Add `target` (subcommands `set`/`show`; args `--publication-type`, `--theme`,
    `--source-mode`, `--request`, `--reference`, `--decided-by`,
    `--source-root`, `--json`).
  - Add `status` (`--source-root`, `--json`).
  - Add `review` (`pdf`, `--source-root`, `--visual-review {done,unavailable}`,
    `--json`).
  - Extend `init` with `--publication-type`, `--theme`, and `--source-mode`.
  - Rename `audit-editorial` to `audit` and keep `audit-editorial` as a
    listed alias.
- [ ] **Publication registry.** In `PUBLICATION_TYPES`, add
      `source_modes: {"tex": "supported" | "required", "markdown": "supported" | "fragments" | "opening-only" | "unsupported"}`
      per the §4.4 table. Add `aliases: [...]` (for example
      `feature-article: ["magazine", "feature", "editorial article"]`),
      `canonical_example: "latex_templates/examples/<dir>/"`, and
      `composition_brief_example`. These fields are data only; Wave 1 lanes
      read them.
- [ ] **Schemas.** Every CLI JSON envelope gains optional `target`
      (the TARGET line object: `publication_type`, `theme`, `renderer`,
      `source_mode`, `declared_by`, `intent_path`) and `next_step`
      (`{command, reason}`). In `reportkit-build-report.schema.json`,
      `selection` gains `declared_by` and `matches_intent`, and
      `BUILD_REPORT_SCHEMA_VERSION` moves 3 → 4 (optional fields only).
      Add new `reportkit-intent.schema.json`, `reportkit-status.schema.json`,
      and `reportkit-review.schema.json`.
- [ ] **Adapter.** Regenerate `adapters/openai/tools.json` via
      `adapters/openai/reportkit_tools.py`, so that `target_set`, `status`,
      and `review` exist (AC12, first half).

### 3.3 Stub hook modules (the parallelism seam)

Create each module with its **final public signature**, a docstring that
cites the spec section, and a no-op body. Wire every call site in `cli.py`
and `publication_build.py` now, so that Wave 1 lanes only fill bodies.

| Module (new) | Frozen signature | No-op behaviour | Filled by |
| --- | --- | --- | --- |
| `reportkit/target.py` | `@dataclass(frozen=True) TargetState(publication_type, theme, renderer, source_mode, main, declared_by, intent: dict \| None, require_declared: bool)`; `load_target(source_root) -> TargetState`; `set_target(source_root, **kw) -> tuple[TargetState, list[diag]]`; `resolve_alias(text) -> tuple[str, str] \| None`; `target_gate(state) -> list[diag]` | `load_target` wraps today's `resolve_document` with `declared_by="default"` when unset; gate returns `[]` | Lane A |
| `reportkit/loop.py` | `target_line(state) -> str`; `target_payload(state) -> dict`; `next_step(command, state, outcome) -> dict`; `LOOP_STEPS` tuple | returns `""`/`{}` | Lane B |
| `reportkit/tex_target.py` | `read_class_options(tex: Path) -> dict \| None`; `tex_gates(state, tex) -> list[diag]`; `engine_gate(state, requested_engine) -> list[diag]` | `None` / `[]` | Lane C |
| `reportkit/primitive_targets.py` | `role_for(primitive_name, kind, publication_type) -> Literal["native","allowed","discouraged","absent"]`; `ROLE_TABLE` | returns `"allowed"` for anything available today | Lane D |
| `reportkit/authoring_templates.py` | `document_template(publication_type, theme) -> str` | returns today's `\maketitle` skeleton (moved verbatim from `context.py:183-187`) | Lane D |
| `reportkit/composition_audit.py` | `audit_source(tex: Path, brief: Path \| None, state) -> dict`; `ROLE_REGISTRIES: dict[str, RoleRegistry]` | delegates to `editorial_audit.audit_editorial_source` for feature-article, otherwise returns a passing empty audit | Lane E |
| `reportkit/review.py` | `write_review(pdf, state, visual_review) -> dict`; `read_review(source_root) -> dict \| None` | writes a minimal `build/review.json` | Lane E |
| `reportkit/status.py` | `collect_status(source_root) -> dict` | returns target payload plus `next_step` | Lane B |

Call sites that Wave 0 wires, all calling the stubs above:

- [ ] `_run_check` appends `target_gate(state)`, `tex_gates(...)` when
      `source_mode == "tex"`, and `audit_source(...)` when a brief exists.
- [ ] `publication_build._preflight` runs the same three gates **before**
      compilation, then `engine_gate`. It also records `declared_by` and
      `matches_intent` into `selection` (both `None` until the lanes fill them).
- [ ] `_run_inspect` compares `build-report.json` `selection` with
      `load_target(...).intent`. The stub always passes.
- [ ] `context_budget.py:76` and `context.py` read `target_line` and
      `authoring_templates.document_template` instead of inlining them.
- [ ] One central output helper in `cli.py` (`_emit(payload, state, command, as_json)`)
      puts `target` and `next_step` in every JSON payload and prints the
      TARGET line first and `next step:` last for human output. Every
      `_run_*` handler routes through it.
- [ ] Add subparsers for `target`, `status`, and `review`, with handlers
      that call the stub modules.

### 3.4 Wave 0 tests

- [ ] `tests/test_loop_contract.py`: every new command is in
      `COMMAND_CONTRACT` and `tools.json`; every new `RK_*` code resolves
      through `make_diagnostic`; every `PUBLICATION_TYPES` entry has
      `source_modes`, `aliases`, and `canonical_example`; the stub modules
      import and expose the frozen signatures (checked with `inspect.signature`).
- [ ] The existing suite passes unchanged. This proves the hooks are
      behaviour-neutral.

**Wave 0 exit gate:** full suite green, merged to `main`. Tag the merge
commit `loop-w0` so lanes branch from the same base.

---

## 4. Wave 1 — parallel lanes

Every lane works in its own worktree off `loop-w0`
(`Agent(isolation="worktree")` or `git worktree add ../rk-lane-X loop/lane-X`).
The file-ownership column is exclusive. **Tests** lists the files each lane
creates, so test files do not collide either.

| Lane | Spec scope | Owns (exclusive) | Reads (frozen) | Depends on |
| --- | --- | --- | --- | --- |
| **A** Target lock | P1 §4.2, F3/F8/F11 aliases | `target.py`, `initialization.py`, `config.py` (`resolve_document` only) | registry, diagnostics | — |
| **B** Loop output + status | P1 §4.1, §4.8 status | `loop.py`, `status.py`, `context_budget.py` (quickstart slice) | `TargetState` | A's contract only |
| **C** Direct-TeX build | P2 §4.3 | `tex_target.py`, `publication_build.py` (staging and engine selection), `latex.py` | `TargetState`, `source_modes` | — |
| **D** Scoped context | P3 §4.5 | `primitive_targets.py`, `authoring_templates.py`, `context.py`, `documentation.py` | registry | — |
| **E** Composition audits + review | P5 §4.7, §4.8 review | `composition_audit.py`, `editorial_audit.py` (becomes an alias shim), `review.py`, per-target brief examples under `latex_templates/examples/*/composition-brief.json` | `role_for` signature | D for real roles, via stub until then |
| **F** Docs router | P4 §4.6, F1/F2/F10 | `SKILL.md`, `AGENTS.md`, `references/*.md` (new split files, troubleshooting) | CLI contract from W0 | — (final wording rebased in W2) |
| **G** Agent evals | P6 §4.9 | `tests/agent_evals/**` | CLI contract | — |

Lanes A, C, D, F, and G have no dependencies after Wave 0. B and E code
against frozen interfaces, so they run in parallel too. They only *test*
against real behaviour after A and D merge (see §5).

### Lane A — Target lock (P1)

- [ ] `set_target`: validate the type/theme pair against
      `PUBLICATION_TYPES[type]["themes"]`, and validate the source mode
      against `source_modes`. A feature article with `markdown` raises
      `RK_SOURCE_MODE_UNSUPPORTED`, and the remediation points to
      `--source-mode tex` (Decision 1). Write the `document:` block with a
      round-trip-safe YAML update that preserves the user's other keys and
      comments where PyYAML allows; otherwise rewrite only the `document:`
      block. Write `.reportkit/intent.json` against
      `reportkit-intent.schema.json`, storing `request` verbatim (Decision 3).
- [ ] `resolve_alias`: map natural-language aliases to (type, theme). `target
      set` echoes the mapping (`magazine → structure=feature-article look=editorial`)
      and records `decided_by: agent-inferred` unless `--decided-by user-confirmed`.
- [ ] `init --publication-type/--theme/--source-mode`: when given, write the
      block and intent. Without them, write the placeholder YAML from §4.2
      with `validation.require_declared_target: true`. Update the
      `PUBLICATION_CONFIG` template in `initialization.py:19-31`.
- [ ] `resolve_document` records `declared_by`
      (`publication.yaml | tex-class-options | default`) without changing any
      resolved value.
- [ ] `target_gate`: undeclared + required → `RK_TARGET_UNDECLARED` (exit 3);
      undeclared + legacy → `RK_TARGET_IMPLICIT` warning.
- **Tests:** `tests/test_target_lock.py` covers AC1 and AC2, the alias table,
  YAML key preservation, the invalid pair, and the markdown feature rejection.

### Lane B — Loop output and status (P1)

- [ ] `target_line` prints the exact format from §4.1, with both axes named
      (`structure=… look=…`, F11).
- [ ] `next_step(command, state, outcome)` is a pure function over the §4.1
      table. A failed gate returns the remediation command (for example,
      undeclared → `reportkit target set`). A success returns the next row.
- [ ] Quickstart slice (`context_budget.py:76`): replace "The current target
      is …" with the declared or `TARGET NOT DECLARED` wording. Add the
      selection table with `source_modes` and the one-line structure-versus-look
      explanation. Stay ≤ 2,000 estimated tokens (AC3).
- [ ] `collect_status` reads only disk: target, intent, brief status (by
      calling `composition_audit.audit_source`), the last successful step
      from `build/` artefact mtimes and `build-report.json`, open diagnostics,
      `review.json` → `visual_review`, and `next_step`. If `visual_review`
      is `unavailable`, it emits `delivery_caveat`.
- **Tests:** `tests/test_loop_output.py` (every command's JSON has `target`
  and `next_step`; human output starts with `TARGET`) and
  `tests/test_status.py` (AC10: run each call in a fresh subprocess and
  compare the reconstructed state).

### Lane C — Direct-TeX build (P2)

- [ ] `read_class_options` parses `\documentclass[...]{reportkit}` for
      `publication-type=`/`theme=` (the same keys the Markdown template
      emits). It returns `None` when the options are missing.
- [ ] `tex_gates`: class options missing or disagreeing with
      `publication.yaml` → `RK_TARGET_MISMATCH`, raised before TeX runs (AC4).
- [ ] `publication_build.py`: when `source_mode == "tex"`, stage
      `document.main` instead of generating `publication.tex`. Set
      `TEXINPUTS` to `latex_templates/`, select the engine from
      `THEMES[theme]["required_engine"]`, and reuse the existing log gate,
      render, and manifest path (the `_finalize`/`_compile` functions around
      lines 838–1025). Keep the Markdown path byte-identical.
- [ ] `engine_gate`: a theme that requires LuaLaTeX with a forced `pdflatex`
      raises `RK_ENGINE_DOWNGRADE` (AC5). Reuse `config.theme_engine_conflict`.
- [ ] Fill `selection.declared_by` in `build-report.json` from
      `TargetState`.
- **Tests:** `tests/test_direct_tex_build.py`: the gate tests need no TeX;
  one TeX-marked build test uses `latex_templates/examples/editorial-feature/`
  copied to `tmp_path`.
- **Hand-off to F:** a short note in the PR description giving the exact
  `reportkit build` invocation that replaces the pdflatex steps in
  troubleshooting.

### Lane D — Scoped context (P3)

- [ ] `ROLE_TABLE`: one central, reviewed table keyed by primitive **family**
      (source `.sty` / chart module), with per-name overrides. Use a central
      table rather than editing every `% <reportkit-contract>` block across
      about 20 `.sty` files, because it is one reviewable diff and does not
      collide with other work. Feature-article: feature primitives `native`,
      `featuretable` and a curated `diagram` subset plus editorial charts
      `allowed`, callouts `discouraged` (Decision 2), algorithm primitives
      and `\maketitle` `absent`. `book/editorial`: callouts `allowed`.
- [ ] `generate_registry` attaches `targets` to each primitive record from
      `ROLE_TABLE`. `_filter_primitives` (`context.py:58`) drops
      `discouraged`/`absent` for the resolved target.
- [ ] `document_template` is built from each target's `canonical_example`:
      preamble, opening primitive (`featureopening`, `briefheader`,
      `researchfrontpage`, `titleslide`, `bookdetails`), and one example per
      native role. `\maketitle` stays only for `technical-report`.
- [ ] `documentation.py`: `render_reference(..., publication_type=T)` filters
      to `native`. The full inventory goes only to
      `references/primitive-contract.md`. Run `docs --write` **only for the
      generated blocks**; Lane F owns the hand-written prose above them.
- **Tests:** `tests/test_scoped_context.py` covers AC6 (≤ 8k tokens per target
  slice, no callout or algorithm primitive `native` for feature-article, a
  parametrised run over all six types) and AC7's byte budget (≤ 20 KB). It
  also checks that every primitive in the registry has a role for every type
  (no silent `allowed`).
- **Coordination with F:** D changes the generated tails of
  `feature-article-authoring.md`, `institutional-research-theme.md`, and
  `presentation-authoring.md` (between `REPORTKIT-CONTRACT:START/END`). F
  edits only the prose outside those markers. Both merge cleanly.

### Lane E — Composition audits and review (P5)

- [ ] Move the logic from `editorial_audit.py` into `composition_audit.py`
      with a `RoleRegistry(required_roles, role_patterns, manual_review, local_style_forbidden)`
      per target (§4.7 table). Leave `editorial_audit.py` as a re-export shim,
      so that `tests/test_editorial_audit.py` passes unchanged (AC9).
- [ ] Brief discovery: `intent.composition_brief` → `composition-brief.json` →
      `editorial-brief.json` (alias).
- [ ] Universal checks: `RK_PRIMITIVE_OFF_TARGET` uses `role_for` (a warning,
      or blocking when `"strict": true`); `RK_LOCAL_STYLE` generalises the
      existing forbidden-command scan. For Markdown projects, audit the
      generated `build/publication.tex`.
- [ ] Write a composition brief example per target next to each canonical
      example, and validate each example against its own brief. This is the
      spec's "role registries need fixture validation" risk.
- [ ] `review.py`: create a per-page checklist from the brief's
      `manual_review` items, plus `visual_review`. Write it to
      `build/review.json`.
- [ ] Fill the `_run_inspect` intent comparison → `RK_INTENT_MISMATCH` (AC11),
      and fill `selection.matches_intent`.
- **Tests:** `tests/test_composition_audit.py` (one parametrised case per
  target with a passing and failing fixture), `tests/test_review.py`, and
  `tests/test_inspect_intent.py`.
- Until Lane D merges, `role_for` returns `"allowed"`. Write the
  off-target tests against a monkeypatched `ROLE_TABLE`, so that they do not
  wait for D.

### Lane F — Docs router (P4)

- [ ] Rewrite `SKILL.md` as a router of 12 KB or less. The frontmatter
      names all six types (F1). Order: loop, selection table (structure × look,
      `source_mode`, engine, example, brief, next reference) within the first
      60 lines, positive stop rules stated once, writing for the decision,
      and a pointer table (AC8).
- [ ] Split the current SKILL.md lines 140–611 into
      `references/diagrams-and-algorithms.md`, `references/charts.md`, and
      `references/visual-grammar.md`. Each opens with a target-scope banner.
- [ ] **Watch `registry.skill_inventory`/`check_skill_drift`.** They parse
      SKILL.md for figure and callout inventories. Point the drift check at the
      moved files, or retire the SKILL.md inventory in favour of the
      generated contract. Keep `docs --check` green.
- [ ] Shrink `AGENTS.md` to about 10 lines. In `troubleshooting.md`, replace
      the raw `pdflatex` steps with `reportkit build`, and move raw engine
      commands into an "Engine developers" section.
- [ ] Trim the hand-written prose of `feature-article-authoring.md` and
      `institutional-research-theme.md`, without touching the generated
      block (see Lane D).
- **Tests:** `tests/test_skill_router.py` checks the size budgets, that the
  description names every key in `PUBLICATION_TYPES`, that the selection table
  starts before line 60, that `SKILL.md` contains no "Do not copy
  `REPORT_TEMPLATE.tex`"-style prohibitions, and that every command mentioned
  exists in `COMMAND_CONTRACT`.

### Lane G — Agent-behaviour evals (P6)

- [ ] Add a `tests/agent_evals/` harness: a host-neutral driver interface
      (`AgentDriver.run(prompt, workdir) -> transcript`) and a scripted
      "oracle" driver that replays the §4.1 loop, so the harness is
      deterministic in CI. Real-model drivers are opt-in behind
      `REPORTKIT_AGENT_EVAL=1` and a pytest marker, excluded by default.
- [ ] Add the four §4.9 scenarios. Each asserts on `build-report.json`
      `selection` and the audit. The context-reset scenario starts a new
      driver with only "continue the publication in <dir>".
- **Tests:** the harness self-test runs in the default suite; the scenarios
  are marked `agent_eval`.

---

## 5. Merge order and integration checkpoints

```
W0 ──► A ──► B ─┐
   ├─► C ───────┤
   ├─► D ──► E ─┼──► W2
   ├─► F ───────┤
   └─► G ───────┘
```

1. **A merges first.** It is the release-critical P1 fix and can ship as a
   patch release by itself. B and E then rebase to pick up the real
   `load_target`.
2. **C and D** merge in either order. Their files do not overlap.
3. **B merges after A.** Its status tests need a real intent. **E merges
   after D.** Its off-target tests switch from the monkeypatched table to the
   real one.
4. **F merges last among lanes.** It rebases onto the actual command
   outputs, and pastes a real `reportkit status` transcript into SKILL.md.
5. **G can merge any time.** Its scenarios go green once A–E are in.

After each merge, the coordinator runs the full suite on `main`. A red
`main` blocks further merges until fixed.

## 6. Coordination protocol

- **One coordinator** (the session that ran Wave 0) owns `main`, the merge
  queue, and the hotspot files. Lane agents do not push to `main`.
- **Contract change requests.** A lane that needs a new field, code, or
  argument in a Wave 0 file stops and sends the coordinator a one-paragraph
  request. The coordinator lands it on `main` as a small commit, and every
  in-flight lane rebases. Lanes never edit hotspot files locally "just for
  now."
- **Status.** Each lane keeps the checklist in its PR description current.
  Blocking questions go to the coordinator, not to other lanes.
- **Sub-agent prompts.** Give each lane agent this plan's §2, its own lane
  section, the frozen signatures table (§3.3), and the relevant spec sections
  only. Do not give it the whole spec. This mirrors the spec's own premise
  (§1): scoped context produces on-target work.

## 7. Wave 2 — integration (single agent)

- [ ] Bump `CONTRACT_VERSION` 1.2.0 → 1.3.0 (minor, additive), and
      `REPORTKIT_VERSION` per CHANGELOG convention.
- [ ] Run `reportkit docs --write`, regenerate `adapters/openai/tools.json`,
      and confirm `docs --check` and `tests/test_openai_adapter.py` are clean
      (AC12).
- [ ] Run the acceptance matrix end-to-end on a fresh `reportkit init`
      project per publication type, with TeX. Tick AC1–AC12 in the PR body
      with the command and output excerpt for each.
- [ ] Run a legacy-project check: build
      `publication_pipeline/example_publication/` unchanged and diff
      `build-report.json` with the pre-change build. The only expected diff is
      the new optional fields plus one `RK_TARGET_IMPLICIT` (AC2).
- [ ] Run the `agent_eval` scenarios with the oracle driver. Where a model
      driver is available, record one real run in the PR, with no pass/fail
      claim beyond what was observed.
- [ ] Add a CHANGELOG entry that lists the new diagnostics and commands, and
      the opt-in blocking behaviour.

## 8. Acceptance criteria → owner

| AC | Owner lane | Test |
| --- | --- | --- |
| 1 `init` without flags → `RK_TARGET_UNDECLARED` | A | `test_target_lock.py` |
| 2 legacy build unchanged + `RK_TARGET_IMPLICIT` | A (+W2 diff) | `test_target_lock.py` |
| 3 quickstart wording, ≤ 2k tokens, source modes | B | `test_loop_output.py` |
| 4 direct-TeX build, `RK_TARGET_MISMATCH` | C | `test_direct_tex_build.py` |
| 5 `RK_ENGINE_DOWNGRADE`, no theme-change advice | C (+W0 text) | `test_direct_tex_build.py` |
| 6 feature slice ≤ 8k, no native callouts or algorithms | D | `test_scoped_context.py` |
| 7 authoring refs ≤ 20 KB, `docs --check` | D + F | `test_scoped_context.py`, `test_skill_router.py` |
| 8 SKILL.md ≤ 12 KB, six types, table by line 60 | F | `test_skill_router.py` |
| 9 audit for every type, legacy test passes | E | `test_composition_audit.py`, `test_editorial_audit.py` |
| 10 `status` from disk alone | B | `test_status.py` |
| 11 `inspect` fails on intent mismatch | E | `test_inspect_intent.py` |
| 12 `tools.json` exposes new tools | W0 + W2 | `test_openai_adapter.py`, `test_loop_contract.py` |

## 9. Risks

| Risk | Mitigation |
| --- | --- |
| Wave 0 stubs are wrong and lanes discover it late | Signatures are checked by `test_loop_contract.py`. Lanes raise change requests on day one, not at merge. Keep Wave 0 small enough to review in one sitting. |
| `ROLE_TABLE` is incomplete, so primitives silently default to `allowed` | Lane D's test requires an explicit role for every (primitive, type) pair. |
| Role registries reject the repository's own canonical examples | Lane E validates each canonical example against its own brief in CI. |
| SKILL.md split breaks `check_skill_drift` | Lane F owns the fix and runs `docs --check` in its done gate. |
| Direct-TeX path diverges from the Markdown path's gates | Lane C calls the shared finalize and log-gate functions. `test_direct_tex_build.py` asserts that both paths produce the same `build-report.json` keys. |
| YAML rewrite drops user comments | Lane A rewrites only the `document:` block, with a round-trip test. |
