"""Brief-driven composition audit for hand-authored editorial features.

This checks observable TeX structure. It cannot judge whether an exhibit is
useful, a quotation is genuine, or rendered pages look good; those remain
explicit manual review items.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any

from .diagnostics import diagnostic_envelope, make_diagnostic

ROLES = frozenset({
    "openingvisual", "dropcap", "featurecolumns", "pullquote",
    "featuresidebar", "featureexhibit", "graphic-exhibit", "full-width-exhibit",
})
MANUAL_REVIEW = (
    "Compare every rendered page with the chosen editorial reference for visual rhythm, whitespace, and legibility.",
    "Verify that every pull quote appears in the article or a named source; never invent quotation or attribution.",
    "Verify that each exhibit answers a reader question and credits its evidence; do not invent chart data.",
)


def _uncomment(source: str) -> str:
    """Remove TeX comments without dropping escaped percent signs."""
    return "\n".join(re.split(r"(?<!\\)%", line, maxsplit=1)[0] for line in source.splitlines())


def _inventory(source: str) -> dict[str, int]:
    body = _uncomment(source)
    def count(pattern: str) -> int:
        return len(re.findall(pattern, body))

    exhibits = re.findall(r"\\begin\{featureexhibit\}(?:\[[^]]*\])?.*?\\end\{featureexhibit\}", body, re.S)
    return {
        "openingvisual": count(r"\\begin\{openingvisual\}"),
        "dropcap": count(r"\\dropcap\s*\{"),
        "featurecolumns": count(r"\\begin\{featurecolumns\}"),
        "pullquote": count(r"\\pullquote\s*\{"),
        "featuresidebar": count(r"\\begin\{featuresidebar\}"),
        "featureexhibit": len(exhibits),
        "graphic-exhibit": sum(bool(re.search(r"\\includegraphics\b|\\begin\{diagram\}", block)) for block in exhibits),
        "full-width-exhibit": count(r"\\begin\{featureexhibit\}\[span=full\]"),
    }


def _prose_words(source: str) -> int:
    """Approximate narrative words, excluding wide reference and visual blocks."""
    for environment in ("featureexhibit", "openingvisual", "featuresidebar", "featurereferences", "longtable", "tabular", "tabularx", "table", "diagram"):
        source = re.sub(rf"\\begin\{{{environment}\}}.*?\\end\{{{environment}\}}", " ", source, flags=re.S)
    source = re.sub(r"\\(?:pullquote|featuresection|featureheadline|featuredeck|featurebyline|imagecredit|caption|source)\s*(?:\[[^]]*\])?\s*\{[^{}]*\}", " ", source)
    source = re.sub(r"\\(?:begin|end)\s*\{[^{}]*\}|\\[A-Za-z@]+\*?", " ", source)
    source = re.sub(r"https?://\S+", " ", source)
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", source))


def _column_coverage(source: str) -> tuple[int, int]:
    """Return narrative words in columns and total narrative words."""
    source = _uncomment(source)
    columns = re.findall(r"\\begin\{featurecolumns\}(.*?)\\end\{featurecolumns\}", source, re.S)
    in_columns = sum(_prose_words(block) for block in columns)
    return in_columns, _prose_words(source)


def _without_reference_tail(section: str) -> str:
    """A chapter's source ledger is lookup material, not narrative prose."""
    return re.split(r"\\(?:subsection|subsubsection)\*?\{(?:Sources|Evidence notes and references)\}", section, maxsplit=1)[0]


def audit_editorial_source(tex: Path, brief: Path) -> dict[str, Any]:
    """Check a feature's source against a declared, publication-specific brief."""
    source = tex.read_text(encoding="utf-8")
    request = json.loads(brief.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("editorial brief must be a JSON object")
    required = request.get("required", [])
    minimum_exhibits = request.get("minimum_exhibits", 0)
    minimum_graphics = request.get("minimum_graphic_exhibits", 0)
    minimum_quotes = request.get("minimum_pullquotes", 0)
    minimum_ratio = request.get("minimum_column_prose_ratio", 0)
    section_ratio = request.get("section_minimum_column_prose_ratio", 0)
    section_quotes = request.get("section_minimum_pullquotes", 0)
    section_graphics = request.get("section_minimum_graphic_exhibits", 0)
    excluded_sections = request.get("exclude_sections", [])
    reference = request.get("visual_reference")
    if not isinstance(required, list) or any(not isinstance(role, str) or role not in ROLES for role in required) or len(set(required)) != len(required):
        raise ValueError(f"brief.required must list distinct roles from {', '.join(sorted(ROLES))}")
    if not isinstance(minimum_exhibits, int) or isinstance(minimum_exhibits, bool) or minimum_exhibits < 0:
        raise ValueError("brief.minimum_exhibits must be a nonnegative integer")
    for name, value in (("minimum_graphic_exhibits", minimum_graphics), ("minimum_pullquotes", minimum_quotes),
                        ("section_minimum_pullquotes", section_quotes), ("section_minimum_graphic_exhibits", section_graphics)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"brief.{name} must be a nonnegative integer")
    for name, value in (("minimum_column_prose_ratio", minimum_ratio), ("section_minimum_column_prose_ratio", section_ratio)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"brief.{name} must be between 0 and 1")
    if not isinstance(excluded_sections, list) or any(not isinstance(title, str) for title in excluded_sections):
        raise ValueError("brief.exclude_sections must be a list of section titles")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("brief.visual_reference must name the chosen example or visual reference")
    if not required and minimum_exhibits == 0:
        raise ValueError("brief must require at least one editorial role or exhibit")

    code = _uncomment(source)
    inventory = _inventory(source)
    diagnostics = []
    class_match = re.search(r"\\documentclass\s*\[([^]]*)\]\s*\{reportkit\}", code)
    options = {item.strip() for item in class_match.group(1).split(",")} if class_match else set()
    if not {"theme=editorial", "publication-type=feature-article"} <= options:
        diagnostics.append(make_diagnostic(
            "publication_validation", "Source must select ReportKit's editorial feature-article pair.",
            code="RK_EDITORIAL_TARGET", source={"file": str(tex), "line": 1},
        ))
    for role in required:
        if inventory[role] == 0:
            diagnostics.append(make_diagnostic(
                "publication_validation", f"Editorial brief requires {role}, but the source has none.",
                code="RK_EDITORIAL_COMPOSITION", source={"file": str(tex), "line": None},
                primitive=role,
                remediation="Use the ReportKit feature primitive where the article's evidence supports it, or revise the brief with a documented editorial reason.",
            ))
    if inventory["featureexhibit"] < minimum_exhibits:
        diagnostics.append(make_diagnostic(
            "publication_validation",
            f"Editorial brief requires {minimum_exhibits} exhibits; source has {inventory['featureexhibit']}.",
            code="RK_EDITORIAL_EXHIBITS", source={"file": str(tex), "line": None},
            primitive="featureexhibit",
            remediation="Add evidence-led exhibits or revise the brief with a documented editorial reason.",
        ))
    for role, minimum in (("graphic-exhibit", minimum_graphics), ("pullquote", minimum_quotes)):
        if inventory[role] < minimum:
            diagnostics.append(make_diagnostic(
                "publication_validation", f"Editorial brief requires {minimum} {role} roles; source has {inventory[role]}.",
                code="RK_EDITORIAL_GRAPHICS" if role == "graphic-exhibit" else "RK_EDITORIAL_QUOTES",
                source={"file": str(tex), "line": None}, primitive=role,
            ))
    article_body = code.split(r"\begin{document}", 1)[-1]
    parts = re.split(r"\\featuresection\{([^{}]+)\}(?:\[[^]]*\])?", article_body)
    column_words, prose_words = _column_coverage(parts[0])
    for section in parts[2::2]:
        inside, total = _column_coverage(_without_reference_tail(section))
        column_words += inside
        prose_words += total
    if minimum_ratio and prose_words and column_words / prose_words < minimum_ratio:
        diagnostics.append(make_diagnostic(
            "publication_validation", f"Only {column_words}/{prose_words} narrative words are in two columns; brief requires {minimum_ratio:.0%}.",
            code="RK_EDITORIAL_COLUMN_COVERAGE", source={"file": str(tex), "line": None},
            remediation="Use featurecolumns for ordinary narrative; reserve full width for openings, visuals, wide data, and deliberate emphasis.",
        ))
    section_coverages = {}
    if section_ratio or section_quotes or section_graphics:
        for title, section in zip(parts[1::2], parts[2::2]):
            if title in excluded_sections:
                continue
            inside, total = _column_coverage(_without_reference_tail(section))
            section_inventory = _inventory(section)
            section_coverages[title] = {"column_words": inside, "prose_words": total,
                                        "pullquotes": section_inventory["pullquote"],
                                        "graphic_exhibits": section_inventory["graphic-exhibit"]}
            if total >= 100 and inside / total < section_ratio:
                diagnostics.append(make_diagnostic(
                    "publication_validation", f"Section {title!r} has {inside}/{total} narrative words in two columns; brief requires {section_ratio:.0%}.",
                    code="RK_EDITORIAL_SECTION_COLUMNS", source={"file": str(tex), "line": None},
                ))
            if section_inventory["pullquote"] < section_quotes:
                diagnostics.append(make_diagnostic(
                    "publication_validation", f"Section {title!r} has {section_inventory['pullquote']} pull quotes; brief requires {section_quotes}.",
                    code="RK_EDITORIAL_SECTION_QUOTES", source={"file": str(tex), "line": None},
                ))
            if section_inventory["graphic-exhibit"] < section_graphics:
                diagnostics.append(make_diagnostic(
                    "publication_validation", f"Section {title!r} has {section_inventory['graphic-exhibit']} graphic exhibits; brief requires {section_graphics}.",
                    code="RK_EDITORIAL_SECTION_GRAPHICS", source={"file": str(tex), "line": None},
                ))
    article_body = code.split(r"\begin{document}", 1)[-1]
    forbidden = re.search(r"\\(?:fontsize|vspace|hspace|definecolor)\b|\\begin\{minipage\}|\\color\s*\{", article_body)
    if forbidden:
        diagnostics.append(make_diagnostic(
            "publication_validation", f"Local styling command {forbidden.group()} bypasses feature theme tokens.",
            code="RK_EDITORIAL_LOCAL_STYLE", source={"file": str(tex), "line": None},
            remediation="Remove local styling and use ReportKit feature primitives and theme tokens.",
        ))
    return diagnostic_envelope(
        diagnostics, source=str(tex), brief=str(brief), visual_reference=reference,
        inventory=inventory, column_coverage={"column_words": column_words, "prose_words": prose_words},
        section_coverages=section_coverages, manual_review_required=True, manual_review=list(MANUAL_REVIEW),
    )
