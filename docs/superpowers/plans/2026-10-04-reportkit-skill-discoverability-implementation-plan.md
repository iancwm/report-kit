# ReportKit Skill Discoverability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make an agent that follows `SKILL.md` and the CLI `next_step` chain discover image slots, Markdown markers, project files, and the composition audit. Also make it report unfinished images at delivery.

**Architecture:**
- **Context slice.** One new module, `markdown_forms.py`, publishes a machine-readable inventory of Markdown-only syntax in the `primitives` context slice. Tests check its examples against the live parsers.
- **`check` gates.** `check` gains two loop diagnostics: a missing composition brief, and image slots used in a direct-TeX project.
- **`status`.** `status` reads unresolved image slots from the latest `build-report.json`.
- **Docs.** The docs (a new reference, three per-format guides, and SKILL.md) are rewritten to route agents to these surfaces.

**Tech Stack:** Python 3 standard library, pytest, jsonschema (optional in tests via `importorskip`), and Markdown docs.

**Spec:** `docs/superpowers/specs/2026-10-04-reportkit-skill-discoverability-spec.md`

## Global Constraints

- Work on a branch, not `main`: `git checkout -b fix/skill-discoverability`. Subagent workers may use a worktree.
- Run tests from the repo root with `python3 -m pytest <paths> -q`. `tests/conftest.py` already puts `python_scripts/` on `sys.path`, so `from reportkit... import ...` works in tests.
- Lint with `ruff check python_scripts tests`. It must pass, because the repo's last commit cleared all ruff findings.
- Do not add runtime dependencies. ReportKit parses its YAML subset itself (`reportkit.config._yaml_tokens`, `reportkit.authoring._parse_subset`).
- The `quickstart` slice must stay at or below 2,000 estimated tokens (`ALWAYS_LOADED_TOKEN_CEILING`). This plan does not change the quickstart.
- The `primitives` slice content is a free-form object in `schemas/reportkit-context-slice.schema.json` (`"content": {"type": "object"}`). Adding a key needs no schema change.
- New diagnostic codes go in `DIAGNOSTIC_CODES` in `python_scripts/reportkit/diagnostics.py`, with `type`, `severity`, `exit_code`, and `remediation`. Create them with `make_diagnostic("target_contract", message, code=...)`.
- Match the surrounding style:
  - `from __future__ import annotations` at the top of each module;
  - short docstrings that state intent;
  - comments only where the reason is non-obvious;
  - British spelling in docs prose ("colour", "licence" as a noun). Field names such as `license` stay as they are.
- Do not edit inside `<!-- REPORTKIT-CONTRACT:START -->` … `<!-- REPORTKIT-CONTRACT:END -->` blocks in `references/*.md`. `reportkit docs` generates them.
- Never invent rights, sources, or citations in example content. Use `example.org` URLs and the fictional subjects already used in the repo (pump housing, field survey).
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```

## Execution Order

- **Wave 1:** Tasks 1, 2, and 3 touch disjoint files. They can run in any order.
- **Wave 2:** Task 4 uses names produced by Tasks 1 and 2. Task 5 uses names produced by Tasks 3 and 4.
- **Task 6** is the final verification and changelog.

## Review Focus

1. **Commented-out image marker in TeX.** A direct-TeX `report.tex` containing `% [[REPORTKIT-IMAGE:img:x]]` inside a comment must not trigger `RK_IMAGE_SLOTS_TEX_MODE`, because comments do not render. Pinned in Task 2.
2. **Markdown projects keep full image validation.** A Markdown project with an orphan `image-slots.yaml` entry must still get `RK_VALIDATION_ORPHAN_IMAGE_DECLARATION`. The suppression is TeX-only. Pinned in Task 2.
3. **No extra noise for undeclared projects.** A project with no declared target already fails (`RK_CONFIG_BUILD_TARGET` or `RK_TARGET_UNDECLARED`). It must not also get `RK_COMPOSITION_BRIEF_MISSING`. Pinned in Task 2.
4. **Malformed build reports.** A `build-report.json` whose `unresolved_image_slots` is not a list, or whose items lack `slug`, must not crash `status`. Bad items are skipped. Pinned in Task 3.
5. **Status payloads still validate.** Payloads with the new fields, including `image_caveat: null`, must validate against `schemas/reportkit-status.schema.json`. Pinned in Task 3.

---

### Task 1: Markdown forms in the `primitives` context slice

**Files:**
- Create: `python_scripts/reportkit/markdown_forms.py`
- Modify: `python_scripts/reportkit/context_budget.py`:
  - lines 20–27 (`_SLICE_DESCRIPTIONS["primitives"]`)
  - lines 144–166 (`slice_contents`, the `"primitives"` entry)
- Test: `tests/test_markdown_forms.py`

**Interfaces:**
- Consumes existing names:
  - `reportkit.image_slots`: `ASPECT_RATIOS: dict[str, tuple[int, int]]`, `IMAGE_FIELDS: tuple[str, ...]`, `IMAGE_SLOTS_FILENAME = "image-slots.yaml"`, `SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...]`, `IMAGE_SENTINEL_RE`
  - `reportkit.authoring`: `LINK_TYPES: set[str]`, `validate_authoring(root: Path) -> AuthoringResult` (has `.ok`, `.errors`, `.sources`, `.links`)
  - `reportkit.publication_validation`: `SENTINEL_RE` (visual marker)
  - `reportkit.markdown_directives`: `parse_markdown(text) -> ParsedMarkdown` (has `.diagnostics: tuple`, `.directives: tuple[DirectiveNode]`; `DirectiveNode.primitive: str`)
- Produces:
  - `reportkit.markdown_forms.MARKDOWN_FORMS_DOCS: str = "references/markdown-authoring.md"`. Task 4 creates this file.
  - `reportkit.markdown_forms.markdown_forms() -> dict[str, Any]`. Its keys are `source_modes` (`["markdown"]`), `docs`, `note`, and `forms`. `forms` is a list of dicts, each with `name`, `syntax` or `file`, `example`, and `rules`, in the order `directive`, `visual`, `image_slot`, `links`, `sources`.
  - The `primitives` slice content gains the key `"markdown_forms"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_markdown_forms.py`:

```python
from __future__ import annotations

from pathlib import Path

from reportkit.authoring import LINK_TYPES, validate_authoring
from reportkit.context import build_context
from reportkit.context_budget import build_context_slice
from reportkit.image_slots import ASPECT_RATIOS, IMAGE_FIELDS, IMAGE_SENTINEL_RE, IMAGE_SLOTS_FILENAME
from reportkit.markdown_directives import parse_markdown
from reportkit.markdown_forms import MARKDOWN_FORMS_DOCS, markdown_forms
from reportkit.publication_validation import SENTINEL_RE


REPO = Path(__file__).resolve().parents[1]


def _form(name: str) -> dict:
    return next(form for form in markdown_forms()["forms"] if form["name"] == name)


def test_primitives_slice_lists_markdown_forms() -> None:
    content = build_context_slice(build_context(REPO), "primitives")["content"]
    forms = content["markdown_forms"]
    assert forms["source_modes"] == ["markdown"]
    assert forms["docs"] == MARKDOWN_FORMS_DOCS == "references/markdown-authoring.md"
    assert [form["name"] for form in forms["forms"]] == ["directive", "visual", "image_slot", "links", "sources"]
    assert all(form["rules"] for form in forms["forms"])


def test_directive_example_parses_without_diagnostics() -> None:
    parsed = parse_markdown(_form("directive")["example"] + "\n")
    assert parsed.diagnostics == ()
    assert [node.primitive for node in parsed.directives] == ["redflag"]


def test_visual_and_image_examples_match_the_validator_markers() -> None:
    assert SENTINEL_RE.fullmatch(_form("visual")["example"])
    assert IMAGE_SENTINEL_RE.fullmatch(_form("image_slot")["example"])


def test_image_slot_form_mirrors_the_manifest_contract() -> None:
    form = _form("image_slot")
    assert form["requires"][0] == IMAGE_SLOTS_FILENAME
    assert form["fields"] == list(IMAGE_FIELDS)
    assert form["aspect_ratios"] == list(ASPECT_RATIOS)


def test_project_file_examples_validate(tmp_path: Path) -> None:
    assert _form("links")["types"] == sorted(LINK_TYPES)
    (tmp_path / "links.yaml").write_text(_form("links")["example"], encoding="utf-8")
    (tmp_path / "sources.yaml").write_text(_form("sources")["example"], encoding="utf-8")
    result = validate_authoring(tmp_path)
    assert result.ok, result.errors
    assert result.links == ["field-survey-data"]
    assert result.sources == ["field-survey"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_markdown_forms.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'reportkit.markdown_forms'`.

- [ ] **Step 3: Create the module**

Create `python_scripts/reportkit/markdown_forms.py`:

```python
"""Machine-readable inventory of Markdown-mode authoring forms.

The primitives slice lists TeX signatures generated from the LaTeX registry.
Markdown manuscripts also accept line markers, fenced directives, and project
files that the publication pipeline consumes; this inventory lets
``reportkit context --slice primitives`` teach them. Tests check every example
against the live parsers so the inventory cannot drift from the code.
"""
from __future__ import annotations

from typing import Any

from .authoring import LINK_TYPES
from .image_slots import ASPECT_RATIOS, IMAGE_FIELDS, IMAGE_SLOTS_FILENAME, SUPPORTED_IMAGE_EXTENSIONS


MARKDOWN_FORMS_DOCS = "references/markdown-authoring.md"


def markdown_forms() -> dict[str, Any]:
    """Return the Markdown-only syntax an agent may use beside the primitives."""
    return {
        "source_modes": ["markdown"],
        "docs": MARKDOWN_FORMS_DOCS,
        "note": (
            "Markdown sources only. Direct-TeX projects use the primitives above; "
            "visual markers and image slots are unavailable there."
        ),
        "forms": [
            {
                "name": "directive",
                "syntax": "```reportkit <primitive>\n<argument>: <value>\ncontent: <text>\n```",
                "example": (
                    "```reportkit redflag\n"
                    "title: Supplier exposure\n"
                    "content: The estimate depends on one supplier renewing its contract.\n"
                    "```"
                ),
                "rules": [
                    "<primitive> must be listed in this slice for the selected target.",
                    "Values are plain text; raw TeX is rejected.",
                    "fragment: <name>.tex includes a trusted file from fragments/ unchanged.",
                ],
            },
            {
                "name": "visual",
                "syntax": "[[REPORTKIT-VISUAL:fig:<slug>]]",
                "example": "[[REPORTKIT-VISUAL:fig:process-flow]]",
                "requires": ["fragments/fig-<slug>.tex"],
                "rules": [
                    "Put the marker alone on its own line and use each slug once.",
                    "fragments/fig-<slug>.tex holds the trusted TeX for one figure, such as a "
                    "diagram environment with caption and source options.",
                    "This is the only way to place a diagram or chart in a Markdown manuscript.",
                ],
            },
            {
                "name": "image_slot",
                "syntax": "[[REPORTKIT-IMAGE:img:<slug>]]",
                "example": "[[REPORTKIT-IMAGE:img:pump-housing]]",
                "requires": [IMAGE_SLOTS_FILENAME, "assets/images/<slug>.<extension>"],
                "fields": list(IMAGE_FIELDS),
                "aspect_ratios": list(ASPECT_RATIOS),
                "extensions": list(SUPPORTED_IMAGE_EXTENSIONS),
                "rules": [
                    "Use for a photograph or observed state that prose or a diagram cannot show.",
                    "Declare the slot before the file exists; a draft build prints an IMAGE NEEDED placeholder.",
                    "Record truthful source, creator, license, attribution, and restrictions; "
                    "write 'pending' until confirmed and never infer a licence.",
                    "The credit line comes from the manifest; do not add \\source{...}.",
                    "Final and release builds reject unresolved slots; report them at delivery.",
                ],
            },
            {
                "name": "links",
                "file": "links.yaml",
                "example": (
                    "links:\n"
                    "  field-survey-data:\n"
                    "    url: https://example.org/survey\n"
                    "    label: Field inspection survey\n"
                    "    type: dataset\n"
                ),
                "types": sorted(LINK_TYPES),
                "rules": [
                    "Each link needs url, label, and one of the listed types.",
                    "TeX sources and fragments reference a link with \\RKLink{<key>}.",
                ],
            },
            {
                "name": "sources",
                "file": "sources.yaml",
                "example": (
                    "sources:\n"
                    "  field-survey:\n"
                    "    type: dataset\n"
                    "    title: Field inspection survey\n"
                    "    file: data/survey.csv\n"
                    "    links:\n"
                    "      - field-survey-data\n"
                    "chapters:\n"
                    "  - id: findings\n"
                    "    title: Findings\n"
                    "    purpose: Report what the inspection found\n"
                    "    sources:\n"
                    "      - field-survey\n"
                ),
                "rules": [
                    "Each source needs type, title, and file; links must name keys in links.yaml.",
                    "Each chapter needs id, title, and purpose; its sources must name declared sources.",
                ],
            },
        ],
    }
```

- [ ] **Step 4: Wire the forms into the slice**

In `python_scripts/reportkit/context_budget.py`:

1. Add the import after `from typing import Any, Mapping`:

   ```python

   from .markdown_forms import markdown_forms
   ```

2. Replace the `"primitives"` description in `_SLICE_DESCRIPTIONS`:

   ```python
       "primitives": "Primitive signatures and examples filtered for the requested target, plus Markdown-mode markers and project files.",
   ```

3. In `slice_contents`, replace the `"primitives"` entry:

   ```python
           "primitives": {
               "filters": context["filters"],
               "primitives": _compact_primitives(capabilities["primitives"]),
               "markdown_forms": markdown_forms(),
           },
   ```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_markdown_forms.py tests/test_context_budget.py tests/test_language_script_truthfulness.py -q`
Expected: all pass.

- [ ] **Step 6: Lint and commit**

```bash
ruff check python_scripts/reportkit/markdown_forms.py python_scripts/reportkit/context_budget.py tests/test_markdown_forms.py
git add python_scripts/reportkit/markdown_forms.py python_scripts/reportkit/context_budget.py tests/test_markdown_forms.py
git commit -m "feat(context): list Markdown forms in the primitives slice

Image slots, visual markers, directive fences, links.yaml, and sources.yaml
are Markdown-only syntax that never appeared in the primitives slice, so the
SKILL stop rule excluded them. Examples are checked against the live parsers.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `check` gates for a missing brief and TeX-mode image slots

**Files:**
- Modify: `python_scripts/reportkit/diagnostics.py`. Add two entries to `DIAGNOSTIC_CODES` (the dict starts at line 59).
- Modify: `python_scripts/reportkit/tex_target.py`. Add imports and a new `tex_image_slot_gate` function after `tex_gates` (line 133).
- Modify: `python_scripts/reportkit/cli.py`:
  - imports at line 58;
  - `_target_diagnostics` at lines 431–447;
  - `_run_check`, just before the line `loop_diagnostics, composition = _target_diagnostics(args, root, state, engine_override)` (about line 507).
- Test: `tests/test_check_discoverability_gates.py`

**Interfaces:**
- Consumes:
  - `reportkit.composition_audit.find_brief(root, state) -> Path | None`
  - `reportkit.image_slots.IMAGE_SLOTS_FILENAME`, `IMAGE_SENTINEL_MARKER = "REPORTKIT-IMAGE"`
  - `reportkit.tex_target._without_tex_comments(source: str) -> str`
  - `TargetState` fields `source_mode`, `main`, and `declared_by`
- Produces:
  - Diagnostic code `RK_COMPOSITION_BRIEF_MISSING`: severity `warning`, `exit_code` 0.
  - Diagnostic code `RK_IMAGE_SLOTS_TEX_MODE`: severity `error`, `exit_code` 3.
  - `reportkit.tex_target.tex_image_slot_gate(root: Path, state: TargetState) -> list[dict[str, Any]]`
  - `check` no longer emits `RK_VALIDATION_*IMAGE*` codes when `source_mode == "tex"`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_check_discoverability_gates.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "publication_pipeline" / "example_publication" / "image-slots.yaml"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(REPO / "reportkit"), *arguments], capture_output=True, text=True)


def _project(tmp_path: Path, source_mode: str) -> Path:
    root = tmp_path / "publication"
    target = ("--publication-type", "technical-report", "--theme", "default", "--source-mode", source_mode)
    for command in (
        ("target", "set", "--source-root", str(root), *target, "--request", "test publication", "--json"),
        ("init", str(root), *target, "--json"),
    ):
        result = _run(*command)
        assert result.returncode == 0, result.stdout + result.stderr
    return root


def _check(root: Path) -> tuple[int, dict]:
    result = _run("check", "--source-root", str(root), "--json")
    return result.returncode, json.loads(result.stdout)


def _codes(payload: dict) -> list[str]:
    return [item["code"] for item in payload["diagnostics"]]


def _image_validation_codes(payload: dict) -> list[str]:
    return [code for code in _codes(payload) if code.startswith("RK_VALIDATION_") and "IMAGE" in code]


def test_check_warns_when_the_composition_brief_is_missing(tmp_path: Path) -> None:
    root = _project(tmp_path, "markdown")
    (root / "composition-brief.json").unlink()
    exit_code, payload = _check(root)
    assert exit_code == 0
    assert payload["passed"] is True
    warning = next(item for item in payload["diagnostics"] if item["code"] == "RK_COMPOSITION_BRIEF_MISSING")
    assert warning["severity"] == "warning"
    assert "reportkit init" in warning["remediation"]


def test_check_is_quiet_about_the_brief_when_one_exists(tmp_path: Path) -> None:
    root = _project(tmp_path, "markdown")
    _, payload = _check(root)
    assert "RK_COMPOSITION_BRIEF_MISSING" not in _codes(payload)


def test_undeclared_project_gets_no_brief_warning(tmp_path: Path) -> None:
    root = tmp_path / "publication"
    assert _run("init", str(root), "--json").returncode == 0
    # Verified 2026-10-04: an init without target flags fails check with
    # RK_CONFIG_BUILD_TARGET (empty publication_type), not RK_TARGET_UNDECLARED.
    _, payload = _check(root)
    assert payload["passed"] is False
    assert "RK_COMPOSITION_BRIEF_MISSING" not in _codes(payload)


def test_tex_project_with_an_image_manifest_gets_one_actionable_error(tmp_path: Path) -> None:
    root = _project(tmp_path, "tex")
    (root / "image-slots.yaml").write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    exit_code, payload = _check(root)
    assert exit_code == 3
    assert payload["passed"] is False
    error = next(item for item in payload["diagnostics"] if item["code"] == "RK_IMAGE_SLOTS_TEX_MODE")
    assert error["severity"] == "error"
    assert "Markdown-only" in error["message"]
    assert _image_validation_codes(payload) == []


def test_tex_project_with_an_image_marker_in_main_is_flagged(tmp_path: Path) -> None:
    root = _project(tmp_path, "tex")
    main = root / "report.tex"
    main.write_text(
        main.read_text(encoding="utf-8").replace(
            "\\end{document}", "[[REPORTKIT-IMAGE:img:pump-housing]]\n\\end{document}",
        ),
        encoding="utf-8",
    )
    _, payload = _check(root)
    assert "RK_IMAGE_SLOTS_TEX_MODE" in _codes(payload)


def test_commented_image_marker_in_tex_is_ignored(tmp_path: Path) -> None:
    root = _project(tmp_path, "tex")
    main = root / "report.tex"
    main.write_text(
        main.read_text(encoding="utf-8").replace(
            "\\end{document}", "% [[REPORTKIT-IMAGE:img:pump-housing]]\n\\end{document}",
        ),
        encoding="utf-8",
    )
    _, payload = _check(root)
    assert "RK_IMAGE_SLOTS_TEX_MODE" not in _codes(payload)


def test_markdown_project_keeps_image_validation(tmp_path: Path) -> None:
    root = _project(tmp_path, "markdown")
    (root / "image-slots.yaml").write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    _, payload = _check(root)
    assert "RK_VALIDATION_ORPHAN_IMAGE_DECLARATION" in _codes(payload)
    assert "RK_IMAGE_SLOTS_TEX_MODE" not in _codes(payload)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_check_discoverability_gates.py -q`

Expected failures:
- `test_check_warns_when_the_composition_brief_is_missing` (StopIteration)
- `test_tex_project_with_an_image_manifest_gets_one_actionable_error`
- `test_tex_project_with_an_image_marker_in_main_is_flagged`

The other four may already pass.

- [ ] **Step 3: Register the codes**

In `python_scripts/reportkit/diagnostics.py`, add these entries inside `DIAGNOSTIC_CODES`, after the `"RK_TARGET_IMPLICIT"` entry:

```python
    "RK_COMPOSITION_BRIEF_MISSING": {
        "type": "target_contract", "severity": "warning", "exit_code": 0,
        "remediation": (
            "No composition brief was found, so the target's composition audit did not run. Rerun "
            "`reportkit init <project-dir> --publication-type <type> --theme <theme> --source-mode <tex|markdown>` "
            "to scaffold composition-brief.json without overwriting existing files."
        ),
    },
    "RK_IMAGE_SLOTS_TEX_MODE": {
        "type": "target_contract", "severity": "error", "exit_code": 3,
        "remediation": (
            "Image slots are Markdown-only. Either switch the project to Markdown with `reportkit target set "
            "--source-mode markdown` (if the format allows it), or remove image-slots.yaml and the "
            "[[REPORTKIT-IMAGE:...]] markers and place local images with the target's figure primitives. "
            "See references/callouts-and-image-slots.md."
        ),
    },
```

- [ ] **Step 4: Add the TeX image gate**

In `python_scripts/reportkit/tex_target.py`, add this import after `from .diagnostics import make_diagnostic`:

```python
from .image_slots import IMAGE_SENTINEL_MARKER, IMAGE_SLOTS_FILENAME
```

Then add this function directly after `tex_gates`:

```python
def tex_image_slot_gate(root: Path, state: TargetState) -> list[dict[str, Any]]:
    """Flag image slots in a direct-TeX project, where the build never places them."""
    if state.source_mode != "tex":
        return []
    reasons: list[str] = []
    manifest = root / IMAGE_SLOTS_FILENAME
    if manifest.is_file():
        reasons.append(f"declares {IMAGE_SLOTS_FILENAME}")
    try:
        source = (root / state.main).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        source = ""
    if IMAGE_SENTINEL_MARKER in _without_tex_comments(source).upper():
        reasons.append(f"{state.main} contains a [[REPORTKIT-IMAGE:...]] marker")
    if not reasons:
        return []
    return [make_diagnostic(
        "target_contract",
        f"Image slots are Markdown-only, but this direct-TeX project {' and '.join(reasons)}; "
        "the build would not place these images.",
        code="RK_IMAGE_SLOTS_TEX_MODE",
        source={"file": IMAGE_SLOTS_FILENAME if manifest.is_file() else state.main},
    )]
```

- [ ] **Step 5: Wire both gates into `check`**

In `python_scripts/reportkit/cli.py`:

1. Change the import at line 58 to:

   ```python
   from .tex_target import engine_gate, tex_gates, tex_image_slot_gate
   ```

2. Replace the body of `_target_diagnostics` from `diagnostics = list(target_gate(state))` through `return diagnostics, composition` with:

   ```python
       diagnostics = list(target_gate(state))
       if state.source_mode == "tex":
           diagnostics.extend(tex_gates(state, root / state.main))
           diagnostics.extend(tex_image_slot_gate(root, state))
       diagnostics.extend(engine_gate(state, engine))
       composition = None
       brief = find_brief(root, state)
       if brief is not None:
           tex = _composition_tex(args, root, state)
           if tex is not None and tex.is_file():
               composition = audit_source(tex, brief, state)
               diagnostics.extend(composition.get("diagnostics", []))
       elif state.declared_by != "default":
           # An undeclared target already fails RK_TARGET_UNDECLARED; only a
           # declared one should hear that its composition audit was skipped.
           diagnostics.append(make_diagnostic(
               "target_contract",
               "No composition brief (composition-brief.json or editorial-brief.json) was found; "
               "the composition audit was skipped.",
               code="RK_COMPOSITION_BRIEF_MISSING",
           ))
       return diagnostics, composition
   ```

3. In `_run_check`, insert this immediately before the line `loop_diagnostics, composition = _target_diagnostics(args, root, state, engine_override)`:

   ```python
       if state.source_mode == "tex":
           # Image-slot validation assumes Markdown sentinels; in direct TeX its
           # orphan and missing-file findings point at a fix that cannot work.
           # RK_IMAGE_SLOTS_TEX_MODE from _target_diagnostics replaces them.
           diagnostics = [
               item for item in diagnostics
               if not (str(item.get("code", "")).startswith("RK_VALIDATION_") and "IMAGE" in str(item.get("code", "")))
           ]
   ```

- [ ] **Step 6: Run the new tests**

Run: `python3 -m pytest tests/test_check_discoverability_gates.py -q`
Expected: 7 passed.

- [ ] **Step 7: Run the suites that exercise `check`**

Run: `python3 -m pytest tests/test_loop_contract.py tests/test_reportkit_vnext.py tests/test_agent_contract.py tests/test_callout_titles_and_image_slots.py publication_pipeline/tests -q`
Expected: all pass.

If a pre-existing test now fails because a declared fixture project has no brief and the test asserts an exact diagnostic list, add a brief to that fixture. Copy the target's `composition_brief_example` from `PUBLICATION_TYPES`. Do not weaken the new warning.

- [ ] **Step 8: Lint and commit**

```bash
ruff check python_scripts/reportkit/diagnostics.py python_scripts/reportkit/tex_target.py python_scripts/reportkit/cli.py tests/test_check_discoverability_gates.py
git add python_scripts/reportkit/diagnostics.py python_scripts/reportkit/tex_target.py python_scripts/reportkit/cli.py tests/test_check_discoverability_gates.py
git commit -m "feat(check): flag a skipped composition audit and TeX-mode image slots

check passed silently when no composition brief existed, and a direct-TeX
project with image-slots.yaml got orphan-declaration errors whose fix cannot
render. Add RK_COMPOSITION_BRIEF_MISSING (warning) and RK_IMAGE_SLOTS_TEX_MODE
(error), and drop the misleading image validation findings in TeX mode.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `status` reports unresolved image slots at delivery

**Files:**
- Modify: `python_scripts/reportkit/status.py` (`collect_status`, lines 92–156)
- Modify: `python_scripts/reportkit/loop.py`. In `next_step`'s `status` branch, change the `elif visual_review in {"done", "unavailable"}:` clause.
- Modify: `schemas/reportkit-status.schema.json` (`properties`)
- Test: `tests/test_status_unresolved_images.py`

**Interfaces:**
- Consumes:
  - `build-report.json` key `unresolved_image_slots`: a list of `{"slug", "asset_state", "replacement_path", "source_location", "reason"}`. `publication_pipeline/scripts/publication_build.py` writes it at about line 1391.
  - `collect_status` already loads the newest report via `_latest_build_report(root)`.
- Produces:
  - `collect_status(root)` result key `unresolved_images: list[dict]`. Each item is `{"slug": str, "replacement_path": str | None, "reason": str}`. The list is empty when there is no report.
  - `collect_status(root)` result key `image_caveat: str | None`.
  - At delivery, `next_step("status", ...)["reason"]` mentions `image_caveat` when `unresolved_images` is non-empty.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_status_unresolved_images.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from reportkit.status import collect_status


REPO = Path(__file__).resolve().parents[1]
ITEM = {
    "slug": "field-photo",
    "asset_state": "placeholder",
    "replacement_path": "assets/images/field-photo.jpg",
    "source_location": {"file": "manuscript/01-fixture.md", "line": 27},
    "reason": "missing image file assets/images/field-photo.jpg",
}


def _declared_project(tmp_path: Path) -> Path:
    root = tmp_path / "publication"
    result = subprocess.run(
        [
            str(REPO / "reportkit"), "target", "set", "--source-root", str(root),
            "--publication-type", "technical-report", "--theme", "default", "--source-mode", "markdown",
            "--request", "test publication", "--json",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return root


def _write_report(root: Path, unresolved: object) -> None:
    report = root / "build" / "combined" / "build-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({
        "passed": True,
        "diagnostics": [],
        "unresolved_image_slots": unresolved,
    }), encoding="utf-8")


def test_status_lists_unresolved_image_slots_from_the_latest_build(tmp_path: Path) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, [ITEM])
    status = collect_status(root)
    assert status["unresolved_images"] == [{
        "slug": "field-photo",
        "replacement_path": "assets/images/field-photo.jpg",
        "reason": "missing image file assets/images/field-photo.jpg",
    }]
    assert "field-photo" in status["image_caveat"]


def test_status_has_no_image_caveat_when_every_slot_is_resolved(tmp_path: Path) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, [])
    status = collect_status(root)
    assert status["unresolved_images"] == []
    assert status["image_caveat"] is None


def test_status_without_a_build_report_has_empty_image_fields(tmp_path: Path) -> None:
    status = collect_status(_declared_project(tmp_path))
    assert status["unresolved_images"] == []
    assert status["image_caveat"] is None


@pytest.mark.parametrize("unresolved", ["field-photo", {"slug": "x"}, [{"reason": "no slug"}, "text", None]])
def test_status_skips_malformed_unresolved_entries(tmp_path: Path, unresolved: object) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, unresolved)
    status = collect_status(root)
    assert status["unresolved_images"] == []
    assert status["image_caveat"] is None


def test_delivery_next_step_names_unresolved_images(tmp_path: Path) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, [ITEM])
    (root / "build" / "review.json").write_text(json.dumps({"visual_review": "done"}), encoding="utf-8")
    status = collect_status(root)
    assert status["next_step"]["command"].startswith("Deliver the publication")
    assert "image_caveat" in status["next_step"]["reason"]


def test_status_with_image_fields_matches_the_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REPO / "schemas" / "reportkit-status.schema.json").read_text(encoding="utf-8"))
    root = _declared_project(tmp_path)
    for unresolved in ([ITEM], []):
        _write_report(root, unresolved)
        jsonschema.Draft202012Validator(schema).validate(collect_status(root))
    assert {"unresolved_images", "image_caveat"} <= set(schema["properties"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_status_unresolved_images.py -q`
Expected: failures with `KeyError: 'unresolved_images'`, and the schema assertion fails.

- [ ] **Step 3: Read the slots in `collect_status`**

In `python_scripts/reportkit/status.py`, insert this immediately before the line `brief_path = find_brief(root, state)` inside `collect_status`:

```python
    unresolved_images: list[dict[str, Any]] = []
    raw_unresolved = report.get("unresolved_image_slots") if report else None
    for item in raw_unresolved if isinstance(raw_unresolved, list) else []:
        if isinstance(item, dict) and isinstance(item.get("slug"), str) and item["slug"]:
            unresolved_images.append({
                "slug": item["slug"],
                "replacement_path": item.get("replacement_path"),
                "reason": str(item.get("reason") or ""),
            })
    image_caveat = None
    if unresolved_images:
        slugs = ", ".join(item["slug"] for item in unresolved_images)
        image_caveat = (
            f"{len(unresolved_images)} image slot(s) are unresolved ({slugs}); name them in the delivery "
            "message and do not present placeholders as final images."
        )
```

Then add two keys to the `result` dict, after `"delivery_caveat": caveat,`:

```python
        "unresolved_images": unresolved_images,
        "image_caveat": image_caveat,
```

- [ ] **Step 4: Name the caveat in the delivery `next_step`**

In `python_scripts/reportkit/loop.py`, in `next_step`'s `status` branch, replace:

```python
        elif visual_review in {"done", "unavailable"}:
            destination, reason = "Deliver the publication and quote the TARGET line from this status output.", "The loop state is ready for the delivery message."
```

with:

```python
        elif visual_review in {"done", "unavailable"}:
            destination = "Deliver the publication and quote the TARGET line from this status output."
            reason = "The loop state is ready for the delivery message."
            if outcome.get("unresolved_images"):
                reason += " Include image_caveat: the build still has unresolved image slots."
```

- [ ] **Step 5: Document the fields in the schema**

In `schemas/reportkit-status.schema.json`, add these entries to `properties`, after `"delivery_caveat"`:

```json
    "unresolved_images": {
      "type": "array",
      "description": "Image slots the latest build left unresolved (missing file or pending rights).",
      "items": {
        "type": "object",
        "required": ["slug", "reason"],
        "properties": {
          "slug": {"type": "string"},
          "replacement_path": {"type": ["string", "null"]},
          "reason": {"type": "string"}
        },
        "additionalProperties": true
      }
    },
    "image_caveat": {"type": ["string", "null"], "description": "Mandatory text for the delivery message when image slots are unresolved."},
```

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest tests/test_status_unresolved_images.py tests/test_loop_contract.py -q`
Expected: all pass.

- [ ] **Step 7: Lint and commit**

```bash
ruff check python_scripts/reportkit/status.py python_scripts/reportkit/loop.py tests/test_status_unresolved_images.py
git add python_scripts/reportkit/status.py python_scripts/reportkit/loop.py schemas/reportkit-status.schema.json tests/test_status_unresolved_images.py
git commit -m "feat(status): report unresolved image slots at delivery

build-report.json already lists unresolved image slots, but status ignored
them, so a draft with IMAGE NEEDED placeholders could be delivered without
comment. Status now returns unresolved_images and image_caveat, and the
delivery next_step names the caveat.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Reference docs for Markdown forms, project files, and image routing

**Files:**
- Create: `references/markdown-authoring.md`
- Modify: `references/callouts-and-image-slots.md`. Edit the "## Declare an image slot" section.
- Modify: `references/feature-article-authoring.md`. Add a section before `## References and contents`.
- Modify: `references/presentation-authoring.md`. Add a section before `## References and contents`.
- Modify: `references/book-authoring.md`. Add a section before `## References and contents`.
- Test: `tests/test_skill_discoverability_docs.py` (create)

**Interfaces:**
- Consumes:
  - `reportkit.markdown_forms.MARKDOWN_FORMS_DOCS` (Task 1)
  - the code `RK_IMAGE_SLOTS_TEX_MODE` (Task 2)
- Produces:
  - `references/markdown-authoring.md` with the anchors `#markdown-forms`, `#project-files`, `#brand-overrides`, and `#direct-tex-projects`. Task 5 links to them.
  - `tests/test_skill_discoverability_docs.py` with helper `_read(path: str) -> str`. Task 5 appends to this file.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_discoverability_docs.py`:

```python
from __future__ import annotations

from pathlib import Path

from reportkit.markdown_forms import MARKDOWN_FORMS_DOCS


REPO = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def test_markdown_authoring_reference_covers_every_form() -> None:
    text = _read(MARKDOWN_FORMS_DOCS)
    for needle in (
        "## Markdown forms", "## Project files", "## Brand overrides", "## Direct TeX projects",
        "[[REPORTKIT-VISUAL:fig:", "fragments/fig-", "[[REPORTKIT-IMAGE:img:", "```reportkit",
        "links.yaml", "sources.yaml", "brand:", "venture", "RK_IMAGE_SLOTS_TEX_MODE",
        "callouts-and-image-slots.md",
    ):
        assert needle in text, needle


def test_image_slot_guide_states_markdown_only_and_credit_rule() -> None:
    text = _read("references/callouts-and-image-slots.md")
    assert "Image slots are Markdown-only" in text
    assert "RK_IMAGE_SLOTS_TEX_MODE" in text
    assert "do not add `\\source{...}`" in text


def test_format_guides_route_photographs() -> None:
    feature = _read("references/feature-article-authoring.md")
    assert "## Photographs and illustrations" in feature
    assert "openingvisual" in feature and "Image slots are Markdown-only" in feature
    for guide in ("references/presentation-authoring.md", "references/book-authoring.md"):
        text = _read(guide)
        assert "## Photographs and illustrations" in text, guide
        assert "markdown-authoring.md" in text, guide
    assert "brand-overrides" in _read("references/presentation-authoring.md")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_skill_discoverability_docs.py -q`
Expected: `FileNotFoundError` for `references/markdown-authoring.md`, plus assertion failures.

- [ ] **Step 3: Create `references/markdown-authoring.md`**

````markdown
# Markdown authoring and project files

Markdown sources accept a small set of ReportKit forms besides ordinary
Markdown. `reportkit context --source-root <project> --slice primitives --json`
lists them under `markdown_forms`, next to the target's TeX primitives. Raw
TeX is disabled in Markdown; trusted TeX lives only in `fragments/`.

## Markdown forms

### Directives

A fenced `reportkit` block calls a primitive listed for your target. Values
are plain text:

```reportkit redflag
title: Supplier exposure
content: The estimate depends on one supplier renewing its contract.
```

Add `fragment: <name>.tex` to include a trusted file from `fragments/`
unchanged. Callout choice and titles are covered in
[Callouts and image slots](callouts-and-image-slots.md).

### Visual markers

Put a diagram or chart in a Markdown manuscript with a marker on its own line:

```markdown
[[REPORTKIT-VISUAL:fig:process-flow]]
```

Write the figure in `fragments/fig-process-flow.tex`, for example a
`diagram` environment with `caption` and `source` options. Use each slug
once. Chart images come from `rkv.save_figure` ([charts](charts.md)).

### Image slots

Use an image slot for a photograph or an observed state that prose or a
diagram cannot show:

```markdown
[[REPORTKIT-IMAGE:img:pump-housing]]
```

Declare the slot in `image-slots.yaml` and put the file at
`assets/images/pump-housing.<png|jpg|jpeg|pdf>` when it exists. A draft
build shows an `IMAGE NEEDED` placeholder until then. The fields, aspect
ratios, and rights rules are in
[Callouts and image slots](callouts-and-image-slots.md#declare-an-image-slot).
`reportkit status` lists unresolved slots as `image_caveat`; repeat that
text when you deliver.

## Project files

Optional files at the project root. `reportkit check` validates them.

`links.yaml` names external links. `type` is one of `citation`,
`documentation`, `repository`, `dataset`, `further_reading`, or
`interactive_resource`. TeX sources and fragments reference a link with
`\RKLink{<key>}`.

```yaml
links:
  field-survey-data:
    url: https://example.org/survey
    label: Field inspection survey
    type: dataset
```

`sources.yaml` records the evidence behind the publication and which chapter
uses it:

```yaml
sources:
  field-survey:
    type: dataset
    title: Field inspection survey
    file: data/survey.csv
    links:
      - field-survey-data
chapters:
  - id: findings
    title: Findings
    purpose: Report what the inspection found
    sources:
      - field-survey
```

`image-slots.yaml` declares image slots; see above. Bibliography files are
covered in [Bibliography and contents](bibliography-and-contents.md).

## Brand overrides

A top-level `brand:` section in `publication.yaml` sets an organisation's
colours, logo, and display font. Only themes that opt in accept it; today
that is `venture`. Other themes reject it.

```yaml
brand:
  primary: "#0B3D91"
  secondary: "#F2A900"
  logo: assets/logo.pdf
  display_font: Inter
```

Colours must be six-digit `#RRGGBB` values. The logo must be an existing
file inside the project.

## Direct TeX projects

Visual markers and image slots are Markdown-only. A direct-TeX project,
including every `feature-article`, places figures with its target's
primitives and local files. Record the source and licence of every
photograph you include. If a TeX project contains `image-slots.yaml` or an
uncommented `[[REPORTKIT-IMAGE:...]]` marker, `reportkit check` fails with
`RK_IMAGE_SLOTS_TEX_MODE`.
````

- [ ] **Step 4: Update `references/callouts-and-image-slots.md`**

Replace the first paragraph under `## Declare an image slot`:

```markdown
Use a real image when it clarifies an object's appearance, a place, or an
observed state that prose or a semantic diagram cannot convey as well. If a
suitable licensable image is available, put it at the declared local path,
record its source and terms, and inspect the crop and legibility. ReportKit
builds do not fetch remote images.
```

with:

```markdown
Use a real image when it clarifies an object's appearance, a place, or an
observed state that prose or a semantic diagram cannot convey as well. If a
suitable licensable image is available, put it at the declared local path,
record its source and terms, and inspect the crop and legibility. ReportKit
builds do not fetch remote images.

Image slots are Markdown-only. In a direct-TeX project, including every
`feature-article`, `reportkit check` fails with `RK_IMAGE_SLOTS_TEX_MODE`
if it finds `image-slots.yaml` or an image marker. Place local images there
with the target's figure primitives instead; see
[Markdown authoring](markdown-authoring.md#direct-tex-projects).
```

Then replace the final paragraph of the file:

```markdown
Record truthful source, creator, licence, attribution, and restrictions for
every supplied image. Use an explicit pending value while rights are being
confirmed; pending rights keep the slot unresolved. Never infer a licence or
present a placeholder as documentary evidence. The engine's generic fixtures
use only locally created graphics.
```

with:

```markdown
Record truthful source, creator, licence, attribution, and restrictions for
every supplied image. Use an explicit pending value while rights are being
confirmed; pending rights keep the slot unresolved. Never infer a licence or
present a placeholder as documentary evidence. The engine's generic fixtures
use only locally created graphics.

The printed credit line comes from these fields, so do not add `\source{...}`
for an image slot. `reportkit status` lists slots the latest build left
unresolved under `image_caveat`; repeat that text in the delivery message.
```

- [ ] **Step 5: Add the per-format sections**

In `references/feature-article-authoring.md`, insert this immediately before `## References and contents`:

```markdown
## Photographs and illustrations

A feature article is direct TeX, and Image slots are Markdown-only. Place a
lead photograph or illustration in `openingvisual` and credit it with its
`credit` argument; credit inline images inside `featureexhibit` with
`\imagecredit{...}`. Keep the file under `assets/`, record its source and
licence in the project, and never present a placeholder rule as the final
image. See [Markdown authoring](markdown-authoring.md#direct-tex-projects).

```

In `references/presentation-authoring.md`, insert this immediately before `## References and contents`:

```markdown
## Photographs and illustrations

In a Markdown deck, place a photograph with an image slot and a diagram or
chart with a visual marker; both are listed under `markdown_forms` in the
primitives slice. See [Markdown authoring](markdown-authoring.md). The
`venture` theme also accepts organisation colours and a logo through
[brand overrides](markdown-authoring.md#brand-overrides).

```

In `references/book-authoring.md`, insert this immediately before `## References and contents`:

```markdown
## Photographs and illustrations

In Markdown chapters, place a photograph with an image slot and a diagram or
chart with a visual marker; see [Markdown authoring](markdown-authoring.md).
Direct-TeX books use the target's figure primitives with local files.

```

- [ ] **Step 6: Run the tests and the docs check**

Run: `python3 -m pytest tests/test_skill_discoverability_docs.py -q`
Expected: 3 passed.

Run: `./reportkit docs --check --json`
Expected: exit 0. Generated contract blocks are untouched.

- [ ] **Step 7: Commit**

```bash
git add references/markdown-authoring.md references/callouts-and-image-slots.md references/feature-article-authoring.md references/presentation-authoring.md references/book-authoring.md tests/test_skill_discoverability_docs.py
git commit -m "docs: route agents to Markdown forms, project files, and photographs

Add references/markdown-authoring.md for visual markers, image slots,
directive fences, links.yaml, sources.yaml, and brand overrides; state that
image slots are Markdown-only; and give each format guide a photographs
section.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: SKILL.md loop, stop rules, and references

**Files:**
- Modify: `SKILL.md`:
  - loop table, lines 12–21
  - stop rules, line 44
  - "Write for the decision", line 52
  - references table, line 66
- Test: `tests/test_skill_discoverability_docs.py`. Append to the file created in Task 4.

**Interfaces:**
- Consumes:
  - the anchors in `references/markdown-authoring.md` (Task 4)
  - the `status` field `image_caveat` (Task 3)
  - the slice key `markdown_forms` (Task 1)
- Produces: the agent-facing SKILL.md text. Nothing downstream imports it.

- [ ] **Step 1: Append the failing tests**

In `tests/test_skill_discoverability_docs.py`, add `import re` to the top-level imports (after `from pathlib import Path`), then append:

```python
def _skill_links() -> list[str]:
    return [
        link for link in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", _read("SKILL.md"))
        if not link.startswith(("http://", "https://"))
    ]


def test_every_skill_link_resolves() -> None:
    assert [link for link in _skill_links() if not (REPO / link).exists()] == []


def test_stop_rule_admits_markdown_forms() -> None:
    skill = _read("SKILL.md")
    assert "Use only primitives and Markdown forms listed by" in skill
    assert "Use only primitives listed by" not in skill


def test_loop_includes_preflight_inspect_and_diagnose() -> None:
    skill = _read("SKILL.md")
    assert "| Preflight | `reportkit doctor --require full-build --json`" in skill
    assert "reportkit inspect" in skill
    assert "reportkit diagnose" in skill
    assert "image_caveat" in skill


def test_skill_routes_images_and_project_files() -> None:
    skill = _read("SKILL.md")
    for reference in (
        "references/markdown-authoring.md", "references/licensing.md", "references/accessibility-tagging.md",
    ):
        assert f"]({reference}" in skill, reference
    assert "image slot" in skill
    assert "not `\\source`" in skill
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_skill_discoverability_docs.py -q`
Expected: the four new tests fail; the Task 4 tests pass.

- [ ] **Step 3: Edit the loop table**

In `SKILL.md`, insert this row between the `| Scaffold |` row and the `| Author |` row:

```markdown
| Preflight | `reportkit doctor --require full-build --json` | Confirms the toolchain can build a PDF before you promise one. |
```

Replace the `| Author |` row (note that the original uses a typographic apostrophe in "target’s") with:

```markdown
| Author | `reportkit context --source-root <project> --slice primitives --json` | Load the target’s primitives and, for Markdown sources, its `markdown_forms`. |
```

Replace the `| Build |`, `| Review |`, and `| Deliver |` rows with:

```markdown
| Build | `reportkit build --source-root <project> --json` | Builds Markdown or direct TeX through the target gates. On failure, `reportkit diagnose <log> --source-root <project> --json` maps the TeX log to source lines. |
| Review | `reportkit render --source-root <project> --pages 1 --json` and `reportkit inspect <pdf> --source-root <project> --json`; then `reportkit review --source-root <project> --visual-review <done or unavailable>` | Render pages, check fonts, links, and bookmarks, and record the manual review. |
| Deliver | `reportkit status --source-root <project> --json` | Recover the saved state, quote its TARGET line, and repeat any `delivery_caveat` or `image_caveat`. |
```

- [ ] **Step 4: Edit the stop rules**

Replace:

```markdown
- Use only primitives listed by `reportkit context --slice primitives` for your target.
```

with:

```markdown
- Use only primitives and Markdown forms listed by `reportkit context --source-root <project> --slice primitives` for your target.
- Visual markers and image slots are Markdown-only; in a direct-TeX project use the target's figure primitives.
```

- [ ] **Step 5: Edit "Write for the decision"**

Replace:

```markdown
- Choose visuals to answer a reader’s question. Cite every figure and diagram with `\source{...}`; a conceptual visual may use `Conceptual diagram.` as its source.
```

with:

```markdown
- Choose visuals to answer a reader’s question. Cite every figure and diagram with `\source{...}`; a conceptual visual may use `Conceptual diagram.` as its source. An image slot takes its credit from `image-slots.yaml`, not `\source`.
- Use a photograph only when it shows an object, place, or observed state that prose or a diagram cannot. In Markdown, declare an image slot and leave the file absent until a licensable local asset exists; never invent rights, and name unresolved slots at delivery.
```

- [ ] **Step 6: Edit the References table**

Replace:

```markdown
| Callouts and image slots | [Callouts and image slots](references/callouts-and-image-slots.md) |
```

with:

```markdown
| Callouts, photographs, and image slots | [Callouts and image slots](references/callouts-and-image-slots.md), [licensing](references/licensing.md) |
| Markdown forms, project files, brand | [Markdown authoring and project files](references/markdown-authoring.md), [brand overrides](references/markdown-authoring.md#brand-overrides) |
| Accessibility | [Accessibility tagging](references/accessibility-tagging.md) |
```

- [ ] **Step 7: Run the tests**

Run: `python3 -m pytest tests/test_skill_discoverability_docs.py -q`
Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
ruff check tests/test_skill_discoverability_docs.py
git add SKILL.md tests/test_skill_discoverability_docs.py
git commit -m "docs(skill): admit Markdown forms and add preflight, inspect, and image guidance

The stop rule excluded every Markdown-only form, the loop omitted doctor,
inspect, and diagnose, and nothing in SKILL.md suggested photographs or
image slots. Link the new Markdown authoring, licensing, and accessibility
references, and tell the agent to repeat image_caveat at delivery.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Changelog and full verification

**Files:**
- Modify: `CHANGELOG.md`. Add entries under `## [Unreleased]`.

**Interfaces:**
- Consumes: everything above.
- Produces: a verified branch, ready for review.

- [ ] **Step 1: Add the changelog entries**

Under `## [Unreleased]` → `### Added` in `CHANGELOG.md`, append:

```markdown
- Agents following SKILL.md now discover Markdown-only authoring forms:
  - `reportkit context --slice primitives` lists visual markers, image slots,
    directive fences, `links.yaml`, and `sources.yaml` under `markdown_forms`.
  - The new `references/markdown-authoring.md` documents these forms, project
    files, and brand overrides.
  - SKILL.md now covers photographs and image slots, a `doctor` preflight,
    `inspect` during review, and `diagnose` on build failure.
- `reportkit check` reports when no composition brief exists
  (`RK_COMPOSITION_BRIEF_MISSING`), and when a direct-TeX project uses
  Markdown-only image slots (`RK_IMAGE_SLOTS_TEX_MODE`). In TeX mode it no
  longer gives the misleading orphan-declaration errors.
- `reportkit status` returns `unresolved_images` and `image_caveat` from the
  latest build, so unfinished images are named at delivery.
```

- [ ] **Step 2: Run the full suite**

Run: `python3 -m pytest tests publication_pipeline/tests -q`
Expected: all pass. Skips for absent optional tools (jsonschema, TeX engines) are acceptable; report them.

- [ ] **Step 3: Lint and check the docs**

Run: `ruff check python_scripts tests && ./reportkit docs --check --json`
Expected: both exit 0.

- [ ] **Step 4: Smoke-test the agent path end to end**

Run in the scratchpad (outside the repo):

```bash
P="$(mktemp -d)/pub"
./reportkit target set --source-root "$P" --publication-type technical-report --theme default --source-mode markdown --request "smoke" --json >/dev/null
./reportkit init "$P" --publication-type technical-report --theme default --source-mode markdown --json >/dev/null
./reportkit context --source-root "$P" --slice primitives --json | python3 -c "import json,sys; f=json.load(sys.stdin)['content']['markdown_forms']; print([x['name'] for x in f['forms']])"
rm "$P/composition-brief.json"
./reportkit check --source-root "$P" --json | python3 -c "import json,sys; print([d['code'] for d in json.load(sys.stdin)['diagnostics']])"
```

Expected output:

```
['directive', 'visual', 'image_slot', 'links', 'sources']
['RK_COMPOSITION_BRIEF_MISSING']
```

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record skill discoverability fixes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
