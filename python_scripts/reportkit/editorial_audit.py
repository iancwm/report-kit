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


def audit_editorial_source(tex: Path, brief: Path) -> dict[str, Any]:
    """Check a feature's source against a declared, publication-specific brief."""
    source = tex.read_text(encoding="utf-8")
    request = json.loads(brief.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("editorial brief must be a JSON object")
    required = request.get("required", [])
    minimum_exhibits = request.get("minimum_exhibits", 0)
    reference = request.get("visual_reference")
    if not isinstance(required, list) or any(not isinstance(role, str) or role not in ROLES for role in required) or len(set(required)) != len(required):
        raise ValueError(f"brief.required must list distinct roles from {', '.join(sorted(ROLES))}")
    if not isinstance(minimum_exhibits, int) or isinstance(minimum_exhibits, bool) or minimum_exhibits < 0:
        raise ValueError("brief.minimum_exhibits must be a nonnegative integer")
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
        inventory=inventory, manual_review_required=True, manual_review=list(MANUAL_REVIEW),
    )
