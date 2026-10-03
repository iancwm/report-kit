# BibTeX Bibliography and Themed Contents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Proposed · not started · 3 October 2026

**Goal:** Let any ReportKit publication cite entries from a consumer `.bib` file and render a themed reference list and contents page for each of the six publication types.

**Architecture:** A generated `reportkit-bibliography-config.tex` (written only when `publication.yaml` has a `bibliography` section) makes the new engine-wide `reportkit-bibliography.sty` load `natbib` and expose `\RKBibliography`; without it the package is inert, so existing documents are unchanged. A new `reportkit-contents.sty` owns the `\RKContents` dispatcher. Each publication-type package supplies skin hooks (`\RKBibSkinBegin`, `\RKBibSkinItemFont`, `\RKContentsSkin`, and for slides `\RKBibRender`) built only from theme tokens. The build adds a `bibtex` pass and a third TeX pass only when the first pass's `.aux` contains a `\citation`.

**Tech Stack:** LaTeX (natbib, `plainnat`/`unsrtnat`, Beamer), BibTeX, Pandoc `--natbib`, Python 3 stdlib, pytest, PyMuPDF.

**Spec:** [docs/superpowers/specs/2026-10-03-reportkit-bibliography-and-contents-spec.md](../specs/2026-10-03-reportkit-bibliography-and-contents-spec.md)

## Global Constraints

- BibTeX + natbib only. No biblatex, biber, CSL, citeproc or new Python dependency.
- Styles: `numeric` → natbib `numbers,sort&compress` + `unsrtnat`; `author-year` → natbib `authoryear,round` + `plainnat`.
- Per-type defaults: technical-report numeric/References/Contents; book author-year/References/Contents; feature-article author-year/References/In this issue; executive-brief numeric/Sources/Contents; equity-research author-year/Sources/In this report; presentation numeric/References/Agenda.
- Documents without a `bibliography` section: same two TeX passes, natbib not loaded, existing tests and baselines unchanged (spec B6, AC5).
- Skins use theme tokens only — no literal `\fontsize` or `\definecolor` in publication-type packages.
- Manual environments (`bookreferences`, `featurereferences`, `briefsources`, `referenceslide`, `\referenceitem`) stay unchanged.
- `bibtex` runs through `run_limited` with the TeX environment (`openout_any=p`, `LC_ALL=C`, `SOURCE_DATE_EPOCH=1`, `FORCE_SOURCE_DATE=1`, `TZ=UTC`).
- Diagnostic codes exactly as spec §5: `RK_BIBLIOGRAPHY_FILE_MISSING`, `RK_BIBLIOGRAPHY_STYLE_INVALID`, `RK_BIBLIOGRAPHY_DUPLICATE_KEY`, `RK_CITATION_UNDEFINED`, `RK_CITATION_WITHOUT_BIBLIOGRAPHY`, `RK_BIBLIOGRAPHY_NOT_PLACED`; build codes `RK_BIBTEX_MISSING` (exit 5), `RK_BIBTEX_FAILURE` (exit 4).
- Presentation references paginate at eight entries per frame with a `(cont.)` continuation title.
- New TeX primitives carry `<reportkit-contract>` blocks and are mapped in `primitive_targets.py` (new entries fail closed otherwise).
- Generated reference docs change only through `reportkit docs --write`.

### Plan-time amendments to the spec (record them in the spec in Task 8)

1. Settings reach TeX through a generated `reportkit-bibliography-config.tex`, not `reportkit-options.tex` (which is a checked-in parser, not generated). Reason: natbib must load only when configured, because `author-year` natbib raises a hard error on the plain `\bibitem`s that `bookreferences` uses.
2. `\RKContents`'s dispatcher lives in a new `reportkit-contents.sty`; the longform page becomes the `\providecommand` default skin.
3. Markdown directives are spelled the ReportKit way: `` ```reportkit references `` and `` ```reportkit contents `` (aliases for `RKBibliography` and `RKContents`), not bare `::: references`.
4. `reportkit doctor --require full-build` treats `bibtex` as part of a full build (it is present in both supported toolchains); the doctor has no project context to make it conditional.
5. Pipeline combined builds of feature-article and equity-research already call `\RKContents`; they now render the type's skin instead of the longform page. Neither has a pixel baseline.

## Review Focus

1. **A `.bib` with `@string`, `@comment`, `@preamble`, mixed-case entry types and keys with `:`/`-`/`.`** — key scanning must accept all of them and ignore the non-entries; a reasonable author expects their existing Zotero/JabRef export to work. (Pinned in Task 1.)
2. **Markdown text with e-mail addresses, `@` in code spans/fenced code, and `[@a; @b, p. 3]` groups** — only real citations count, otherwise `reportkit check` blocks on phantom undefined keys. (Pinned in Task 1.)
3. **A configured bibliography with `\RKBibliography` placed but zero citations** — bibtex would fail with "I found no \citation commands"; the build must skip bibtex and succeed with a warning, not fail. (Pinned in Task 4.)
4. **`bibliography.file` in a subdirectory (`refs/main.bib`) or with spaces/unsafe characters** — subdirectories work; unsafe names fail in `check` with a clear message rather than a cryptic bibtex error. (Pinned in Tasks 1 and 4.)
5. **A book that uses the manual `bookreferences` environment and no `bibliography` section** — must still compile identically (natbib not loaded). (Pinned in Task 3.)

---

## File Structure

| File | Responsibility |
| --- | --- |
| Create `python_scripts/reportkit/bibliography.py` | Settings model, `.bib` key scanner, citation extraction (Markdown/TeX), check diagnostics, config-file writer, aux/blg/bbl helpers. |
| Modify `python_scripts/reportkit/config.py` | Accept the `bibliography` section and profile overrides. |
| Modify `python_scripts/reportkit/publications.py` | Per-type `bibliography_style`, `bibliography_title`, `contents_title`. |
| Modify `python_scripts/reportkit/diagnostics.py` | Register the new codes. |
| Modify `python_scripts/reportkit/cli.py` | Add bibliography diagnostics to `reportkit check`. |
| Create `latex_templates/reportkit-bibliography.sty` | Config loading, natbib, `\RKBibliography`, default skin. |
| Create `latex_templates/reportkit-contents.sty` | `\RKContents` dispatcher, `\rkcontents@inline`, `\rkcontents@list`, defaults. |
| Modify `latex_templates/reportkit.cls`, `latex_templates/reportkit-slides.cls` | Load both packages before the publication-type package. |
| Modify `latex_templates/reportkit-longform.sty` | Replace `\RKContents` with a `\providecommand` page skin. |
| Modify the six publication-type packages | Type skins. |
| Modify `publication_pipeline/scripts/publication_build.py` | Stage `.bib`, write config, bibtex pass, `--natbib`, auto-placement, build report. |
| Modify `python_scripts/reportkit/markdown_directives.py` | `references`/`contents` aliases. |
| Modify `python_scripts/reportkit/primitive_targets.py` | Roles for `RKBibliography`, `RKContents`, `agendaslide`. |
| Modify `python_scripts/reportkit_doctor.py` | `bibtex` in full build. |
| Modify `schemas/reportkit-build-report.schema.json` | `bibliography` property. |
| Create `tests/test_bibliography_model.py`, `tests/test_bibliography_tex.py`, `tests/test_bibliography_skins.py`, `publication_pipeline/tests/test_bibliography_build.py` | Tests. |
| Create `tests/bibliography_helpers.py` | Shared compile helper (TeX → bibtex → TeX → TeX). |
| Create `references/bibliography-and-contents.md`; modify `SKILL.md`, six authoring guides, `TODOS.md`, spec | Docs. |

---

### Task 1: Bibliography settings, `.bib` scanning and citation extraction

**Files:**
- Create: `python_scripts/reportkit/bibliography.py`
- Modify: `python_scripts/reportkit/config.py` (constants near line 37–47, `_known_for` ~222, `_validate_and_normalize` section loop ~257)
- Modify: `python_scripts/reportkit/publications.py` (each record in `PUBLICATION_TYPES`)
- Test: `tests/test_bibliography_model.py`

**Interfaces:**
- Produces:
  - `BIB_STYLES: tuple[str, ...] = ("numeric", "author-year")`
  - `@dataclass(frozen=True) class BibliographySettings: file: str; path: Path; stem: str; style: str; title: str; include_uncited: bool`
  - `resolve_bibliography(config: dict, profile: str | None, publication_type: str, source_root: Path) -> BibliographySettings | None` — raises `BibliographyConfigError(code: str, message: str)` on invalid config.
  - `scan_bib_keys(text: str) -> list[tuple[str, int]]` — `(key, line)` in file order, duplicates kept.
  - `markdown_citation_keys(text: str) -> list[tuple[str, int]]`
  - `tex_citation_keys(text: str) -> list[tuple[str, int]]`
  - `SAFE_BIB_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.bib")`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_bibliography_model.py
"""Bibliography settings, .bib key scanning and citation extraction."""
from __future__ import annotations

from pathlib import Path

import pytest

from reportkit.bibliography import (
    BibliographyConfigError,
    markdown_citation_keys,
    resolve_bibliography,
    scan_bib_keys,
    tex_citation_keys,
)
from reportkit.config import load_publication_config
from reportkit.publications import PUBLICATION_TYPES

EXPECTED_DEFAULTS = {
    "technical-report": ("numeric", "References", "Contents"),
    "book": ("author-year", "References", "Contents"),
    "feature-article": ("author-year", "References", "In this issue"),
    "executive-brief": ("numeric", "Sources", "Contents"),
    "equity-research": ("author-year", "Sources", "In this report"),
    "presentation": ("numeric", "References", "Agenda"),
}


def test_every_publication_type_declares_reference_and_contents_defaults() -> None:
    for name, (style, title, contents) in EXPECTED_DEFAULTS.items():
        record = PUBLICATION_TYPES[name]
        assert record["bibliography_style"] == style
        assert record["bibliography_title"] == title
        assert record["contents_title"] == contents


def _write_config(root: Path, body: str) -> dict:
    (root / "publication.yaml").write_text("publication:\n  title: T\n" + body, encoding="utf-8")
    return load_publication_config(root / "publication.yaml")


def test_unconfigured_project_has_no_bibliography(tmp_path: Path) -> None:
    config = _write_config(tmp_path, "")
    assert resolve_bibliography(config, None, "book", tmp_path) is None


def test_type_defaults_apply_when_style_and_title_are_omitted(tmp_path: Path) -> None:
    (tmp_path / "references.bib").write_text("@book{a, title={A}}\n", encoding="utf-8")
    config = _write_config(tmp_path, "bibliography:\n  file: references.bib\n")
    settings = resolve_bibliography(config, None, "book", tmp_path)
    assert settings is not None
    assert (settings.style, settings.title, settings.stem) == ("author-year", "References", "references")
    assert settings.include_uncited is False


def test_overrides_and_profile_override(tmp_path: Path) -> None:
    (tmp_path / "refs").mkdir()
    (tmp_path / "refs" / "main.bib").write_text("", encoding="utf-8")
    config = _write_config(
        tmp_path,
        "bibliography:\n  file: refs/main.bib\n  style: numeric\n  title: Works cited\n  include_uncited: true\n"
        "profiles:\n  final:\n    bibliography:\n      style: author-year\n",
    )
    draft = resolve_bibliography(config, None, "book", tmp_path)
    final = resolve_bibliography(config, "final", "book", tmp_path)
    assert (draft.style, draft.title, draft.stem, draft.include_uncited) == ("numeric", "Works cited", "refs/main", True)
    assert final.style == "author-year"


def test_unknown_bibliography_key_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bibliography.format"):
        _write_config(tmp_path, "bibliography:\n  file: r.bib\n  format: apa\n")


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("bibliography:\n  file: missing.bib\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  file: ../outside.bib\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  file: 'my refs.bib'\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  style: numeric\n", "RK_BIBLIOGRAPHY_FILE_MISSING"),
        ("bibliography:\n  file: references.bib\n  style: apa\n", "RK_BIBLIOGRAPHY_STYLE_INVALID"),
    ],
)
def test_invalid_configuration_raises_coded_error(tmp_path: Path, body: str, code: str) -> None:
    (tmp_path / "references.bib").write_text("", encoding="utf-8")
    (tmp_path / "my refs.bib").write_text("", encoding="utf-8")
    config = _write_config(tmp_path, body)
    with pytest.raises(BibliographyConfigError) as excinfo:
        resolve_bibliography(config, None, "technical-report", tmp_path)
    assert excinfo.value.code == code


def test_scan_bib_keys_handles_real_world_exports() -> None:
    text = (
        "% Zotero export\n"
        "@string{jan = \"January\"}\n"
        "@Comment{jabref-meta: databaseType:bibtex;}\n"
        "@preamble{\"\\newcommand{\\noop}[1]{}\"}\n"
        "@Article{smith:2024-a,\n  title={One}}\n"
        "@BOOK{ Jones.2019 ,\n  title={Two}}\n"
        "@misc(paren_key, title={Three})\n"
        "@article{smith:2024-a, title={Dup}}\n"
    )
    assert scan_bib_keys(text) == [("smith:2024-a", 5), ("Jones.2019", 7), ("paren_key", 9), ("smith:2024-a", 10)]


def test_markdown_citation_keys_ignore_code_and_email() -> None:
    text = (
        "As shown [@smith:2024-a; @jones2019, p. 3] and @lee2020 argues.\n"
        "Write to someone@example.com about it.\n"
        "Inline `@notacite` code.\n"
        "```\n@alsonot\n```\n"
        "Suppressed author [-@kim2021].\n"
    )
    assert markdown_citation_keys(text) == [
        ("smith:2024-a", 1), ("jones2019", 1), ("lee2020", 1), ("kim2021", 7),
    ]


def test_tex_citation_keys_cover_natbib_forms_and_skip_comments() -> None:
    text = (
        "See \\citep[p.~3]{a,b} and \\citet*{c}.\n"
        "% \\citep{commented}\n"
        "\\citealp{d} \\cite{e} \\citeauthor{f} \\citeyearpar[see][]{g}\n"
        "\\nocite{*}\n"
    )
    assert tex_citation_keys(text) == [("a", 1), ("b", 1), ("c", 1), ("d", 3), ("e", 3), ("f", 3), ("g", 3)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bibliography_model.py -v`
Expected: FAIL / collection error — `ModuleNotFoundError: No module named 'reportkit.bibliography'`

- [ ] **Step 3: Add the config section**

In `python_scripts/reportkit/config.py`, after `OUTPUT_KEYS = ("directory",)` add:

```python
# Optional BibTeX bibliography (bibliography-and-contents spec §1).
BIBLIOGRAPHY_KEYS = ("file", "style", "title", "include_uncited")
```

Change `SECTIONS` to include `"bibliography"`:

```python
SECTIONS = ("publication", "document", "license", "theme", "brand", "profiles", "validation", "output", "bibliography")
```

In `_known_for` add `"bibliography": BIBLIOGRAPHY_KEYS,`. In `_validate_and_normalize` change the section loop tuple to
`("publication", "document", "license", "theme", "brand", "validation", "output", "bibliography")`.

Add a resolver next to `resolve_validation`:

```python
def resolve_bibliography_section(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    return _profile_section(config, "bibliography", profile)
```

- [ ] **Step 4: Add per-type defaults**

In `python_scripts/reportkit/publications.py`, add these three keys to each `PUBLICATION_TYPES` record (values from Global Constraints), e.g. for `technical-report`:

```python
        "bibliography_style": "numeric",
        "bibliography_title": "References",
        "contents_title": "Contents",
```

If `check_publication_registry` enforces an allowed-key set, add the three keys to it.

- [ ] **Step 5: Write `bibliography.py` (model, scanning, extraction)**

```python
"""BibTeX bibliography support (bibliography-and-contents spec).

Dependency-free: the .bib file is scanned only for entry keys; BibTeX does
all formatting. Citation extraction mirrors what Pandoc ``--natbib`` and
natbib itself will treat as citations, so ``reportkit check`` and the build
agree on which keys must exist.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .config import resolve_bibliography_section
from .publications import PUBLICATION_TYPES

BIB_STYLES: tuple[str, ...] = ("numeric", "author-year")
SAFE_BIB_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.bib")
CONFIG_FILENAME = "reportkit-bibliography-config.tex"

_BIB_ENTRY = re.compile(r"@(?P<type>[A-Za-z]+)\s*[{(]\s*(?P<key>[^,\s{}()]+)\s*,")
_BIB_NON_ENTRIES = {"string", "comment", "preamble"}
_MD_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_MD_CODE_SPAN = re.compile(r"`+[^`]*`+")
# Pandoc citation: '@' not preceded by a word character (excludes e-mail),
# key starts with a letter/digit/underscore, may contain :.#$%&-+?<>~/ internally.
_MD_CITATION = re.compile(r"(?<![\w.@])-?@(?P<key>[A-Za-z0-9_][A-Za-z0-9_:.#$%&\-+?<>~/]*[A-Za-z0-9_])")
_TEX_CITE = re.compile(
    r"\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear|citeyearpar|citenum|Citep|Citet|Citealp|Citealt|Citeauthor)\*?"
    r"(?:\s*\[[^\]]*\]){0,2}\s*\{(?P<keys>[^}]*)\}"
)


class BibliographyConfigError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class BibliographySettings:
    file: str
    path: Path
    stem: str
    style: str
    title: str
    include_uncited: bool


def resolve_bibliography(
    config: dict[str, Any], profile: str | None, publication_type: str, source_root: Path,
) -> BibliographySettings | None:
    section = resolve_bibliography_section(config, profile)
    if not section:
        return None
    record = PUBLICATION_TYPES.get(publication_type, PUBLICATION_TYPES["technical-report"])
    raw_file = section.get("file")
    if not raw_file:
        raise BibliographyConfigError("RK_BIBLIOGRAPHY_FILE_MISSING", "bibliography.file is required when a bibliography section is present")
    file = str(raw_file).replace("\\", "/")
    relative = Path(file)
    if relative.is_absolute() or ".." in relative.parts or not SAFE_BIB_PATH.fullmatch(file):
        raise BibliographyConfigError(
            "RK_BIBLIOGRAPHY_FILE_MISSING",
            f"bibliography.file must be a relative .bib path inside the project using letters, digits, '_', '-', '.', '/': {file!r}",
        )
    path = (source_root / relative).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError:
        raise BibliographyConfigError("RK_BIBLIOGRAPHY_FILE_MISSING", f"bibliography.file escapes the project: {file!r}") from None
    if not path.is_file():
        raise BibliographyConfigError("RK_BIBLIOGRAPHY_FILE_MISSING", f"bibliography.file not found: {file}")
    style = str(section.get("style") or record["bibliography_style"])
    if style not in BIB_STYLES:
        raise BibliographyConfigError(
            "RK_BIBLIOGRAPHY_STYLE_INVALID", f"bibliography.style must be one of {', '.join(BIB_STYLES)}; got {style!r}",
        )
    return BibliographySettings(
        file=file,
        path=path,
        stem=file[: -len(".bib")],
        style=style,
        title=str(section.get("title") or record["bibliography_title"]),
        include_uncited=bool(section.get("include_uncited", False)),
    )


def scan_bib_keys(text: str) -> list[tuple[str, int]]:
    keys: list[tuple[str, int]] = []
    for match in _BIB_ENTRY.finditer(text):
        if match.group("type").lower() in _BIB_NON_ENTRIES:
            continue
        keys.append((match.group("key"), text.count("\n", 0, match.start()) + 1))
    return keys


def markdown_citation_keys(text: str) -> list[tuple[str, int]]:
    keys: list[tuple[str, int]] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), 1):
        opener = _MD_FENCE.match(line)
        if opener:
            marker = opener.group(1)
            if fence is None:
                fence = marker[0] * 3
            elif marker.startswith(fence):
                fence = None
            continue
        if fence is not None:
            continue
        line = _MD_CODE_SPAN.sub("", line)
        keys.extend((match.group("key"), number) for match in _MD_CITATION.finditer(line))
    return keys


def tex_citation_keys(text: str) -> list[tuple[str, int]]:
    keys: list[tuple[str, int]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = re.sub(r"(?<!\\)%.*$", "", raw)
        for match in _TEX_CITE.finditer(line):
            for key in match.group("keys").split(","):
                key = key.strip()
                if key and key != "*":
                    keys.append((key, number))
    return keys
```

Note: `\nocite{*}` is not matched because `nocite` is not in `_TEX_CITE`'s command list.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_bibliography_model.py tests/test_publication_registry.py -v`
Expected: PASS. If `test_markdown_citation_keys_ignore_code_and_email` fails on the e-mail line, check that the `(?<![\w.@])` lookbehind is present.

- [ ] **Step 7: Commit**

```bash
git add python_scripts/reportkit/bibliography.py python_scripts/reportkit/config.py python_scripts/reportkit/publications.py tests/test_bibliography_model.py
git commit -m "feat(bibliography): add settings model, .bib key scan and citation extraction"
```

---

### Task 2: `reportkit check` bibliography diagnostics

**Files:**
- Modify: `python_scripts/reportkit/bibliography.py` (add `bibliography_diagnostics`)
- Modify: `python_scripts/reportkit/diagnostics.py` (`DIAGNOSTIC_CODES`)
- Modify: `python_scripts/reportkit/cli.py` (`_run_check`, after the font-policy check ~line 492)
- Test: `tests/test_bibliography_model.py` (append)

**Interfaces:**
- Consumes: `resolve_bibliography`, `scan_bib_keys`, `markdown_citation_keys`, `tex_citation_keys`, `BibliographyConfigError` (Task 1).
- Produces: `bibliography_diagnostics(source_root: Path, config: dict, profile: str | None, document: dict) -> list[dict]` where `document` is `resolve_document(...)` output (keys `publication_type`, `source_mode`, `main`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bibliography_model.py`:

```python
from reportkit.bibliography import bibliography_diagnostics


def _md_project(root: Path, manuscript: str, *, bib: str | None, yaml_extra: str = "") -> tuple[dict, dict]:
    (root / "manuscript").mkdir()
    (root / "manuscript" / "01.md").write_text(manuscript, encoding="utf-8")
    if bib is not None:
        (root / "references.bib").write_text(bib, encoding="utf-8")
        yaml_extra = "bibliography:\n  file: references.bib\n" + yaml_extra
    config = _write_config(root, "document:\n  publication_type: technical-report\n  source_mode: markdown\n" + yaml_extra)
    return config, {"publication_type": "technical-report", "source_mode": "markdown", "main": "report.tex"}


def _codes(diagnostics: list[dict]) -> list[tuple[str, str]]:
    return [(item["code"], item["severity"]) for item in diagnostics]


def test_clean_project_has_no_bibliography_diagnostics(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "Cited [@a].\n", bib="@book{a, title={A}}\n")
    assert bibliography_diagnostics(tmp_path, config, None, document) == []


def test_undefined_citation_is_an_error_with_location(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "Intro.\nCited [@missing].\n", bib="@book{a, title={A}}\n")
    diagnostics = bibliography_diagnostics(tmp_path, config, None, document)
    assert _codes(diagnostics) == [("RK_CITATION_UNDEFINED", "error")]
    assert diagnostics[0]["source"]["file"] == "manuscript/01.md"
    assert diagnostics[0]["source"]["line"] == 2


def test_duplicate_bib_key_is_an_error(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "[@a]\n", bib="@book{a, title={A}}\n@misc{a, title={B}}\n")
    assert _codes(bibliography_diagnostics(tmp_path, config, None, document)) == [("RK_BIBLIOGRAPHY_DUPLICATE_KEY", "error")]


def test_citations_without_bibliography_section_are_an_error(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "[@a]\n", bib=None)
    assert _codes(bibliography_diagnostics(tmp_path, config, None, document)) == [("RK_CITATION_WITHOUT_BIBLIOGRAPHY", "error")]


def test_config_errors_surface_as_configuration_diagnostics(tmp_path: Path) -> None:
    config, document = _md_project(tmp_path, "[@a]\n", bib="", yaml_extra="  style: apa\n")
    diagnostics = bibliography_diagnostics(tmp_path, config, None, document)
    assert _codes(diagnostics) == [("RK_BIBLIOGRAPHY_STYLE_INVALID", "error")]
    assert diagnostics[0]["type"] == "configuration_error"


def test_tex_source_without_rkbibliography_warns(tmp_path: Path) -> None:
    (tmp_path / "references.bib").write_text("@book{a, title={A}}\n", encoding="utf-8")
    (tmp_path / "report.tex").write_text("\\documentclass{reportkit}\n\\begin{document}\n\\citep{a}\n\\end{document}\n", encoding="utf-8")
    config = _write_config(tmp_path, "bibliography:\n  file: references.bib\n")
    document = {"publication_type": "technical-report", "source_mode": "tex", "main": "report.tex"}
    assert _codes(bibliography_diagnostics(tmp_path, config, None, document)) == [("RK_BIBLIOGRAPHY_NOT_PLACED", "warning")]


def test_tex_fragments_are_scanned(tmp_path: Path) -> None:
    (tmp_path / "references.bib").write_text("@book{a, title={A}}\n", encoding="utf-8")
    (tmp_path / "report.tex").write_text("\\citep{a}\n\\RKBibliography\n", encoding="utf-8")
    (tmp_path / "fragments").mkdir()
    (tmp_path / "fragments" / "fig-x.tex").write_text("\\citet{nope}\n", encoding="utf-8")
    config = _write_config(tmp_path, "bibliography:\n  file: references.bib\n")
    document = {"publication_type": "technical-report", "source_mode": "tex", "main": "report.tex"}
    diagnostics = bibliography_diagnostics(tmp_path, config, None, document)
    assert _codes(diagnostics) == [("RK_CITATION_UNDEFINED", "error")]
    assert diagnostics[0]["source"]["file"] == "fragments/fig-x.tex"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bibliography_model.py -v -k "diagnostic or citation or duplicate or placed or fragments"`
Expected: FAIL — `ImportError: cannot import name 'bibliography_diagnostics'`

- [ ] **Step 3: Register the codes**

In `python_scripts/reportkit/diagnostics.py`, add to `DIAGNOSTIC_CODES`:

```python
    "RK_BIBLIOGRAPHY_FILE_MISSING": {
        "type": "configuration_error", "severity": "error", "exit_code": 2,
        "remediation": "Set bibliography.file to a .bib file inside the project (letters, digits, '_', '-', '.', '/').",
    },
    "RK_BIBLIOGRAPHY_STYLE_INVALID": {
        "type": "configuration_error", "severity": "error", "exit_code": 2,
        "remediation": "Set bibliography.style to numeric or author-year, or remove it to use the publication type's default.",
    },
    "RK_BIBLIOGRAPHY_DUPLICATE_KEY": {
        "type": "publication_validation", "severity": "error", "exit_code": 3,
        "remediation": "Give every .bib entry a unique key and update citations that used the duplicate.",
    },
    "RK_CITATION_UNDEFINED": {
        "type": "publication_validation", "severity": "error", "exit_code": 3,
        "remediation": "Add the entry to the .bib file or correct the citation key. Never invent a bibliography entry.",
    },
    "RK_CITATION_WITHOUT_BIBLIOGRAPHY": {
        "type": "configuration_error", "severity": "error", "exit_code": 2,
        "remediation": "Add a bibliography section with file: <name>.bib to publication.yaml.",
    },
    "RK_BIBLIOGRAPHY_NOT_PLACED": {
        "type": "publication_validation", "severity": "warning", "exit_code": 0,
        "remediation": "Call \\RKBibliography where the reference list belongs, usually at the end of the document.",
    },
    "RK_BIBTEX_MISSING": {
        "type": "environment_error", "severity": "error", "exit_code": 5,
        "remediation": "Install bibtex (scripts/setup_tex.sh) or build in the pinned container.",
    },
    "RK_BIBTEX_FAILURE": {
        "type": "compile_failure", "severity": "error", "exit_code": 4,
        "remediation": "Fix the .bib syntax reported in the .blg log and rebuild.",
    },
```

- [ ] **Step 4: Implement `bibliography_diagnostics`**

Append to `bibliography.py`:

```python
from .diagnostics import make_diagnostic

_PLACEMENT = re.compile(r"\\RKBibliography\b")
_MD_PLACEMENT = re.compile(r"^\s{0,3}(?:`{3,}|~{3,}|:::?)\s*reportkit[\s:/]+(?:references|RKBibliography)\b", re.MULTILINE)


def _citation_sources(source_root: Path, document: dict[str, Any]) -> list[tuple[str, list[tuple[str, int]], str]]:
    """Return (relative file, citations, text) for every authored source."""
    sources: list[tuple[str, list[tuple[str, int]], str]] = []
    if str(document.get("source_mode") or "markdown") == "tex":
        candidates = [source_root / str(document.get("main") or "report.tex")]
        fragments = source_root / "fragments"
        if fragments.is_dir():
            candidates.extend(sorted(fragments.glob("*.tex")))
        extract = tex_citation_keys
    else:
        manuscript = source_root / "manuscript"
        candidates = sorted(manuscript.glob("*.md")) if manuscript.is_dir() else []
        extract = markdown_citation_keys
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        sources.append((path.relative_to(source_root).as_posix(), extract(text), text))
    return sources


def bibliography_diagnostics(
    source_root: Path, config: dict[str, Any], profile: str | None, document: dict[str, Any],
) -> list[dict[str, Any]]:
    publication_type = str(document.get("publication_type") or "technical-report")
    sources = _citation_sources(source_root, document)
    cited = [(key, file, line) for file, keys, _ in sources for key, line in keys]
    try:
        settings = resolve_bibliography(config, profile, publication_type, source_root)
    except BibliographyConfigError as exc:
        return [make_diagnostic("configuration_error", str(exc), code=exc.code, source={"file": "publication.yaml"})]
    if settings is None:
        if not cited:
            return []
        key, file, line = cited[0]
        return [make_diagnostic(
            "configuration_error",
            f"{file}:{line}: citation @{key} but publication.yaml has no bibliography section",
            code="RK_CITATION_WITHOUT_BIBLIOGRAPHY", source={"file": file, "line": line},
        )]
    diagnostics: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key, line in scan_bib_keys(settings.path.read_text(encoding="utf-8")):
        if key in seen:
            diagnostics.append(make_diagnostic(
                "publication_validation", f"{settings.file}:{line}: duplicate .bib key {key!r}",
                code="RK_BIBLIOGRAPHY_DUPLICATE_KEY", source={"file": settings.file, "line": line},
            ))
        seen.add(key)
    for key, file, line in cited:
        if key not in seen:
            diagnostics.append(make_diagnostic(
                "publication_validation", f"{file}:{line}: citation key {key!r} is not in {settings.file}",
                code="RK_CITATION_UNDEFINED", source={"file": file, "line": line},
            ))
    if cited and str(document.get("source_mode") or "markdown") == "tex":
        if not any(_PLACEMENT.search(text) for _, _, text in sources):
            diagnostics.append(make_diagnostic(
                "publication_validation", "sources cite bibliography entries but never call \\RKBibliography",
                code="RK_BIBLIOGRAPHY_NOT_PLACED", source={"file": str(document.get("main") or "report.tex")},
            ))
    return diagnostics
```

- [ ] **Step 5: Wire into `reportkit check`**

In `python_scripts/reportkit/cli.py` `_run_check`, immediately after the `font_policy_conflict` block, add:

```python
    diagnostics.extend(bibliography_diagnostics(root, config, args.profile, document))
```

and add `from .bibliography import bibliography_diagnostics` to the imports.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_bibliography_model.py tests/test_reportkit_vnext.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add python_scripts/reportkit/bibliography.py python_scripts/reportkit/diagnostics.py python_scripts/reportkit/cli.py tests/test_bibliography_model.py
git commit -m "feat(bibliography): report citation and bibliography problems in reportkit check"
```

---

### Task 3: TeX core — `reportkit-bibliography.sty`, `reportkit-contents.sty`, class loading, longform skin

**Files:**
- Create: `latex_templates/reportkit-bibliography.sty`, `latex_templates/reportkit-contents.sty`
- Modify: `latex_templates/reportkit.cls` (before the publication-type `\RequirePackage` block, ~line 95), `latex_templates/reportkit-slides.cls` (~line 64)
- Modify: `latex_templates/reportkit-longform.sty:29-33`
- Modify: `python_scripts/reportkit/primitive_targets.py`
- Create: `tests/bibliography_helpers.py`, `tests/test_bibliography_tex.py`

**Interfaces:**
- Produces (TeX):
  - Config file `reportkit-bibliography-config.tex` with exactly: `\renewcommand{\RKBibStyle}{<style>}`, `\renewcommand{\RKBibFile}{<stem>}`, `\renewcommand{\RKBibTitle}{<escaped title>}`, `\RKBibIncludeUncitedtrue|false`.
  - `\RKBibliography[<title>]` (empty/omitted → `\RKBibTitle`).
  - Skin hooks a type package may define with `\newcommand`: `\RKBibSkinBegin{title}`, `\RKBibSkinEnd`, `\RKBibSkinItemFont`, `\RKBibRender{title}` (full override; slides only), `\RKContentsSkin{title}`, `\RKContentsTitle`.
  - Helpers: `\rkcontents@inline{<separator>}`, `\rkcontents@list` (read `\jobname.toc`; call at most once per document).
  - Internal: `\rk@bib@bst` (`unsrtnat`/`plainnat`), `\ifRKBibConfigured`.
- Produces (Python test helper): `compile_with_bibliography(tmp_path: Path, *, documentclass: str, body: str, bib: str | None, style: str = "numeric", title: str = "References", include_uncited: bool = False, preamble: str = "", engine: str = "pdflatex") -> CompileResult` with fields `pdf: Path`, `log: str`, `text: str` (all pages), `pages: list[str]`, `returncode: int`, `passes: int`.

- [ ] **Step 1: Write the shared compile helper**

```python
# tests/bibliography_helpers.py
"""Compile a ReportKit document through TeX -> bibtex -> TeX -> TeX."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"


@dataclass
class CompileResult:
    pdf: Path
    log: str
    text: str
    pages: list[str]
    returncode: int
    passes: int


def write_bibliography_config(directory: Path, *, stem: str, style: str, title: str, include_uncited: bool) -> None:
    (directory / "reportkit-bibliography-config.tex").write_text(
        "% Generated for tests.\n"
        f"\\renewcommand{{\\RKBibStyle}}{{{style}}}\n"
        f"\\renewcommand{{\\RKBibFile}}{{{stem}}}\n"
        f"\\renewcommand{{\\RKBibTitle}}{{{title}}}\n"
        + ("\\RKBibIncludeUncitedtrue\n" if include_uncited else "\\RKBibIncludeUncitedfalse\n"),
        encoding="utf-8",
    )


def compile_with_bibliography(
    tmp_path: Path, *, documentclass: str, body: str, bib: str | None, style: str = "numeric",
    title: str = "References", include_uncited: bool = False, preamble: str = "", engine: str = "pdflatex",
) -> CompileResult:
    import pymupdf

    tex = tmp_path / "doc.tex"
    tex.write_text(f"{documentclass}\n{preamble}\n\\begin{{document}}\n{body}\n\\end{{document}}\n", encoding="utf-8")
    if bib is not None:
        (tmp_path / "references.bib").write_text(bib, encoding="utf-8")
        write_bibliography_config(tmp_path, stem="references", style=style, title=title, include_uncited=include_uncited)
    env = dict(
        os.environ, LC_ALL="C",
        TEXINPUTS=f"{tmp_path}:{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:",
    )
    command = [shutil.which(engine) or engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "doc.tex"]
    log_parts: list[str] = []

    def tex_pass() -> int:
        proc = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
        log_parts.append(proc.stdout)
        return proc.returncode

    passes = 1
    code = tex_pass()
    aux = tmp_path / "doc.aux"
    if code == 0 and bib is not None and aux.is_file() and "\\citation" in aux.read_text(encoding="utf-8", errors="replace"):
        bibtex = subprocess.run(["bibtex", "doc"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
        log_parts.append(bibtex.stdout)
        code = bibtex.returncode if bibtex.returncode > 1 else 0  # bibtex exits 1 on warnings
        for _ in range(2):
            if code == 0:
                code = tex_pass()
                passes += 1
    elif code == 0:
        code = tex_pass()
        passes += 1
    pdf = tmp_path / "doc.pdf"
    pages: list[str] = []
    if pdf.is_file():
        with pymupdf.open(pdf) as document:
            pages = [page.get_text() for page in document]
    return CompileResult(pdf=pdf, log="\n".join(log_parts), text="\n".join(pages), pages=pages, returncode=code, passes=passes)
```

- [ ] **Step 2: Write the failing TeX tests**

```python
# tests/test_bibliography_tex.py
"""Engine-wide bibliography and contents packages."""
from __future__ import annotations

from pathlib import Path
import re
import shutil

import pytest

from bibliography_helpers import compile_with_bibliography
from reportkit.primitive_targets import role_for
from reportkit.registry import generate_registry

pytestmark = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("bibtex") is None, reason="requires pdflatex and bibtex",
)

BIB = (
    "@book{smith2024, author={Smith, Ada}, title={Gauges and Rivers}, publisher={Delta Press}, year={2024}}\n"
    "@article{jones2019, author={Jones, Bo}, title={Tidal Survey Methods}, journal={Coastal Notes}, year={2019}, volume={4}, pages={1--9}}\n"
    "@misc{lee2020, author={Lee, Cy}, title={Uncited Field Notes}, year={2020}}\n"
)
BODY = (
    "\\usepackage{reportkit-longform}\n" "\\RKContents\n"
    "\\section{Findings}\nAs \\citet{smith2024} shows, gauges matter \\citep{jones2019}.\n"
    "\\RKBibliography\n"
)


def _body() -> tuple[str, str]:
    preamble, body = BODY.split("\n", 1)
    return preamble, body


def test_numeric_style_formats_labels_and_lists_only_cited(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB)
    assert result.returncode == 0, result.log[-4000:]
    assert result.passes == 3
    assert "Smith [1]" in result.text
    assert "[2]" in result.text
    assert "Gauges and Rivers" in result.text and "Tidal Survey Methods" in result.text
    assert "Uncited Field Notes" not in result.text
    assert "References" in result.text
    assert "Citation" not in result.log or "undefined" not in result.log


def test_author_year_style_formats_labels(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(
        tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB, style="author-year",
    )
    assert result.returncode == 0, result.log[-4000:]
    assert "Smith (2024)" in result.text
    assert "(Jones, 2019)" in result.text


def test_include_uncited_lists_every_entry(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(
        tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB, include_uncited=True,
    )
    assert result.returncode == 0, result.log[-4000:]
    assert "Uncited Field Notes" in result.text


def test_default_contents_page_lists_references_section(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB)
    assert result.returncode == 0, result.log[-4000:]
    contents_page = next(page for page in result.pages if page.lstrip().startswith("Contents"))
    assert "Findings" in contents_page and "References" in contents_page


def test_unconfigured_document_does_not_load_natbib(tmp_path: Path) -> None:
    preamble = "\\usepackage{reportkit-longform}"
    body = "\\RKContents\n\\section{Only}\nText.\n"
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=None)
    assert result.returncode == 0, result.log[-4000:]
    assert result.passes == 2
    assert "natbib.sty" not in (tmp_path / "doc.log").read_text(encoding="utf-8", errors="replace")


def test_manual_bookreferences_still_compile_without_configuration(tmp_path: Path) -> None:
    body = (
        "\\section{Body}\nSee \\cite{x}.\n"
        "\\begin{bookreferences}{9}\n\\bibitem{x} Example Author. A fictional source. 2026.\n\\end{bookreferences}\n"
    )
    result = compile_with_bibliography(
        tmp_path, documentclass="\\documentclass[publication-type=book]{reportkit}", body=body, bib=None,
    )
    assert result.returncode == 0, result.log[-4000:]
    assert "A fictional source" in result.text


def test_rkbibliography_without_configuration_is_a_coded_error(tmp_path: Path) -> None:
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", body="\\RKBibliography", bib=None)
    assert result.returncode != 0
    assert "RK_BIBLIOGRAPHY_UNCONFIGURED" in result.log


def test_contract_records_and_roles() -> None:
    registry = generate_registry()
    commands = registry["primitives"]["command"]
    assert "RKBibliography" in commands and "RKContents" in commands
    for publication_type in ("technical-report", "book", "feature-article", "executive-brief", "equity-research", "presentation"):
        assert role_for("RKBibliography", "command", publication_type) == "native"
        assert role_for("RKContents", "command", publication_type) == "native"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_bibliography_tex.py -v`
Expected: FAIL — `\RKBibliography` undefined / `test_contract_records_and_roles` KeyError.

- [ ] **Step 4: Create `reportkit-contents.sty`**

```tex
% ReportKit contents dispatcher (bibliography-and-contents spec §2.2).
% \RKContents is one authoring entry point; its layout is the selected
% publication type's \RKContentsSkin. Publication-type packages (loaded after
% this file) define \RKContentsSkin and \RKContentsTitle with \newcommand;
% reportkit-longform.sty provides the full contents page with
% \providecommand; anything still undefined at the end of the preamble gets
% the plain defaults below.
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{reportkit-contents}[2026/10/03 v1.0.0 ReportKit contents dispatcher]
\RequirePackage{xparse}
\RequirePackage{etoolbox}

% <reportkit-contract>
% {"kind":"command","description":"Contents in the publication type's own style: a contents page (technical report, book), an inline strip (feature article, executive brief), a page-numbered list (equity research), or an agenda slide (presentation). Call once.","arguments":[{"name":"title","type":"text","specifier":"O","description":"Optional heading; defaults to the publication type's contents title.","default":""}],"constraints":[{"code":"once_per_document","description":"Call at most once; it reads the contents file."}],"example":"\\RKContents","stability":"experimental","since":"1.11.0"}
% </reportkit-contract>
\NewDocumentCommand{\RKContents}{O{}}{%
  \ifstrempty{#1}{\RKContentsSkin{\RKContentsTitle}}{\RKContentsSkin{#1}}%
}

% Inline: "Title page  sep  Title page"; only section-level entries.
\newcommand{\rkcontents@inline}[1]{%
  \begingroup
  \def\rkcontents@sep{}%
  \def\numberline##1{}%
  \def\l@part##1##2{}%
  \def\l@section##1##2{\rkcontents@sep##1\nobreakspace##2\def\rkcontents@sep{#1}}%
  \def\l@subsection##1##2{}%
  \def\l@subsubsection##1##2{}%
  \@starttoc{toc}%
  \endgroup
}
% List: one line per section, page number flush right.
\newcommand{\rkcontents@list}{%
  \begingroup
  \def\numberline##1{}%
  \def\l@part##1##2{}%
  \def\l@section##1##2{\noindent##1\hfill##2\par}%
  \def\l@subsection##1##2{}%
  \def\l@subsubsection##1##2{}%
  \@starttoc{toc}%
  \endgroup
}

\AtEndPreamble{%
  \providecommand{\RKContentsTitle}{Contents}%
  \providecommand{\RKContentsSkin}[1]{%
    \section*{#1}\begingroup\renewcommand{\contentsname}{}\rkcontents@list\endgroup}%
}
\endinput
```

- [ ] **Step 5: Create `reportkit-bibliography.sty`**

```tex
% ReportKit BibTeX bibliography (bibliography-and-contents spec §2.1).
% Inert unless the build stages reportkit-bibliography-config.tex, so a
% document without a configured bibliography never loads natbib (natbib in
% author-year mode rejects the plain \bibitem entries of bookreferences).
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{reportkit-bibliography}[2026/10/03 v1.0.0 ReportKit BibTeX bibliography]
\RequirePackage{xparse}
\RequirePackage{etoolbox}

\newif\ifRKBibConfigured
\newif\ifRKBibIncludeUncited
\providecommand{\RKBibStyle}{numeric}
\providecommand{\RKBibFile}{}
\providecommand{\RKBibTitle}{References}
\IfFileExists{reportkit-bibliography-config.tex}{%
  \input{reportkit-bibliography-config.tex}\RKBibConfiguredtrue
}{}

\ifRKBibConfigured
  \ifdefstring{\RKBibStyle}{author-year}{%
    \RequirePackage[authoryear,round]{natbib}\def\rk@bib@bst{plainnat}%
  }{%
    \RequirePackage[numbers,sort&compress]{natbib}\def\rk@bib@bst{unsrtnat}%
  }
\fi

% Default render: natbib's \bibsection/\bibfont hooks around \bibliography.
\newcommand{\rk@bib@paged}[1]{%
  \begingroup
  \renewcommand{\bibsection}{\RKBibSkinBegin{#1}}%
  \renewcommand{\bibfont}{\RKBibSkinItemFont}%
  \bibliographystyle{\rk@bib@bst}%
  \bibliography{\RKBibFile}%
  \RKBibSkinEnd
  \endgroup
}

% <reportkit-contract>
% {"kind":"command","description":"Reference list generated by BibTeX from publication.yaml's bibliography.file, in the publication type's style. Cite with \\citep{key} (parenthetical) or \\citet{key} (textual); Markdown uses [@key] and @key.","arguments":[{"name":"title","type":"text","specifier":"O","description":"Optional heading; defaults to bibliography.title or the publication type's references title.","default":""}],"constraints":[{"code":"requires_bibliography_config","description":"publication.yaml must declare bibliography.file; otherwise RK_BIBLIOGRAPHY_UNCONFIGURED."},{"code":"no_invented_entries","description":"Cite only entries that exist in the .bib file."}],"example":"\\RKBibliography","stability":"experimental","since":"1.11.0"}
% </reportkit-contract>
\NewDocumentCommand{\RKBibliography}{O{}}{%
  \ifRKBibConfigured
    \ifRKBibIncludeUncited\nocite{*}\fi
    \ifstrempty{#1}{\RKBibRender{\RKBibTitle}}{\RKBibRender{#1}}%
  \else
    \PackageError{reportkit-bibliography}{RK_BIBLIOGRAPHY_UNCONFIGURED}{%
      Add a bibliography section with file: <name>.bib to publication.yaml.}%
  \fi
}

\AtEndPreamble{%
  \providecommand{\RKBibSkinBegin}[1]{%
    \section*{#1}\phantomsection\addcontentsline{toc}{section}{#1}}%
  \providecommand{\RKBibSkinEnd}{}%
  \providecommand{\RKBibSkinItemFont}{}%
  \providecommand{\RKBibRender}[1]{\rk@bib@paged{#1}}%
}
\endinput
```

Note: `\section*` under `reportkit-longform` already clears the page (its `\pretocmd{\section}`), which is the technical-report behaviour we want.

- [ ] **Step 6: Load both packages from the classes**

In `latex_templates/reportkit.cls`, immediately before the comment/`\RequirePackage` block that loads `\rk@pubtypepackage` (~line 93), add:

```tex
% Engine-wide contents dispatcher and (config-gated) BibTeX bibliography.
% Loaded before the publication-type package so its skins can define the
% hooks these packages default at the end of the preamble.
\RequirePackage{reportkit-contents}
\RequirePackage{reportkit-bibliography}
```

Add the same three lines at the matching position in `latex_templates/reportkit-slides.cls` (before the `\rk@pubtypepackage` block, ~line 63).

- [ ] **Step 7: Make the longform page the default contents skin**

Replace `latex_templates/reportkit-longform.sty` lines 29–33 (`\newcommand{\RKContents}{...}`) with:

```tex
% \RKContents (reportkit-contents.sty) dispatches here unless the
% publication type supplies its own skin. Unchanged long-form contents page.
\providecommand{\RKContentsSkin}[1]{%
  \clearpage\phantomsection\pdfbookmark[1]{#1}{reportkit-contents}%
  \thispagestyle{fancy}%
  \begingroup\renewcommand{\contentsname}{#1}\sffamily\tableofcontents\endgroup\clearpage
}
```

The title passed is `\RKContentsTitle` (default `Contents`), so the page is unchanged.

- [ ] **Step 8: Map roles**

In `python_scripts/reportkit/primitive_targets.py`, add a family (match the dict-of-families structure used by the existing `_family(...)` entries):

```python
    "references_and_contents": _family(
        members={"command": ("RKBibliography", "RKContents")},
        native=_PUBLICATION_TYPES,
    ),
```

- [ ] **Step 9: Run tests**

Run: `pytest tests/test_bibliography_tex.py tests/test_book.py tests/test_compact_contents.py tests/test_agent_contract.py tests/test_latex_publication_registry.py -v`
Expected: PASS. If natbib-after-hyperref produces a log warning or error, move the two `\RequirePackage` lines in `reportkit.cls` to *before* `\RequirePackage{reportkit-paged-core}` and re-run; record the choice in a comment.

- [ ] **Step 10: Regenerate contract docs and commit**

```bash
python -m reportkit docs --write
git add latex_templates/reportkit-bibliography.sty latex_templates/reportkit-contents.sty latex_templates/reportkit.cls latex_templates/reportkit-slides.cls latex_templates/reportkit-longform.sty python_scripts/reportkit/primitive_targets.py tests/bibliography_helpers.py tests/test_bibliography_tex.py references/
git commit -m "feat(tex): add config-gated BibTeX bibliography and contents dispatcher"
```

(If `python -m reportkit` is not the entry point, use the `reportkit` console script from the test venv.)

---

### Task 4: Build pipeline — stage, configure, bibtex pass, report

**Files:**
- Modify: `python_scripts/reportkit/bibliography.py` (writer and log helpers)
- Modify: `publication_pipeline/scripts/publication_build.py` (`_PreflightResult`, `_preflight`, `_stage_build_directory`, `_compile_tex_passes`, `build`)
- Modify: `schemas/reportkit-build-report.schema.json`
- Test: `publication_pipeline/tests/test_bibliography_build.py`

**Interfaces:**
- Consumes: `resolve_bibliography`, `bibliography_diagnostics`, `BibliographySettings` (Tasks 1–2); TeX config contract (Task 3).
- Produces:
  - `write_bibliography_config(path: Path, settings: BibliographySettings) -> None`
  - `aux_has_citations(aux_text: str) -> bool`
  - `blg_diagnostics(blg_text: str) -> list[dict]` (kind `bibliography_warning`)
  - `count_bbl_entries(bbl_text: str) -> int`
  - `_PreflightResult.bibliography: BibliographySettings | None`
  - build report key `bibliography`: `null` or `{"file", "style", "entries_cited", "bibtex_exit", "auto_placed", "diagnostics"}`

- [ ] **Step 1: Write the failing tests**

```python
# publication_pipeline/tests/test_bibliography_build.py
"""Bibliography staging, pass sequencing and build report."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import types

import pytest

from publication_pipeline.scripts import publication_build
from reportkit.bibliography import (
    BibliographySettings,
    aux_has_citations,
    blg_diagnostics,
    count_bbl_entries,
    write_bibliography_config,
)

REPO = Path(__file__).resolve().parents[2]


def _settings(tmp_path: Path, **overrides) -> BibliographySettings:
    values = dict(file="references.bib", path=tmp_path / "references.bib", stem="references",
                  style="numeric", title="Works & Sources", include_uncited=False)
    values.update(overrides)
    return BibliographySettings(**values)


def test_config_writer_escapes_title(tmp_path: Path) -> None:
    write_bibliography_config(tmp_path / "c.tex", _settings(tmp_path, include_uncited=True))
    text = (tmp_path / "c.tex").read_text(encoding="utf-8")
    assert "\\renewcommand{\\RKBibStyle}{numeric}" in text
    assert "\\renewcommand{\\RKBibFile}{references}" in text
    assert "\\renewcommand{\\RKBibTitle}{Works \\& Sources}" in text
    assert "\\RKBibIncludeUncitedtrue" in text


def test_log_helpers() -> None:
    assert aux_has_citations("\\relax\n\\citation{a}\n\\bibdata{references}\n")
    assert not aux_has_citations("\\relax\n\\bibdata{references}\n")
    blg = "Warning--empty journal in jones2019\nI couldn't open database file nope.bib\n(There were 2 warnings)\n"
    kinds = [(item["type"], item["severity"]) for item in blg_diagnostics(blg)]
    assert kinds == [("bibliography_warning", "warning"), ("bibliography_warning", "warning")]
    assert count_bbl_entries("\\bibitem[{A}(2024)]{a}\nx\n\\bibitem{b}\n") == 2


class _Recorder:
    """Fake run_limited: records commands and fakes TeX/bibtex outputs."""

    def __init__(self, output: Path, *, aux: str, bibtex_code: int = 0) -> None:
        self.output, self.aux, self.bibtex_code, self.commands = output, aux, bibtex_code, []

    def __call__(self, command, *, cwd, timeout, memory_limit_mb, **kwargs):
        self.commands.append(command[0])
        stream = kwargs.get("stdout")
        if command[0] == "bibtex":
            (self.output / "publication.bbl").write_text("\\bibitem{a}\n", encoding="utf-8")
            (self.output / "publication.blg").write_text("Warning--empty year in a\n", encoding="utf-8")
            if stream is not None:
                stream.write("bibtex\n")
            return types.SimpleNamespace(returncode=self.bibtex_code)
        (self.output / "publication.aux").write_text(self.aux, encoding="utf-8")
        if stream is not None:
            stream.write("tex pass\n")
        return types.SimpleNamespace(returncode=0)


def _run_passes(tmp_path: Path, monkeypatch, *, settings, aux: str, bibtex_code: int = 0):
    output = tmp_path / "out"
    output.mkdir()
    (output / "publication.tex").write_text("", encoding="utf-8")
    recorder = _Recorder(output, aux=aux, bibtex_code=bibtex_code)
    monkeypatch.setattr(publication_build, "run_limited", recorder)
    report = {"commands": [], "exit_codes": [], "bibliography": None if settings is None else {
        "file": settings.file, "style": settings.style, "entries_cited": 0, "bibtex_exit": None,
        "auto_placed": False, "diagnostics": []}}
    result = publication_build._compile_tex_passes(
        engine="pdflatex", tex=output / "publication.tex", log=output / "publication.log", output=output,
        texinputs="", timeout=10, memory_limit_mb=512, selection_marker="MARK", report=report,
        report_path=output / "build-report.json", history_root=tmp_path / "history", bibliography=settings,
    )
    return result, recorder.commands, report


def test_unconfigured_build_runs_exactly_two_tex_passes(tmp_path: Path, monkeypatch) -> None:
    result, commands, _ = _run_passes(tmp_path, monkeypatch, settings=None, aux="\\citation{a}\n")
    assert result is None
    assert commands == ["pdflatex", "pdflatex"]


def test_configured_build_with_citations_runs_bibtex_then_two_passes(tmp_path: Path, monkeypatch) -> None:
    result, commands, report = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\citation{a}\n")
    assert result is None
    assert commands == ["pdflatex", "bibtex", "pdflatex", "pdflatex"]
    assert report["bibliography"]["bibtex_exit"] == 0
    assert report["bibliography"]["entries_cited"] == 1
    assert report["bibliography"]["diagnostics"][0]["type"] == "bibliography_warning"
    assert "bibtex publication" in report["commands"]


def test_configured_build_without_citations_skips_bibtex(tmp_path: Path, monkeypatch) -> None:
    result, commands, report = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\bibdata{references}\n")
    assert result is None
    assert commands == ["pdflatex", "pdflatex"]
    assert report["bibliography"]["bibtex_exit"] is None


def test_bibtex_warnings_exit_one_is_not_a_failure(tmp_path: Path, monkeypatch) -> None:
    result, commands, _ = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\citation{a}\n", bibtex_code=1)
    assert result is None
    assert commands == ["pdflatex", "bibtex", "pdflatex", "pdflatex"]


def test_bibtex_error_fails_with_exit_four(tmp_path: Path, monkeypatch) -> None:
    result, commands, report = _run_passes(tmp_path, monkeypatch, settings=_settings(tmp_path), aux="\\citation{a}\n", bibtex_code=2)
    assert result == 4
    assert commands == ["pdflatex", "bibtex"]
    assert report["status"] == "failed"


def test_missing_bibtex_fails_with_exit_five(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "out"
    output.mkdir()
    calls = []

    def fake(command, **kwargs):
        calls.append(command[0])
        if command[0] == "bibtex":
            raise FileNotFoundError("bibtex")
        (output / "publication.aux").write_text("\\citation{a}\n", encoding="utf-8")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(publication_build, "run_limited", fake)
    report = {"commands": [], "exit_codes": [], "bibliography": {"bibtex_exit": None, "diagnostics": [], "entries_cited": 0}}
    result = publication_build._compile_tex_passes(
        engine="pdflatex", tex=output / "publication.tex", log=output / "publication.log", output=output,
        texinputs="", timeout=10, memory_limit_mb=512, selection_marker="MARK", report=report,
        report_path=output / "build-report.json", history_root=tmp_path / "history", bibliography=_settings(tmp_path),
    )
    assert result == 5
    assert report["diagnostics"]["diagnostics"][0]["code"] == "RK_BIBTEX_MISSING"


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("pdflatex", "bibtex", "pandoc")), reason="requires pdflatex, bibtex, pandoc",
)
def test_markdown_project_with_subdirectory_bib_builds_end_to_end(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    source = tmp_path / "project"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    (source / "refs").mkdir()
    (source / "refs" / "main.bib").write_text(
        "@book{smith2024, author={Smith, Ada}, title={Gauges and Rivers}, publisher={Delta Press}, year={2024}}\n",
        encoding="utf-8",
    )
    (source / "manuscript" / "order.txt").write_text("01-intro.md\n", encoding="utf-8")
    (source / "manuscript" / "01-intro.md").write_text("# Introduction\n\nGauges matter [@smith2024].\n", encoding="utf-8")
    (source / "publication.yaml").write_text(
        "publication:\n  title: Bibliography smoke\n  author: Test\n  version: v1\n"
        "document:\n  publication_type: technical-report\n  theme: default\n  source_mode: markdown\n"
        "bibliography:\n  file: refs/main.bib\n",
        encoding="utf-8",
    )
    output = tmp_path / "build"
    process = subprocess.run(
        [sys.executable, str(REPO / "publication_pipeline" / "scripts" / "publication_build.py"),
         "--mode", "combined", "--source-root", str(source), "--output-root", str(output), "--json"],
        capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-4000:] + process.stderr[-4000:]
    report = json.loads((output / "combined" / "build-report.json").read_text(encoding="utf-8"))
    assert report["bibliography"]["file"] == "refs/main.bib"
    assert report["bibliography"]["entries_cited"] == 1
    assert report["bibliography"]["auto_placed"] is True
    import pymupdf

    with pymupdf.open(output / "combined" / report["pdf"]) as document:
        text = "".join(page.get_text() for page in document)
    assert "[1]" in text and "Gauges and Rivers" in text and "References" in text
```

The end-to-end test also covers Task 5's `--natbib` and auto-placement. Expect it to keep failing until Task 5 is done; leave it in place.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest publication_pipeline/tests/test_bibliography_build.py -v`
Expected: FAIL — `ImportError: cannot import name 'aux_has_citations'`.

- [ ] **Step 3: Add the writer and log helpers to `bibliography.py`**

```python
from .latex import tex_escape

_BLG_WARNING = re.compile(r"^(?:Warning--.*|I couldn't open .*)$", re.MULTILINE)


def write_bibliography_config(path: Path, settings: BibliographySettings) -> None:
    path.write_text(
        "% Generated by publication_build.py; do not edit.\n"
        f"\\renewcommand{{\\RKBibStyle}}{{{settings.style}}}\n"
        f"\\renewcommand{{\\RKBibFile}}{{{settings.stem}}}\n"
        f"\\renewcommand{{\\RKBibTitle}}{{{tex_escape(settings.title)}}}\n"
        + ("\\RKBibIncludeUncitedtrue\n" if settings.include_uncited else "\\RKBibIncludeUncitedfalse\n"),
        encoding="utf-8",
    )


def aux_has_citations(aux_text: str) -> bool:
    return "\\citation{" in aux_text


def blg_diagnostics(blg_text: str) -> list[dict[str, Any]]:
    return [
        make_diagnostic("bibliography_warning", match.group(0).strip(), code="RK_BIBLIOGRAPHY_WARNING")
        for match in _BLG_WARNING.finditer(blg_text)
    ]


def count_bbl_entries(bbl_text: str) -> int:
    return len(re.findall(r"^\\bibitem\b", bbl_text, flags=re.MULTILINE))
```

Confirm `tex_escape` lives in `reportkit.latex` (`grep -n "def tex_escape" python_scripts/reportkit/*.py`); import it from wherever `publication_build.py` imports it.

- [ ] **Step 4: Resolve the bibliography in preflight**

In `publication_build.py`: add `bibliography: BibliographySettings | None = None` as the last field of `_PreflightResult`. In `_preflight`, after `document = resolve_document(config, profile)`, add:

```python
    bibliography_errors = [
        item for item in bibliography_diagnostics(source_root, config, profile, document)
        if item["severity"] == "error"
    ]
    for item in bibliography_errors:
        print(f"bibliography: [{item['code']}] {item['message']}", file=sys.stderr)
    if bibliography_errors:
        return 2 if any(item["type"] == "configuration_error" for item in bibliography_errors) else 3
    bibliography = resolve_bibliography(config, profile, str(document.get("publication_type") or "technical-report"), source_root)
```

and pass `bibliography=bibliography` into the `_PreflightResult(...)` constructor. Import `bibliography_diagnostics, resolve_bibliography, write_bibliography_config, aux_has_citations, blg_diagnostics, count_bbl_entries, CONFIG_FILENAME` from `reportkit.bibliography`.

- [ ] **Step 5: Stage the `.bib` and config**

At the end of `_stage_build_directory` (before `return staged_assets, cover_name`), add a `bibliography: BibliographySettings | None = None` keyword parameter and:

```python
    if bibliography is not None:
        destination = output / bibliography.file
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bibliography.path, destination)
        staged_assets.append({"path": bibliography.file, "sha256": sha256(bibliography.path)})
        write_bibliography_config(output / CONFIG_FILENAME, bibliography)
```

Pass `bibliography=preflight.bibliography` from `build()`.

- [ ] **Step 6: Rewrite `_compile_tex_passes` with an optional bibtex pass**

Add keyword parameter `bibliography: BibliographySettings | None = None`. Restructure the body:

```python
    env = dict(
        os.environ, TEXINPUTS=texinputs,
        openin_any="a" if engine == "lualatex" else "p", openout_any="p",
        LC_ALL="C", SOURCE_DATE_EPOCH="1", FORCE_SOURCE_DATE="1", TZ="UTC",
    )
    # (keep the existing explanatory comments for openin_any/LC_ALL above this dict)

    def tex_pass(pass_number: int, final: bool) -> int | None:
        command = [engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name]
        # ... existing body of one loop iteration, unchanged, using `env` ...
        # replace `if pass_number == 2:` with `if final:`
        return None  # or the _fail(...) exit code exactly as today

    failure = tex_pass(1, final=False)
    if failure is not None:
        return failure
    aux = output / tex.with_suffix(".aux").name
    aux_text = aux.read_text(encoding="utf-8", errors="replace") if aux.is_file() else ""
    if bibliography is not None and aux_has_citations(aux_text):
        command = ["bibtex", tex.stem]
        report["commands"].append(" ".join(command))
        bib_env = dict(env, BIBINPUTS=f"{output}:", BSTINPUTS="")
        bib_log = output / "publication-bibtex.log"
        with bib_log.open("w", encoding="utf-8") as stream:
            try:
                proc = run_limited(
                    command, cwd=output, timeout=timeout, memory_limit_mb=memory_limit_mb,
                    env=bib_env, stdout=stream, stderr=subprocess.STDOUT, text=True,
                )
            except subprocess.TimeoutExpired:
                return _fail(report, diagnostic_envelope([
                    make_diagnostic("compile_timeout", f"bibtex exceeded {timeout} seconds", code="RK_COMPILE_TIMEOUT")
                ], passed=False), 4, report_path=report_path, history_root=history_root)
            except FileNotFoundError:
                return _fail(report, diagnostic_envelope([
                    make_diagnostic("environment_error", "bibtex is not installed", code="RK_BIBTEX_MISSING")
                ], passed=False), 5, report_path=report_path, history_root=history_root)
        report["exit_codes"].append({"command": " ".join(command), "code": proc.returncode})
        blg = output / tex.with_suffix(".blg").name
        blg_text = blg.read_text(encoding="utf-8", errors="replace") if blg.is_file() else ""
        bbl = output / tex.with_suffix(".bbl").name
        record = report.setdefault("bibliography", {})
        record["bibtex_exit"] = proc.returncode
        record["diagnostics"] = blg_diagnostics(blg_text)
        record["entries_cited"] = count_bbl_entries(bbl.read_text(encoding="utf-8", errors="replace")) if bbl.is_file() else 0
        # bibtex exits 1 for warnings only, 2+ for errors.
        if proc.returncode > 1:
            return _fail(report, diagnostic_envelope([
                make_diagnostic("compile_failure", f"bibtex exited with status {proc.returncode}: {blg_text[-500:]}", code="RK_BIBTEX_FAILURE"),
                *record["diagnostics"],
            ], passed=False), 4, report_path=report_path, history_root=history_root)
        for item in record["diagnostics"]:
            print(f"bibliography warning: {item['message']}", file=sys.stderr)
        for pass_number, final in ((2, False), (3, True)):
            failure = tex_pass(pass_number, final=final)
            if failure is not None:
                return failure
        return None
    return tex_pass(2, final=True)
```

`BSTINPUTS=""` keeps the default TeX tree for `plainnat.bst`/`unsrtnat.bst` (an empty value means "default path" to kpathsea). Update the docstring to "Run the required TeX passes (two, or three with a bibtex pass when a configured bibliography is cited)".

- [ ] **Step 7: Record the bibliography in the report**

In `build()`, in the `report = {...}` dict add:

```python
        "bibliography": None if preflight.bibliography is None else {
            "file": preflight.bibliography.file, "style": preflight.bibliography.style,
            "entries_cited": 0, "bibtex_exit": None, "auto_placed": False, "diagnostics": [],
        },
```

and pass `bibliography=preflight.bibliography` to `_compile_tex_passes`.

In `schemas/reportkit-build-report.schema.json` add under `properties`:

```json
"bibliography": {
  "type": ["object", "null"],
  "properties": {
    "file": {"type": "string"},
    "style": {"enum": ["numeric", "author-year"]},
    "entries_cited": {"type": "integer", "minimum": 0},
    "bibtex_exit": {"type": ["integer", "null"]},
    "auto_placed": {"type": "boolean"},
    "diagnostics": {"type": "array"}
  },
  "required": ["file", "style", "entries_cited", "bibtex_exit", "auto_placed"]
}
```

- [ ] **Step 8: Run tests**

Run: `pytest publication_pipeline/tests/test_bibliography_build.py -v -k "not end_to_end" && pytest publication_pipeline/tests tests/test_reportkit_vnext.py -q`
Expected: unit tests PASS; the existing suites PASS (two-pass behaviour unchanged).

- [ ] **Step 9: Commit**

```bash
git add python_scripts/reportkit/bibliography.py publication_pipeline/scripts/publication_build.py schemas/reportkit-build-report.schema.json publication_pipeline/tests/test_bibliography_build.py
git commit -m "feat(build): stage .bib and run bibtex only when a configured bibliography is cited"
```

---

### Task 5: Markdown citations, directives and auto-placement

**Files:**
- Modify: `publication_pipeline/scripts/publication_build.py` (`render_markdown`, `_render_manuscript_bodies`)
- Modify: `python_scripts/reportkit/markdown_directives.py` (selector resolution in `_parse_body` / where `primitive` is set)
- Test: `publication_pipeline/tests/test_bibliography_build.py` (append), `tests/test_bibliography_model.py` (append)

**Interfaces:**
- Consumes: `markdown_citation_keys` (Task 1), `_PreflightResult.bibliography`, report `bibliography` dict (Task 4).
- Produces: `render_markdown(..., natbib: bool = False)`; directive aliases `references → RKBibliography`, `contents → RKContents`; `DIRECTIVE_ALIASES: dict[str, str]` in `markdown_directives.py`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bibliography_model.py`:

```python
from reportkit.markdown_directives import parse_markdown
from reportkit.tex_renderer import render_ir


def test_references_and_contents_directives_render_engine_commands() -> None:
    text = "```reportkit contents\n```\n\nBody.\n\n```reportkit references\ntitle: Works cited\n```\n"
    parsed = parse_markdown(text)
    assert [node.primitive for node in parsed.directives] == ["RKContents", "RKBibliography"]
    rendered = list(render_ir(parsed.ir, publication_type="technical-report", theme="default", renderer="paged").values())
    assert rendered[0].startswith("\\RKContents")
    assert rendered[1] == "\\RKBibliography[Works cited]"
```

Append to `publication_pipeline/tests/test_bibliography_build.py`:

```python
def test_pandoc_gets_natbib_only_when_requested(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "p"
    (root / "manuscript").mkdir(parents=True)
    manuscript = root / "manuscript" / "01.md"
    manuscript.write_text("Text [@a].\n", encoding="utf-8")
    seen: list[list[str]] = []

    def fake(command, **kwargs):
        seen.append(command)
        return types.SimpleNamespace(returncode=0, stdout="Text \\citep{a}.\n", stderr="")

    monkeypatch.setattr(publication_build, "run_limited", fake)
    publication_build.render_markdown(root, manuscript, tmp_path / "a.tex", natbib=True)
    publication_build.render_markdown(root, manuscript, tmp_path / "b.tex")
    assert "--natbib" in seen[0]
    assert "--natbib" not in seen[1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bibliography_model.py::test_references_and_contents_directives_render_engine_commands publication_pipeline/tests/test_bibliography_build.py::test_pandoc_gets_natbib_only_when_requested -v`
Expected: FAIL — unknown primitive `references` / unexpected keyword `natbib`.

- [ ] **Step 3: Add directive aliases**

In `markdown_directives.py` near the other module constants:

```python
# Friendly directive names for engine-wide commands (bibliography-and-contents spec §3).
DIRECTIVE_ALIASES: dict[str, str] = {"references": "RKBibliography", "contents": "RKContents"}
```

Wherever `_parse_body` (or `parse_markdown`) assigns the resolved selector to the node's `primitive`, map it through `DIRECTIVE_ALIASES.get(name, name)` before constructing the `DirectiveNode`. Find the line with `grep -n "primitive=" python_scripts/reportkit/markdown_directives.py`.

If the rendered output in the test is `\RKBibliography[]{}`-shaped rather than `\RKBibliography[Works cited]`, inspect `tex_renderer._render_arguments` for how `specifier: "O"` text arguments are bracketed and adjust the contract's argument (`"specifier":"O"`) rather than special-casing the renderer.

- [ ] **Step 4: Add `--natbib` to Pandoc**

In `render_markdown`, add the keyword parameter `natbib: bool = False` and change the Pandoc command list in `run_pandoc` to:

```python
                "pandoc", "-f", "markdown-raw_tex", "-t", writer,
                *(["--natbib"] if natbib else []),
                f"--lua-filter={TABLE_WIDTHS_FILTER}", *slide_level, str(input_path),
```

- [ ] **Step 5: Pass the flag and auto-place the list**

In `_render_manuscript_bodies`, add keyword parameters `bibliography: BibliographySettings | None = None` and `report_bibliography: dict | None = None`; pass `natbib=bibliography is not None` to `render_markdown`. After the loop, before `return body_files`:

```python
    if bibliography is not None:
        texts = [(source_root / "manuscript" / name).read_text(encoding="utf-8") for name in manuscripts]
        cites = any(markdown_citation_keys(text) for text in texts)
        placed = any(re.search(r"reportkit[\s:/]+(?:references|RKBibliography)\b", text) for text in texts)
        if cites and not placed:
            auto = output / "reportkit-auto-bibliography.tex"
            auto.write_text("\\RKBibliography\n", encoding="utf-8")
            body_files.append(auto)
            if report_bibliography is not None:
                report_bibliography["auto_placed"] = True
```

Because the report dict is built after the bodies today, compute `auto_placed` into a local first: have `_render_manuscript_bodies` return it (change its return type to `tuple[list[Path], bool] | int`) and set `report["bibliography"]["auto_placed"]` when the report is built. Update the single call site in `build()`.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_bibliography_model.py publication_pipeline/tests/test_bibliography_build.py publication_pipeline/tests -q`
Expected: PASS, including `test_markdown_project_with_subdirectory_bib_builds_end_to_end`.

- [ ] **Step 7: Commit**

```bash
git add python_scripts/reportkit/markdown_directives.py publication_pipeline/scripts/publication_build.py tests/test_bibliography_model.py publication_pipeline/tests/test_bibliography_build.py
git commit -m "feat(markdown): natbib citations, references/contents directives, auto-placed reference list"
```

---

### Task 6: Paged skins — book, feature-article, executive-brief, equity-research

**Files:**
- Modify: `latex_templates/publication_types/reportkit-book.sty`, `reportkit-feature-article.sty`, `reportkit-executive-brief.sty`, `reportkit-equity-research.sty` (append before `\endinput`)
- Test: `tests/test_bibliography_skins.py`

**Interfaces:**
- Consumes: hook names and helpers from Task 3; theme tokens already used by each package (`\rkbook@unnumbered`, `\RKTokBookReferenceFont`, `\RKTokBookReferenceColor`, `\RKTokFeatureReferenceTitleFont`, `\RKTokFeatureReferenceFont`, `\RKTokFeatureReferenceColor`, `\RKTokFeatureSectionColor`, `\RKTokFeatureSectionSkip`, `\RKTokFeatureElementSkip`, `\RKReserveSpace`, `\rksourcesize`, `\rksidebarsize`).
- Produces: per-type `\RKBibSkinBegin`, `\RKBibSkinItemFont`, `\RKContentsSkin`, `\RKContentsTitle` (book defines only bibliography hooks and the title; it keeps the longform contents page).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_bibliography_skins.py
"""Per-publication-type reference and contents skins."""
from __future__ import annotations

from pathlib import Path
import re
import shutil

import pytest

from bibliography_helpers import compile_with_bibliography
from reportkit.publications import PUBLICATION_TYPES

REPO = Path(__file__).resolve().parents[1]
PUBTYPES = REPO / "latex_templates" / "publication_types"
BIB = (
    "@book{smith2024, author={Smith, Ada}, title={Gauges and Rivers}, publisher={Delta Press}, year={2024}}\n"
    "@article{jones2019, author={Jones, Bo}, title={Tidal Survey Methods}, journal={Coastal Notes}, year={2019}}\n"
)
FONT = f"\\setreportkitfontpath{{{REPO / 'font_data'}/}}"
# (publication type, theme, engine, preamble, two section commands, numeric-or-author-year label)
CASES = {
    "book": ("default", "pdflatex", "\\usepackage{reportkit-longform}", "\\chapter", "Smith (2024)"),
    "feature-article": ("editorial", "lualatex", "\\usepackage{reportkit-longform}", "\\section", "Smith (2024)"),
    "executive-brief": ("executive", "lualatex", "\\usepackage{reportkit-longform}\\RKSectionOpensPagefalse", "\\section", "Smith [1]"),
    "equity-research": ("institutional-research", "lualatex", "\\usepackage{reportkit-longform}" + FONT, "\\section", "Smith (2024)"),
}


def _code(path: Path) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in path.read_text(encoding="utf-8").splitlines())


@pytest.mark.parametrize("name", ["reportkit-book.sty", "reportkit-feature-article.sty", "reportkit-executive-brief.sty", "reportkit-equity-research.sty", "reportkit-presentation.sty"])
def test_skins_use_tokens_not_literals(name: str) -> None:
    code = _code(PUBTYPES / name)
    skin = code[code.find("RKBibSkin") - 200:] if "RKBibSkin" in code else ""
    assert skin, f"{name} defines no bibliography skin"
    assert "\\fontsize" not in skin and "\\definecolor" not in skin


@pytest.mark.parametrize("publication_type", list(CASES))
def test_contents_titles_match_registry(publication_type: str) -> None:
    code = _code(PUBTYPES / f"reportkit-{publication_type}.sty")
    title = PUBLICATION_TYPES[publication_type]["contents_title"]
    assert f"\\newcommand{{\\RKContentsTitle}}{{{title}}}" in code


@pytest.mark.parametrize("publication_type", list(CASES))
def test_skin_compiles_with_title_contents_and_labels(tmp_path: Path, publication_type: str) -> None:
    theme, engine, preamble, sectioning, label = CASES[publication_type]
    if shutil.which(engine) is None or shutil.which("bibtex") is None:
        pytest.skip(f"requires {engine} and bibtex")
    style = PUBLICATION_TYPES[publication_type]["bibliography_style"]
    title = PUBLICATION_TYPES[publication_type]["bibliography_title"]
    body = (
        "\\RKContents\n"
        f"{sectioning}{{Findings}}\nAs \\citet{{smith2024}} shows \\citep{{jones2019}}.\n"
        f"{sectioning}{{Outlook}}\nMore text.\n"
        "\\RKBibliography\n"
    )
    result = compile_with_bibliography(
        tmp_path, documentclass=f"\\documentclass[theme={theme},publication-type={publication_type}]{{reportkit}}",
        preamble=preamble, body=body, bib=BIB, style=style, title=title, engine=engine,
    )
    assert result.returncode == 0, result.log[-6000:]
    assert label in result.text
    assert title in result.text
    assert "Gauges and Rivers" in result.text
    contents_title = PUBLICATION_TYPES[publication_type]["contents_title"]
    assert contents_title in result.text
    assert "Findings" in result.text.split(contents_title, 1)[1]
    assert "undefined" not in result.log.lower() or "citation" not in result.log.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bibliography_skins.py -v`
Expected: FAIL — no skin defined / contents title missing.

- [ ] **Step 3: Book skin** — append to `reportkit-book.sty` before `\endinput`:

```tex
% -----------------------------------------------------------------------------
% BibTeX reference list skin (bibliography-and-contents spec §2.3): the same
% unnumbered, contents-listed chapter opener and type as bookreferences. The
% contents page stays the long-form page.
% -----------------------------------------------------------------------------
\newcommand{\RKContentsTitle}{Contents}
\newcommand{\RKBibSkinBegin}[1]{\rkbook@unnumbered{#1}\let\@mkboth\@gobbletwo}
\newcommand{\RKBibSkinItemFont}{\RKTokBookReferenceFont\color{\RKTokBookReferenceColor}}
```

- [ ] **Step 4: Feature-article skin** — append to `reportkit-feature-article.sty` before `\endinput`:

```tex
% -----------------------------------------------------------------------------
% BibTeX references and "In this issue" contents (bibliography-and-contents
% spec §2.3). References share featurereferences' heading and type; contents
% is an inline strip that never breaks the page.
% -----------------------------------------------------------------------------
\newcommand{\RKContentsTitle}{In this issue}
\newcommand{\RKContentsSkin}[1]{%
  \par\vspace{\RKTokFeatureElementSkip}%
  {\RKTokFeatureReferenceTitleFont\color{\RKTokFeatureSectionColor}#1\par}%
  \vspace{\RKTokFeatureElementSkip}%
  {\RKTokFeatureReferenceFont\color{\RKTokFeatureReferenceColor}\rkcontents@inline{\quad\textbullet\quad}\par}%
  \vspace{\RKTokFeatureSectionSkip}%
}
\newcommand{\RKBibSkinBegin}[1]{%
  \par\RKReserveSpace{6\baselineskip}%
  \vspace{\RKTokFeatureSectionSkip}%
  \phantomsection\addcontentsline{toc}{section}{#1}%
  {\RKTokFeatureReferenceTitleFont\color{\RKTokFeatureSectionColor}#1\par}%
  \vspace{\RKTokFeatureElementSkip}%
}
\newcommand{\RKBibSkinItemFont}{\RKTokFeatureReferenceFont\color{\RKTokFeatureReferenceColor}}
```

- [ ] **Step 5: Executive-brief skin** — append to `reportkit-executive-brief.sty` before `\endinput`:

```tex
% -----------------------------------------------------------------------------
% BibTeX sources and compact contents (bibliography-and-contents spec §2.3).
% Contents appear only where the author calls \RKContents.
% -----------------------------------------------------------------------------
\newcommand{\RKContentsTitle}{Contents}
\newcommand{\RKContentsSkin}[1]{%
  \par{\sffamily\rksourcesize\color{Muted}\textbf{#1}\quad\rkcontents@inline{\quad\textbullet\quad}\par}%
}
\newcommand{\RKBibSkinBegin}[1]{%
  \par\RKReserveSpace{3\baselineskip}%
  {\sffamily\bfseries\rksourcesize\color{Ink}#1\par}\setlength{\bibsep}{2pt}%
}
\newcommand{\RKBibSkinItemFont}{\sffamily\rksourcesize\color{Muted}}
```

- [ ] **Step 6: Equity-research skin** — append to `reportkit-equity-research.sty` before `\endinput`:

```tex
% -----------------------------------------------------------------------------
% BibTeX sources and "In this report" contents (bibliography-and-contents spec
% §2.3). The contents list fits the sidebar; sources precede disclosures.
% -----------------------------------------------------------------------------
\newcommand{\RKContentsTitle}{In this report}
\newcommand{\RKContentsSkin}[1]{%
  \par{\sffamily\bfseries\rksidebarsize\color{Ink}#1\par}\vspace{2pt}%
  {\sffamily\rksidebarsize\color{Muted}\rkcontents@list}%
}
\newcommand{\RKBibSkinBegin}[1]{%
  \section*{#1}\phantomsection\addcontentsline{toc}{section}{#1}%
}
\newcommand{\RKBibSkinItemFont}{\sffamily\rksourcesize\color{Ink}}
```

- [ ] **Step 7: Technical-report contents title** — no file change is needed (defaults apply); confirm `test_contents_titles_match_registry` is not parametrized over `technical-report`.

- [ ] **Step 8: Run tests**

Run: `pytest tests/test_bibliography_skins.py tests/test_book.py tests/test_executive_brief.py tests/test_editorial_theme.py tests/test_institutional_equity_theme_compile.py tests/test_theme_contract.py tests/test_publication_theme_coverage.py -v`
Expected: PASS. If an engine fails on fonts, copy the preamble used by the matching existing test (`tests/test_executive_brief.py`, `tests/test_editorial_theme.py`) into that `CASES` entry; do not change the skin.

- [ ] **Step 9: Commit**

```bash
git add latex_templates/publication_types/ tests/test_bibliography_skins.py
git commit -m "feat(skins): book, feature, brief and equity reference and contents skins"
```

---

### Task 7: Presentation — paginated references and `agendaslide`

**Files:**
- Modify: `latex_templates/publication_types/reportkit-presentation.sty` (after `\referenceitem`)
- Modify: `python_scripts/reportkit/primitive_targets.py` (add `agendaslide` to the presentation compositions family that lists `referenceslide`, ~line 219)
- Test: `tests/test_bibliography_skins.py` (append)

**Interfaces:**
- Consumes: `\rk@bib@bst`, `\RKBibFile`, `\RKContentsTitle` (Task 3); counter `rkpresentation@references`; tokens `\RKTokPresentationSurface`, `\RKTokPresentationAssertionFont`, `\RKTokPresentationSourceFont`, `\RKTokPresentationBodyFont`.
- Produces: `\RKBibRender{title}` (frames), `\RKContentsSkin{title}` (agenda frame), composition `agendaslide[title]`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_bibliography_skins.py`:

```python
TEN = "".join(
    f"@misc{{ref{i:02d}, author={{Author{i:02d}, A.}}, title={{Entry number {i:02d}}}, year={{2020}}}}\n" for i in range(1, 11)
)
DECK = (
    "\\begin{frame}[plain]\\begin{titleslide}\\end{titleslide}\\end{frame}\n"
    "\\RKContents\n"
    "\\begin{frame}[plain]\\begin{sectiondivider}{Market}\\end{sectiondivider}\\end{frame}\n"
    "\\begin{frame}\\begin{messageslide}{Demand is rising}Per \\citet{ref01}.\\end{messageslide}\\end{frame}\n"
    "\\begin{frame}[plain]\\begin{sectiondivider}{Plan}\\end{sectiondivider}\\end{frame}\n"
    "\\RKBibliography\n"
)


@pytest.mark.skipif(shutil.which("lualatex") is None or shutil.which("bibtex") is None, reason="requires lualatex and bibtex")
def test_presentation_references_paginate_at_eight_and_agenda_lists_sections(tmp_path: Path) -> None:
    result = compile_with_bibliography(
        tmp_path,
        documentclass="\\documentclass[theme=executive,publication-type=presentation]{reportkit-slides}",
        preamble="\\title{Deck}", body=DECK, bib=TEN, include_uncited=True, engine="lualatex",
    )
    assert result.returncode == 0, result.log[-6000:]
    agenda = next(page for page in result.pages if "Agenda" in page)
    assert "Market" in agenda and "Plan" in agenda
    reference_pages = [page for page in result.pages if "Entry number" in page]
    assert len(reference_pages) == 2
    assert "Entry number 08" in reference_pages[0] and "Entry number 09" not in reference_pages[0]
    assert "Entry number 09" in reference_pages[1] and "Entry number 10" in reference_pages[1]
    assert "(cont.)" in reference_pages[1]


def test_agendaslide_contract_and_role() -> None:
    from reportkit.primitive_targets import role_for
    from reportkit.registry import generate_registry

    assert "agendaslide" in generate_registry()["primitives"]["composition"]
    assert role_for("agendaslide", "composition", "presentation") == "native"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bibliography_skins.py -v -k "presentation or agendaslide"`
Expected: FAIL.

- [ ] **Step 3: Implement the presentation skin** — append after `\referenceitem` in `reportkit-presentation.sty`:

```tex
% -----------------------------------------------------------------------------
% Agenda and BibTeX references (bibliography-and-contents spec §2.3).
% \RKBibliography is used outside any frame: it opens an allowframebreaks
% frame and forces a break after every eighth entry, so a long list never
% shrinks below the theme's source size. \RKContents emits an agenda frame
% listing the sections sectiondivider registers.
% -----------------------------------------------------------------------------
\newcommand{\RKContentsTitle}{Agenda}

% <reportkit-contract>
% {"kind":"composition","description":"Agenda slide listing the deck's sections (registered by sectiondivider) in order.","arguments":[{"name":"title","type":"text","specifier":"O","description":"Heading; defaults to Agenda.","default":""}],"constraints":[{"code":"content_only_wrap_in_frame","description":"Content only; wrap in \\begin{frame}...\\end{frame}."}],"example":"\\begin{frame}\n\\begin{agendaslide}\n\\end{agendaslide}\n\\end{frame}","stability":"experimental","since":"1.11.0"}
% </reportkit-contract>
\NewDocumentEnvironment{agendaslide}{O{}}{%
  \RKTokPresentationSurface{content}%
  {\sffamily\bfseries\RKTokPresentationAssertionFont\color{Ink}\ifstrempty{#1}{\RKContentsTitle}{#1}\par}%
  \vspace{3mm}%
  {\sffamily\RKTokPresentationBodyFont\color{Ink}%
   \setbeamertemplate{section in toc}{\inserttocsection\par}%
   \tableofcontents[hideallsubsections]}%
}{}

\newcommand{\RKContentsSkin}[1]{%
  \begin{frame}\begin{agendaslide}[#1]\end{agendaslide}\end{frame}%
}

\newcounter{rkpresentation@bibitems}
\newcommand{\RKBibRender}[1]{%
  \begingroup
  \setbeamertemplate{frametitle}{%
    {\sffamily\bfseries\RKTokPresentationAssertionFont\color{Ink}\insertframetitle\par}\vspace{3mm}}%
  \setbeamertemplate{frametitle continuation}{(cont.)}%
  \renewcommand{\bibsection}{}%
  \renewcommand{\bibfont}{\sffamily\RKTokPresentationSourceFont\color{Ink}}%
  \setcounter{rkpresentation@bibitems}{0}%
  \let\rkpresentation@natbibitem\bibitem
  \def\bibitem{%
    \ifnum\value{rkpresentation@bibitems}=8
      \setcounter{rkpresentation@bibitems}{0}\framebreak
    \fi
    \stepcounter{rkpresentation@bibitems}\rkpresentation@natbibitem}%
  \begin{frame}[allowframebreaks]{#1}%
    \RKTokPresentationSurface{content}%
    \bibliographystyle{\rk@bib@bst}%
    \bibliography{\RKBibFile}%
  \end{frame}%
  \endgroup
}
```

If `\framebreak` inside natbib's list misbehaves (entries 9–10 on the same page as 1–8, or a TeX error), replace the `\framebreak` approach with closing and reopening the list: set `\bibsep` and rely on `allowframebreaks` height splitting, *and* change the test's per-page assertion to "no page has more than eight entries". Record the outcome in the commit message.

- [ ] **Step 4: Map the role** — in `primitive_targets.py`, add `"agendaslide"` to the presentation composition members tuple that contains `"referenceslide"` (~line 219) and to the presentation native list that contains `"referenceslide"` (~line 298).

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_bibliography_skins.py tests/test_presentation_compositions.py tests/test_presentation_authoring.py tests/test_slide_renderer.py tests/test_slide_accessibility.py -v`
Expected: PASS.

- [ ] **Step 6: Regenerate docs and commit**

```bash
python -m reportkit docs --write
git add latex_templates/publication_types/reportkit-presentation.sty python_scripts/reportkit/primitive_targets.py tests/test_bibliography_skins.py references/
git commit -m "feat(presentation): agenda slide and BibTeX references paginated at eight per frame"
```

---

### Task 8: Doctor, documentation, skill and status

**Files:**
- Modify: `python_scripts/reportkit_doctor.py` (~line 170 `full_ok`; ~210 NOTE)
- Create: `references/bibliography-and-contents.md`
- Modify: `SKILL.md`, `references/technical-report*`/`visual-grammar.md` (whichever is the technical guide linked from SKILL.md), `references/book-authoring.md`, `references/feature-article-authoring.md`, `references/executive-brief-authoring.md`, `references/institutional-research-theme.md`, `references/presentation-authoring.md`
- Modify: `docs/superpowers/specs/2026-10-03-reportkit-bibliography-and-contents-spec.md` (status + plan-time amendments), `TODOS.md`
- Test: existing doctor tests (`grep -rln reportkit_doctor tests`)

- [ ] **Step 1: Write the failing doctor test** — in the existing doctor test module found by `grep -rln "reportkit_doctor" tests publication_pipeline/tests` (create `tests/test_doctor_bibtex.py` if none), add:

```python
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]


def test_full_build_requires_bibtex(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    # Expose every real tool except bibtex by shadowing it with a failing stub.
    stub = fake_bin / "bibtex"
    stub.write_text("#!/bin/sh\nexit 127\n", encoding="utf-8")
    stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")
    proc = subprocess.run(
        [sys.executable, str(REPO / "python_scripts" / "reportkit_doctor.py"), "--json"],
        capture_output=True, text=True, env=env,
    )
    checks = {item["name"]: item["available"] for item in json.loads(proc.stdout)["checks"]}
    assert checks["bibtex"] is False
    assert json.loads(proc.stdout)["mode"] != "FULL BUILD"
```

Before writing it, read `check_executable` in `reportkit_doctor.py`; if it only checks `shutil.which`, a stub on PATH counts as present — in that case make the stub absent instead by constructing a PATH that excludes the directory containing the real `bibtex` (`Path(shutil.which("bibtex")).parent`) and skip the test if that directory also holds `pdflatex`.

- [ ] **Step 2: Run to verify it fails**, then change `reportkit_doctor.py`:

```python
    full_ok = py_ok and viz_ok and tex_ok and fonts_ok and algorithms_ok and pandoc_ok and pymupdf_ok and bibtex_ok
```

and replace the NOTE block with:

```python
        if biber_ok and not bibtex_ok:
            print("NOTE: biber is installed but ReportKit bibliographies use bibtex.")
```

Add a branch where `full_ok` is false only because of bibtex, printing `"bibtex is missing: run scripts/setup_tex.sh or use the pinned container."`.

Run: `pytest tests/test_doctor_bibtex.py tests/test_reportkit_vnext.py -q` → PASS.

- [ ] **Step 3: Write `references/bibliography-and-contents.md`** with these sections, each concrete:
  1. *When to use* — any publication citing external sources; never invent entries.
  2. *Configure* — the YAML block from spec §1 and the per-type default table.
  3. *Cite* — TeX `\citep{key}`, `\citet{key}`, `\citep[p.~3]{key}`, `\citealp{key}`; Markdown `[@key]`, `@key`, `[@a; @b, p. 3]`, `[-@key]`.
  4. *Place the list* — `\RKBibliography[title]`; Markdown `` ```reportkit references `` or automatic at the end.
  5. *Contents* — `\RKContents[title]` / `` ```reportkit contents ``; table of what each type renders.
  6. *Presentations* — `\RKBibliography` outside frames, eight per frame; `agendaslide`.
  7. *Diagnostics* — the §5 table and the build codes.
  8. *Manual fallback* — the existing environments, for sources with no `.bib`.

- [ ] **Step 4: Update `SKILL.md`** — in “Write for the decision”, replace the last sentence of the callouts bullet with: “Put sources in the project's `.bib` file, cite them with `\citep`/`\citet` or `[@key]`, and place `\RKBibliography`; never invent a bibliography entry.” Add a References-table row: `| Citations, references, contents | [Bibliography and contents](references/bibliography-and-contents.md) |`.

- [ ] **Step 5: Per-type guides** — add a `## References and contents` subsection to each of the six guides naming the type's default style, references title, contents skin, and the manual environment as fallback (two to four sentences each, values from Global Constraints).

- [ ] **Step 6: Spec and status** — in the spec, change the status line to `**Status:** Implemented on \`feat/bibliography-and-contents\` · visual review pending · <date>` and add a `## Plan-time amendments` section copying the five amendments from this plan's Global Constraints. In `TODOS.md`, add both this spec and plan to the Outstanding documents table (P2, "Implemented on branch; human visual review of the six skins remains") and an Open-work bullet for the visual review.

- [ ] **Step 7: Check docs and commit**

Run: `python -m reportkit docs --check` (or the repository's docs drift test: `pytest tests/test_agent_contract.py tests/test_repository_hygiene.py -q`). Expected: PASS.

```bash
git add python_scripts/reportkit_doctor.py tests/ references/ SKILL.md TODOS.md docs/superpowers/specs/2026-10-03-reportkit-bibliography-and-contents-spec.md
git commit -m "docs: bibliography and contents guide, skill, per-type guides, doctor bibtex check"
```

---

### Task 9: Full verification

**Files:** none (verification only; fix forward in the owning task's files if anything fails).

- [ ] **Step 1: Full test and lint run**

Run: `pytest -q` and `ruff check .` (use the repo's test venv at `build/.venv-tests` if the system Python lacks dependencies).
Expected: all pass, except pre-existing strict xfails listed in `TODOS.md` (operator theme). Compare the failure list with `git stash; pytest -q; git stash pop` on `main` if anything unexpected appears.

- [ ] **Step 2: Regression on existing baselines**

Run the existing visual QA scripts that have checked-in baselines and do not require the pinned OCI toolchain to compare (e.g. `python scripts/visual_qa_equity_research.py --help` to find the compare mode). Where only the pinned container can compare, record that the comparison is pending; do not regenerate baselines.

- [ ] **Step 3: Consumer-project smoke through the CLI** (per AGENTS.md: projects outside the engine checkout)

```bash
mkdir -p /tmp/claude-1000/rk-bib-smoke && cd /tmp/claude-1000/rk-bib-smoke
reportkit init demo --publication-type technical-report --theme default --source-mode markdown
# add references.bib with two entries, bibliography: {file: references.bib} to publication.yaml,
# a manuscript paragraph citing [@key], and ```reportkit contents``` at the top
reportkit doctor --require full-build --json
reportkit check --source-root demo --json
reportkit build --source-root demo --json
reportkit render --source-root demo --pages 1-3 --json
```

Expected: check passes; build passes; `build-report.json` `bibliography.entries_cited == 2`; rendered pages show the contents strip/page and the reference list. Repeat the check with a misspelled key and confirm `RK_CITATION_UNDEFINED`.

- [ ] **Step 4: Visual review**

View the rendered PNGs for each of the six skin fixtures produced by `tests/test_bibliography_skins.py` (re-run with `--basetemp=/tmp/claude-1000/rk-skins` to keep the PDFs and render them with `publication_pipeline/scripts/render_pdf_pages.py`). Record in the final report which pages were viewed. If page images cannot be viewed, state that visual review is unavailable — never claim it was done.

- [ ] **Step 5: Finish the branch** — use superpowers:finishing-a-development-branch (PR via `gh`).
