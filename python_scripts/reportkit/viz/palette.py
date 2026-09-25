"""Theme-file resolution and Python/LaTeX palette and token-contract checks.

Separated from ``core.py`` because these functions validate ReportKit's
theme system against its LaTeX side rather than render a chart; they back the
module's ``check-theme`` CLI command.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Mapping

from reportkit.publications import THEMES, canonical_theme_name
from reportkit.themes import get_theme, validate_theme_contract


def theme_file_for(theme: str, repo_root: str | Path | None = None) -> Path:
    """Resolve a theme name to its LaTeX file, e.g. "default" -> themes/reportkit-theme-default.sty.

    Since v1.6.0, ReportKit's palette lives in a theme file under
    latex_templates/themes/, not in reportkit.cls itself -- see
    docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md,
    open question 2.
    """
    # palette.py lives at python_scripts/reportkit/viz/palette.py; the
    # repository root is therefore three parents above this module.
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    canonical = canonical_theme_name(theme)
    return root / "latex_templates" / "themes" / f"reportkit-theme-{canonical}.sty"


def validate_palette_against_latex(class_path: str | Path, colors: Mapping[str, str] | None = None) -> list[str]:
    """Return human-readable mismatches between Python and a ReportKit theme's LaTeX colors.

    `colors` defaults to LATEX_THEME_COLORS -- the currently-applied theme's
    Python-side palette (default theme's, unless apply_theme() switched it)
    -- for backward compatibility with callers that don't specify one.  Pass
    `reportkit.themes.get_theme(name).latex_colors` explicitly to check a
    *specific* theme regardless of which one is currently applied; this
    module's own `check-theme` CLI command does exactly that (open question
    2's resolution: the Python-side check is theme-parameterized, closing
    the honest-failure gap the institutional theme had here from Step 1
    through Step 3, before reportkit.themes.institutional_research existed).
    """
    if colors is None:
        from . import core

        colors = core.LATEX_THEME_COLORS
    class_path = Path(class_path)
    text = class_path.read_text(encoding="utf-8")
    found = {
        name: f"#{value.upper()}"
        for name, value in re.findall(r"\\definecolor\{([^}]+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}", text)
    }
    mismatches: list[str] = []
    for name, expected in colors.items():
        actual = found.get(name)
        if actual is None:
            mismatches.append(f"missing LaTeX color: {name}")
        elif actual.upper() != expected.upper():
            mismatches.append(f"{name}: LaTeX {actual} != Python {expected}")
    return mismatches


def validate_theme_contract_against_latex(
    theme: str,
    *,
    repo_root: str | Path | None = None,
) -> list[str]:
    """Validate one Python theme and its shared/common LaTeX token boundary."""
    try:
        resolved = get_theme(theme)
    except ValueError as exc:
        return [str(exc)]

    errors = validate_theme_contract(resolved)
    canonical = canonical_theme_name(theme)
    record = THEMES.get(canonical)
    if record is None:
        return [*errors, f"theme {theme!r} is missing from the publication registry"]

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    themes_root = root / "latex_templates" / "themes"
    common_package = str(record.get("common_package", ""))
    common_path = themes_root / f"{common_package}.sty"
    if not common_package or not common_path.is_file():
        errors.append(f"missing common theme package: {common_package or '<unset>'}")
        common_text = ""
    else:
        common_text = common_path.read_text(encoding="utf-8")

    core_path = root / "latex_templates" / "reportkit-core.sty"
    if not core_path.is_file():
        errors.append(f"missing shared theme-token contract: {core_path}")
        core_text = ""
    else:
        core_text = core_path.read_text(encoding="utf-8")

    declared = set(re.findall(r"\\newcommand\{\\(RKTok[A-Za-z0-9]+)\}", core_text))
    semantic_modules = (
        "reportkit-boxes.sty",
        "reportkit-diagrams.sty",
        "reportkit-structure.sty",
        "reportkit-process.sty",
        "reportkit-spatial.sty",
    )
    used: set[str] = set()
    for module in semantic_modules:
        module_path = root / "latex_templates" / module
        if not module_path.is_file():
            errors.append(f"missing semantic module for shared token check: {module}")
            continue
        used.update(re.findall(r"\\(RKTok[A-Za-z0-9]+)", module_path.read_text(encoding="utf-8")))

    for token in sorted(used):
        if token not in declared:
            errors.append(f"{token} is used by a semantic module but not declared in reportkit-core.sty")
        if not re.search(rf"\\renewcommand\{{\\{re.escape(token)}\}}", common_text):
            errors.append(f"{common_package}.sty does not populate {token}")

    for renderer in record.get("renderers", []):
        adapter = (record.get("renderer_adapters") or {}).get(renderer)
        if not adapter:
            errors.append(f"theme {canonical!r} is missing its {renderer!r} renderer adapter")
            continue
        adapter_path = themes_root / f"{adapter}.sty"
        if not adapter_path.is_file():
            errors.append(f"missing {renderer} theme adapter: {adapter_path}")
        elif renderer == "slides":
            adapter_text = adapter_path.read_text(encoding="utf-8")
            if r"\rk@presentationtokensloadedtrue" not in adapter_text:
                errors.append(f"{adapter}.sty does not load presentation tokens")

    return errors


__all__ = ["theme_file_for", "validate_palette_against_latex", "validate_theme_contract_against_latex"]
