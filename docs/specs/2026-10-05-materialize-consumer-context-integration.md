# Spec — integrate `reportkit materialize` and the single-PDF build contract

- **Date:** 2026-10-05
- **Branch:** `feat/materialize-consumer-context` (uncommitted work on top of `5a0d8dc`)
- **Area:** `python_scripts/reportkit/{materialize,cli,loop,registry,target}.py`,
  `publication_pipeline/scripts/publication_build.py`, `SKILL.md`, `references/`,
  `adapters/openai/tools.json`, `CHANGELOG.md`
- **Status:** proposed

## Summary

The branch adds two features. Both aim to make consumer projects (content repos)
robust when an agent runs the ReportKit skill:

1. **`reportkit materialize`** copies the locked target's reference docs, its
   primitives context slice, and a preflight checklist into
   `<project>/.reportkit/`. The agent then reads local files instead of
   exploring the engine clone.
2. **Single-PDF combined build.** A combined build removes `build/combined/`
   before staging. It renames the compiled `publication.pdf` to `<slug>.pdf`
   instead of copying it, so exactly one PDF remains.

A review on 2026-10-05 found the implementation sound. The full suite passes
(940 passed, 4 skipped, 6 xfailed), `reportkit docs --check` passes, and a
consumer project run end to end worked: `target set` → `init` → `materialize` →
`check` → `build` ×2 → `package`. Four integration gaps remain before merge:

| # | Gap | Effect |
|---|-----|--------|
| G1 | `init` can write a malformed `publication.yaml` (existing bug) | Every later command, including `materialize`, fails with `unknown key "default"validation` |
| G2 | No `next_step` routes to `materialize` | Agents that follow `next_step`, as `AGENTS.md` instructs, never run it |
| G3 | `materialize` silently falls back to `technical-report/default` when no target is declared | Copies the wrong guidance and contradicts the SKILL stop rule |
| G4 | No tests for `materialize`, its loop routing, or stale-artefact removal | Regressions go unnoticed |

There are also two maintenance gaps: the checklist text is duplicated (G5), and
the user-visible changes are not in `CHANGELOG.md` (G6).

## Current behaviour (verified)

- `reportkit materialize --source-root <p> --json` writes
  `.reportkit/{CHECKLIST.md,context.json,references/*.md}`. It returns
  `{"passed": true, "materialized": {...}}` and gives
  `next_step = reportkit check --json`.
- `materialize` refuses a project inside the engine clone
  (`RK_MATERIALIZE_LOCATION`, exit 2). If the context fails to load it returns
  `RK_MATERIALIZE_CONTEXT` (exit 2). If a write fails it returns
  `RK_MATERIALIZE_WRITE` (exit 70).
- `reference_names()` always copies 8 core references, plus one per structure
  (`TYPE_REFERENCE`) and one per look (`THEME_REFERENCE`). All of these files exist.
- The build history lives in `<output_root>/history/`, a sibling of `combined/`,
  so `rmtree(combined)` does not touch it.
- No code reads `publication.pdf` after a build. `cli.py:715` already excludes it
  when it looks for the delivered PDF, and keeping that exclusion is harmless for
  older build directories.

## Work items

### W1 — Fix `init` YAML corruption (G1, prerequisite)

**Reproduce** (with no prior `target set`):

```sh
reportkit init /tmp/p --publication-type technical-report --theme default --source-mode markdown
tail -5 /tmp/p/publication.yaml
#   publication_type:   "technical-report" # REQUIRED: ...
#   theme:
# "default"validation:
```

**Root cause.** In `python_scripts/reportkit/target.py` (≈ line 416), the
document-block child pattern is:

```python
rf"^({re.escape(indent_text)})([A-Za-z_][A-Za-z0-9_-]*)(\s*:\s*)(.*?)(\r?\n)?$"
```

The trailing `\s*` in the delimiter group can match a newline. For an empty
value such as `  theme:\n`, it consumes the `\n`, so the `newline` group is
empty. The rewritten line then loses its line break and merges into the next
key. The same greedy `\s*` keeps the scaffold's alignment spaces in
`publication_type:   "…"`.

**Fix.** Restrict the delimiter to horizontal whitespace:

```python
rf"^({re.escape(indent_text)})([A-Za-z_][A-Za-z0-9_-]*)([ \t]*:[ \t]*)(.*?)(\r?\n)?$"
```

Normalise the delimiter written back to `": "`, so the scaffold's padding does
not survive.

**Tests** (`tests/test_initialization.py` or `tests/test_target*.py`):
- `init` with target flags on an empty directory produces a `publication.yaml`
  that `load_target()` reloads. It declares the requested
  type, theme, and source mode, and keeps `validation.require_declared_target: true`.
- `set_target` on a document block with an empty-valued key followed by another
  top-level key keeps both keys on separate lines. Cover `\n` and `\r\n` line endings.

### W2 — Route the loop through `materialize` (G2)

`materialize` already writes the primitives slice to `.reportkit/context.json`,
so it subsumes the separate *Author* call. Make it the documented step after
scaffolding:

| Command | Current `next_step` | New `next_step` |
|---|---|---|
| `init` (declared + intent) | `reportkit context --slice primitives --json` | `reportkit materialize --json` |
| `context` (declared + intent) | `reportkit context --slice primitives --json` | unchanged for `--slice quickstart`; `reportkit materialize --json` after `--slice primitives` |
| `materialize` | `reportkit check --json` | unchanged |
| `status` before a build | (existing logic) | Suggest `materialize` when `.reportkit/context.json` is absent |

For the `context` row, `next_step` needs the slice, either as part of the
command string or as an outcome field. Pass it as `outcome["slice"]` from
`_run_context` rather than parsing argv.

**SKILL.md:** merge the *Author* and *Materialize* rows into one *Materialize*
row. Its result text names `context.json` and `markdown_forms`. Keep
`reportkit context --slice primitives` as the way to re-read the slice. Update
the SKILL.md assertions in `tests/test_skill_discoverability_docs.py` and
`tests/test_openai_adapter.py` to match.

**Tests** (`tests/test_loop_contract.py`): add a `next_step` case for each new
row above, and keep the existing `materialize → check` assertion.

### W3 — Refuse an undeclared target (G3)

`_run_materialize` currently does this:

```python
publication_type = state.publication_type if state else "technical-report"
```

It also accepts a state whose `declared_by == "default"`. Instead, when the
target is not declared, emit the same blocking diagnostic and exit code as other
target-gated commands. Reuse the existing helper or code that `check`/`build`
use for `require_declared_target`. The diagnostic's `remediation` points to
`reportkit target set`, and `next_step` follows the existing undeclared branch.
Remove the fallback defaults.

### W4 — Test coverage (G4)

New file: `tests/test_materialize.py`.

1. **Happy path.** After `target set` and `init` in `tmp_path`, `materialize --json`
   exits 0. `.reportkit/CHECKLIST.md`, `context.json`, and every name from
   `reference_names(type, theme)` exist. `context.json` equals
   `build_context_slice(..., "primitives")` for the target.
2. **Per-target references.** Parametrise over every supported structure × look
   pair from the publication registry. Assert that `reference_names()`
   returns only files that exist under `references/`. This catches renamed docs,
   because `materialize` currently skips missing files silently.
3. **Location refusal.** A `--source-root` inside `REPO_ROOT` returns exit 2 with
   `RK_MATERIALIZE_LOCATION` and writes nothing.
4. **Undeclared target.** This is the W3 refusal. It writes nothing.
5. **Idempotent re-run.** A second run succeeds and overwrites the files.
   `intent.json` is untouched.
6. **Contract parity.** `materialize` is present in `COMMAND_CONTRACT`, the
   argparse subcommands, and `adapters/openai/tools.json`.
   `tests/test_openai_adapter.py` may already enforce this; extend it if not.

In `publication_pipeline/tests/test_build_target_selection.py`, add a
stale-artefact case. Before a second combined build, plant
`build/combined/stale.pdf` and `build/combined/old.aux`. After the build, only
`<slug>.pdf` remains among the PDFs and neither planted file exists.

### W5 — Single source for the checklist (G5)

`CHECKLIST_TEXT` in `materialize.py` and the "Consumer preflight checklist"
section of `SKILL.md` repeat the same rules, and they will drift apart.

- Move the full checklist to `references/consumer-preflight.md`.
- `materialize` copies it to `.reportkit/CHECKLIST.md` by reading that file.
  Delete the `CHECKLIST_TEXT` constant.
- `SKILL.md` keeps a two-line pointer: run `materialize`, then follow
  `.reportkit/CHECKLIST.md`. Add a row for it to the References table.
- Add a test that `.reportkit/CHECKLIST.md` matches the source byte for byte.

### W6 — Documentation and changelog (G6)

- In `CHANGELOG.md`, under `[Unreleased]`:
  - **Added:** `reportkit materialize`.
  - **Changed:** a combined build now removes `build/combined/` before each run and
    leaves exactly one `<slug>.pdf`. The intermediate `publication.pdf` is no
    longer kept.
  - **Fixed:** `init` no longer corrupts `publication.yaml`.
- `references/repository-boundary.md`: the "Output contract" section is already
  added. Add a line saying that `.reportkit/references/`, `context.json`, and
  `CHECKLIST.md` are regenerated copies. Consumers can commit or ignore them,
  but `intent.json` must be committed.
- `references/migrating-content-branches.md`: add a step to run
  `reportkit materialize` after migrating an existing content repo.
- Regenerate the contract docs and the OpenAI tool schema from
  `COMMAND_CONTRACT`. Confirm with `reportkit docs --check`.

## Compatibility and risk

- **Removing `build/combined/` deletes anything a consumer stored there by
  hand.** This directory has always been engine-owned build output. The
  changelog entry and the Output contract section make the behaviour explicit.
  `history/` and `output/` are not affected.
- **External scripts that read `build/combined/publication.pdf` will break.**
  No in-repo consumer reads it. Call this out in the changelog **Changed** entry.
- **Changing `next_step` alters the routing agents follow.** Agents following
  the old route still work, because `context --slice primitives` remains valid.
- **The `target.py` regex change affects every `target set` write.** The W1
  tests cover empty values, inline comments, padded delimiters, and CRLF line endings.

## Acceptance criteria

- [ ] `init` with target flags on an empty directory produces a reloadable
      `publication.yaml`. `materialize`, `check`, and `build` succeed on it without
      a prior `target set`.
- [ ] Following only `next_step` from `init` reaches `materialize` and then `check`.
- [ ] `materialize` refuses an undeclared target, an in-clone project, and a
      context failure with registered codes and exit codes, and writes nothing.
- [ ] For every supported structure × look pair, `materialize` copies only references
      that exist. The checklist matches `references/consumer-preflight.md`.
- [ ] Two consecutive combined builds leave exactly one PDF in `build/combined/`
      and no planted stale files. `package` copies that PDF to `output/`.
- [ ] The full suite passes. `reportkit docs --check` passes. The
      `tools.json` entry for `reportkit_materialize` matches `COMMAND_CONTRACT`.
- [ ] A consumer-project PDF builds for one Markdown target and one direct-TeX
      target. Inspect the `build-report.json` selection and review the
      rendered pages, or report that visual review was unavailable.

## Suggested order

W1 → W3 → W4 (tests for the existing behaviour plus W1/W3) → W2 → W5 → W6.
W1 comes first because it blocks the end-to-end checks in W4 and the
acceptance criteria.

## Out of scope

- Detecting stale materialized copies after an engine upgrade, for example
  recording the engine commit in `.reportkit/` and having `status` warn on a
  mismatch. Do this as a follow-up once W5 sets the single source.
- Materialize guidance specific to direct-TeX projects. The checklist covers
  Markdown sources. Direct-TeX projects still get the references and
  `context.json`.
- The existing `RK_PRIMITIVE_OFF_TARGET` warnings from the generated entrypoint.
  See `2026-10-05-markdown-table-minipage-composition-false-positive.md`.
