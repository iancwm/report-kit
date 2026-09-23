"""Agent contract: language and script truthfulness (D-prime 3).

Agent-interface spec section 13: every Theme declares script coverage and
per-script font stacks; locale typography loads only for verified
languages; missing glyphs are fatal under ``font_policy: strict``; context
exposes renderer/theme language compatibility; RTL stays explicitly
unsupported; Vietnamese stays metadata-only.

The static tests need no toolchain. The compile tests run the real engines
and skip where they are absent.
"""
from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from reportkit.context import build_context
from reportkit.context_budget import ALWAYS_LOADED_TOKEN_CEILING, build_context_slice
from reportkit.diagnostics import inspect_log
from reportkit.languages import (
    LOCALE_TYPOGRAPHY,
    RTL_LANGUAGES,
    language_diagnostics,
    normalize_language_tag,
    resolve_language,
    validate_script_coverage,
)
from reportkit.publications import (
    RENDERERS,
    THEMES,
    canonical_theme_name,
    check_publication_registry,
    render_latex_registry,
    resolve_build_target,
)
from reportkit.themes import ScriptCoverageTokens, ScriptFontStack, get_theme, validate_theme_contract

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
CANONICAL_THEMES = sorted({canonical_theme_name(name) for name in THEMES})
NEW_THEME_INSTRUCTION = (
    "declare script_coverage=ScriptCoverageTokens(verified=('Latn',), metadata_only=(), rtl='unsupported', "
    "font_stacks={'Latn': ScriptFontStack(body=(...), heading=(...), mono=(...))}, "
    "verified_languages=('en',), metadata_only_languages=('vi',)) in the theme's Python module, "
    "listing the font families its .sty actually selects"
)


# ---------------------------------------------------------------------------
# Theme declarations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("theme_name", CANONICAL_THEMES)
def test_every_theme_declares_script_coverage_and_font_stacks(theme_name: str) -> None:
    theme = get_theme(theme_name)
    errors = validate_script_coverage(theme)
    assert errors == [], f"theme {theme_name!r}: {errors}; {NEW_THEME_INSTRUCTION}"
    coverage = theme.script_coverage
    for script in coverage.verified:
        assert isinstance(coverage.font_stacks[script], ScriptFontStack), NEW_THEME_INSTRUCTION


def test_script_coverage_fields_are_required_so_new_themes_must_declare_them() -> None:
    required = {field.name for field in dataclasses.fields(ScriptCoverageTokens)
                if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING}
    assert required == {
        "verified", "metadata_only", "rtl", "font_stacks", "verified_languages", "metadata_only_languages",
    }, NEW_THEME_INSTRUCTION
    with pytest.raises(TypeError, match="font_stacks"):
        ScriptCoverageTokens(verified=("Latn",), metadata_only=(), rtl="unsupported")  # type: ignore[call-arg]


@pytest.mark.parametrize("theme_name", CANONICAL_THEMES)
def test_font_stacks_name_fonts_the_theme_package_actually_selects(theme_name: str) -> None:
    """A stack is only truthful if the theme's LaTeX package can select it."""
    package = TEMPLATES / "themes" / f"{THEMES[theme_name]['common_package']}.sty"
    text = package.read_text(encoding="utf-8")
    # Families supplied by a package rather than named literally.
    provided_by = {
        "Libertinus Serif": r"\RequirePackage{libertinus}",
        "Libertinus Sans": r"\RequirePackage{libertinus}",
        "Libertinus Mono": r"\RequirePackage{libertinus}",
        "Latin Modern Mono": r"\RequirePackage{fontspec}",
    }
    for script, stack in get_theme(theme_name).script_coverage.font_stacks.items():
        for role in ("body", "heading", "mono"):
            for family in getattr(stack, role):
                marker = provided_by.get(family, family)
                assert marker in text, (
                    f"{package.name} does not select {family!r} declared in font_stacks[{script!r}].{role}"
                )


@pytest.mark.parametrize("theme_name", CANONICAL_THEMES)
def test_rtl_is_explicitly_unsupported_and_vietnamese_stays_metadata_only(theme_name: str) -> None:
    coverage = get_theme(theme_name).script_coverage
    assert coverage.rtl == "unsupported"
    assert "vi" in coverage.metadata_only_languages, (
        "Vietnamese stays metadata-only until a real typography fixture proves its locale typography"
    )
    assert "vi" not in coverage.verified_languages
    assert not set(coverage.verified_languages) & RTL_LANGUAGES


def test_validator_names_the_missing_declaration() -> None:
    theme = get_theme("default")
    broken = dataclasses.replace(theme, script_coverage=dataclasses.replace(
        theme.script_coverage, font_stacks={}, rtl="partial",
        verified=("Latn", "Arab"), verified_languages=("en", "ar", "de"),
    ))
    errors = validate_theme_contract(broken)
    joined = "\n".join(errors)
    assert "font_stacks must declare a ScriptFontStack" in joined
    assert "script_coverage.rtl must be 'unsupported'" in joined
    assert "right-to-left scripts ['Arab']" in joined
    assert "right-to-left languages ['ar']" in joined
    assert "LOCALE_TYPOGRAPHY has no locale typography for it" in joined  # 'de'


def test_registry_reports_a_theme_without_language_declarations(monkeypatch: pytest.MonkeyPatch) -> None:
    record = dict(THEMES["default"])
    record["language_support"] = {"error": "theme 'default' must register ... ScriptCoverageTokens(...)"}
    monkeypatch.setitem(THEMES, "default", record)
    errors = check_publication_registry(REPO)
    assert any("ScriptCoverageTokens" in error for error in errors)


def test_latex_registry_carries_language_tables() -> None:
    text = render_latex_registry()
    assert r"\expandafter\def\csname RKRTLLanguage@ar\endcsname{1}" in text
    assert r"\expandafter\def\csname RKLocaleBabel@en\endcsname{american}" in text
    for theme in THEMES:
        assert rf"\expandafter\def\csname RKThemeLanguage@{theme}@en\endcsname{{verified}}" in text
        assert rf"\expandafter\def\csname RKThemeLanguage@{theme}@vi\endcsname{{metadata-only}}" in text
    assert text == (TEMPLATES / "reportkit-publication-registry.def").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Language resolution and diagnostics
# ---------------------------------------------------------------------------


def test_language_tags_normalize_and_resolve_to_verified_locale_typography() -> None:
    assert normalize_language_tag("en_gb") == "en-GB"
    assert normalize_language_tag("zh-hant-tw") == "zh-Hant-TW"
    with pytest.raises(ValueError):
        normalize_language_tag("not a tag")
    assert resolve_language("en-US", "default").locale_typography == "american"
    # No separate UK patterns exist in the pinned format; en-GB truthfully
    # resolves to the primary subtag's locale.
    assert "en-GB" not in LOCALE_TYPOGRAPHY
    assert resolve_language("en-GB", "executive").locale_typography == "american"
    vi = resolve_language("vi", "institutional-research")
    assert (vi.status, vi.locale_typography) == ("metadata_only", None)
    assert resolve_language("he", "default").status == "rtl_unsupported"
    assert resolve_language("de", "technical").status == "undeclared"


def test_language_diagnostics_match_policy() -> None:
    assert language_diagnostics(None, "default") == []
    assert language_diagnostics("en-GB", "default") == []

    [metadata] = language_diagnostics("vi", "default")
    assert (metadata["code"], metadata["severity"]) == ("RK_LANGUAGE_METADATA_ONLY", "warning")

    for policy in ("fallback", "strict"):
        [rtl] = language_diagnostics("ar-EG", "default", font_policy=policy)
        assert (rtl["code"], rtl["severity"]) == ("RK_LANGUAGE_RTL_UNSUPPORTED", "error")

    [undeclared] = language_diagnostics("de", "default", font_policy="fallback")
    assert (undeclared["code"], undeclared["severity"]) == ("RK_LANGUAGE_UNDECLARED", "warning")
    [refused] = language_diagnostics("de", "default", font_policy="strict")
    assert (refused["code"], refused["severity"]) == ("RK_LANGUAGE_UNSUPPORTED", "error")
    assert set(refused["candidates"]) == {"en", "vi"}

    [invalid] = language_diagnostics("english please", "default")
    assert invalid["code"] == "RK_LANGUAGE_TAG_INVALID"


def test_log_gate_classifies_both_engines_missing_glyph_reports_as_blocking() -> None:
    lualatex = "Missing character: There is no \u4e2d (U+4E2D) in font [LibertinusSerif-Regular.otf\n"
    pdflatex = "! LaTeX Error: Unicode character \u1ec0 (U+1EC0)\n               not set up for use with LaTeX.\n"
    for text in (lualatex, pdflatex):
        result = inspect_log(text)
        kinds = [item["type"] for item in result["diagnostics"]]
        assert kinds[0] == "missing_glyph"
        assert result["diagnostics"][0]["blocking"] is True
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# Context exposure
# ---------------------------------------------------------------------------


def test_context_exposes_renderer_and_theme_language_compatibility() -> None:
    context = build_context(REPO, publication_type="presentation")
    capabilities = context["capabilities"]
    for name, renderer in capabilities["renderers"].items():
        support = renderer["language_support"]
        assert support["rtl"] == "unsupported", name
        assert support["text_direction"] == ["ltr"], name
        assert support["locale_typography"]["loaded_for"] == "verified-languages-only"
        assert set(support["missing_glyph"]) == {"strict", "fallback"}
    for name, theme in capabilities["themes"].items():
        support = theme["language_support"]
        assert support["scripts"]["font_stacks"]["Latn"]["body"], name
        assert support["locale_typography"] == {"en": "american", "en-US": "american"}
    selection = context["selection"]["language_support"]
    assert selection["text_direction"] == ["ltr"]
    assert selection["scripts"]["font_stacks"]["Latn"]["body"] == ["Libertinus Sans"]
    assert selection == resolve_build_target("presentation", "executive").as_dict()["language_support"]


def test_language_support_lives_in_the_selection_slice_not_a_bloated_quickstart() -> None:
    context = build_context(REPO)
    selection = build_context_slice(context, "selection")["content"]
    assert "font_stacks" in selection["selection"]["language_support"]["scripts"]
    assert all("language_support" in record for record in selection["themes"].values())
    assert all("language_support" in record for record in selection["renderers"].values())
    quickstart = build_context_slice(context, "quickstart")
    text = quickstart["content"]["text"]
    assert "RTL is unsupported" in text and "metadata-only vi" in text
    assert "font_stacks" not in json.dumps(quickstart["content"])
    assert quickstart["estimated_tokens"] <= ALWAYS_LOADED_TOKEN_CEILING


def test_renderer_records_require_language_support(monkeypatch: pytest.MonkeyPatch) -> None:
    record = {key: value for key, value in RENDERERS["paged"].items() if key != "language_support"}
    monkeypatch.setitem(RENDERERS, "paged", record)
    assert "renderer 'paged' is missing language_support" in check_publication_registry(REPO)


# ---------------------------------------------------------------------------
# Pipeline wiring (no TeX)
# ---------------------------------------------------------------------------


def _project(tmp_path: Path, yaml: str, body: str = "Hello world.\n") -> Path:
    root = tmp_path / "publication"
    (root / "manuscript").mkdir(parents=True)
    (root / "fragments").mkdir()
    (root / "publication.yaml").write_text(yaml, encoding="utf-8")
    (root / "manuscript" / "order.txt").write_text("01-body.md\n", encoding="utf-8")
    (root / "manuscript" / "01-body.md").write_text("# Body\n\n" + body, encoding="utf-8")
    return root


@pytest.mark.parametrize(("language", "code", "exit_code"), [
    ("ar", "RK_LANGUAGE_RTL_UNSUPPORTED", 2),
    ("vi", "RK_LANGUAGE_METADATA_ONLY", 0),
    ("en-GB", None, 0),
])
def test_check_reports_language_compatibility_before_tex(tmp_path: Path, language: str, code: str | None, exit_code: int) -> None:
    root = _project(tmp_path, f"title: Language probe\nlanguage: {language}\n")
    result = subprocess.run(
        [str(REPO / "reportkit"), "check", "--source-root", str(root), "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    codes = [item["code"] for item in payload["diagnostics"]]
    assert result.returncode == exit_code, payload
    if code:
        assert code in codes
    else:
        assert not [value for value in codes if value.startswith("RK_LANGUAGE")]


def test_write_metadata_emits_policy_and_normalized_language(tmp_path: Path) -> None:
    sys.path.insert(0, str(REPO / "publication_pipeline" / "scripts"))
    from publication_build import write_metadata

    output = tmp_path / "metadata.tex"
    identity = {key: "" for key in ("subtitle", "author", "version", "date", "left_header", "footer",
                                     "subject", "keywords", "project_url", "disclaimer")}
    identity["title"] = "T"
    license_values = {"content_license": "X", "content_license_url": "https://example.com", "classification": ""}
    write_metadata(output, identity=identity, combined=False, license_values=license_values, cover_name=None,
                   uses_tables=False, uses_code=False, font_policy="strict", language="en_gb")
    text = output.read_text(encoding="utf-8")
    assert r"\setreportkitfontpolicy{strict}" in text
    assert r"\setreportkitlanguage{en-GB}" in text
    write_metadata(output, identity=identity, combined=False, license_values=license_values, cover_name=None,
                   uses_tables=False, uses_code=False)
    text = output.read_text(encoding="utf-8")
    assert r"\setreportkitfontpolicy{fallback}" in text
    assert r"\setreportkitlanguage" not in text


# ---------------------------------------------------------------------------
# Real compiles
# ---------------------------------------------------------------------------


def _compile(tmp_path: Path, engine: str, name: str, preamble: str, body: str, *,
             cls: str = "reportkit", options: str = "") -> tuple[int, str, bool]:
    if shutil.which(engine) is None:
        pytest.skip(f"{engine} not on PATH")
    if cls == "reportkit-slides":
        body = "\\begin{frame}{Probe}" + body + "\\end{frame}"
    documentclass = f"\\documentclass[{options}]{{{cls}}}" if options else f"\\documentclass{{{cls}}}"
    tex = tmp_path / f"{name}.tex"
    tex.write_text(
        f"{documentclass}\n{preamble}\n\\title{{Probe}}\\author{{ReportKit}}\n"
        f"\\begin{{document}}\n{body}\n\\end{{document}}\n",
        encoding="utf-8",
    )
    env = dict(
        os.environ, LC_ALL="C", openin_any="a",
        TEXINPUTS=f"{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:",
    )
    proc = subprocess.run(
        [engine, "-interaction=nonstopmode", "-halt-on-error", tex.name],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    log = (tmp_path / f"{name}.log").read_text(encoding="utf-8", errors="replace")
    return proc.returncode, log, (tmp_path / f"{name}.pdf").is_file()


CJK = "Hello \u4e2d\u6587 world."


def _unwrap(log: str) -> str:
    """Undo TeX's fixed-width log wrapping (it splits lines mid-word)."""
    return "".join(log.splitlines())


@pytest.mark.parametrize(("cls", "options"), [
    ("reportkit", ""),
    ("reportkit-slides", "theme=executive,publication-type=presentation"),
])
def test_missing_glyph_is_fatal_only_under_strict_font_policy(tmp_path: Path, cls: str, options: str) -> None:
    code, log, pdf = _compile(tmp_path, "lualatex", "strict", r"\setreportkitfontpolicy{strict}", CJK, cls=cls, options=options)
    assert code != 0 and not pdf, "strict font policy must stop the engine at a missing glyph"
    strict = inspect_log(log)
    assert any(item["type"] == "missing_glyph" and item["blocking"] for item in strict["diagnostics"])

    code, log, pdf = _compile(tmp_path, "lualatex", "fallback", "", CJK, cls=cls, options=options)
    assert code == 0 and pdf, "fallback keeps the historical engine behavior"
    fallback = inspect_log(log)
    assert "missing_glyph" in [item["type"] for item in fallback["diagnostics"]]
    assert fallback["passed"] is False, "the build-log gate still blocks a logged missing glyph"


def test_locale_typography_loads_only_for_verified_languages(tmp_path: Path) -> None:
    code, log, pdf = _compile(tmp_path, "pdflatex", "en", r"\setreportkitlanguage{en-GB}", "Hello.")
    assert code == 0 and pdf
    assert "babel.sty" in log and "loading babel locale american" in _unwrap(log)

    code, log, pdf = _compile(tmp_path, "pdflatex", "none", "", "Hello.")
    assert code == 0 and pdf
    assert "babel.sty" not in log, "the implicit en-US default must not load a locale package"

    code, log, pdf = _compile(tmp_path, "lualatex", "vi", r"\setreportkitlanguage{vi}", "Ti\u1ebfng Vi\u1ec7t.")
    assert code == 0 and pdf
    assert "babel.sty" not in log, "metadata-only languages must not load locale typography"
    assert "metadata-only for theme default" in _unwrap(log)
    pymupdf = pytest.importorskip("pymupdf")
    document = pymupdf.open(tmp_path / "vi.pdf")
    assert document.xref_get_key(document.pdf_catalog(), "Lang") == ("string", "vi")


@pytest.mark.parametrize(("preamble", "message"), [
    (r"\setreportkitlanguage{ar}", "RTL is explicitly unsupported"),
    (r"\setreportkitfontpolicy{strict}\setreportkitlanguage{de}", "is not declared by theme default"),
])
def test_tex_core_refuses_rtl_and_strict_undeclared_languages(tmp_path: Path, preamble: str, message: str) -> None:
    code, log, pdf = _compile(tmp_path, "pdflatex", "refused", preamble, "Hello.")
    assert code != 0 and not pdf
    assert message in _unwrap(log)


def test_undeclared_language_only_warns_under_fallback(tmp_path: Path) -> None:
    code, log, pdf = _compile(tmp_path, "pdflatex", "de", r"\setreportkitlanguage{de}", "Hallo.")
    assert code == 0 and pdf
    assert "babel.sty" not in log
    assert "Package reportkit-core Warning: Language 'de' is not declared" in _unwrap(log)


def test_vietnamese_fixture_proves_default_theme_cannot_set_it_under_pdflatex(tmp_path: Path) -> None:
    """The evidence behind keeping Vietnamese metadata-only for the default theme."""
    if shutil.which("pdflatex") is None:
        pytest.skip("pdflatex not on PATH")
    fixture = TEMPLATES / "examples" / "career_guide_vi" / "report.tex"
    shutil.copy(fixture, tmp_path / "report.tex")
    env = dict(os.environ, LC_ALL="C", TEXINPUTS=f"{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:")
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode != 0
    result = inspect_log((tmp_path / "report.log").read_text(encoding="utf-8", errors="replace"))
    glyphs = [item for item in result["diagnostics"] if item["type"] == "missing_glyph"]
    assert glyphs and "U+1EC0" in glyphs[0]["message"]


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("lualatex", "pandoc")),
    reason="pipeline compile requires LuaLaTeX and Pandoc",
)
@pytest.mark.parametrize(("policy", "exit_code"), [("strict", 4), ("fallback", 3)])
def test_pipeline_build_fails_on_missing_glyph_under_both_policies(tmp_path: Path, policy: str, exit_code: int) -> None:
    """strict stops in the engine (compile failure, exit 4); fallback compiles
    and the build-log gate blocks it (validation failure, exit 3)."""
    root = _project(
        tmp_path,
        "publication:\n  title: Glyph probe\n  language: en-US\n"
        "document:\n  engine: lualatex\n  theme: institutional-research\n  publication_type: equity-research\n"
        f"theme:\n  font_policy: {policy}\n",
        body=CJK + "\n",
    )
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--source-root", str(root), "--output-root", str(tmp_path / "out"), "--json"],
        capture_output=True, text=True, timeout=600,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == exit_code, payload
    kinds = [item["type"] for item in payload["diagnostics"]]
    assert "missing_glyph" in kinds, payload["diagnostics"]
    metadata = next((tmp_path / "out").rglob("metadata.tex")).read_text(encoding="utf-8")
    assert rf"\setreportkitfontpolicy{{{policy}}}" in metadata
    assert r"\setreportkitlanguage{en-US}" in metadata
