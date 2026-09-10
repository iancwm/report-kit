"""Canonical publication, renderer, and theme capability catalog.

Only combinations implemented by the current paged renderer belong here.  The
future renderer work extends this registry rather than adding parallel checks.
"""
from __future__ import annotations

from typing import Any

RENDERERS: dict[str, dict[str, Any]] = {
    "paged": {
        "name": "paged",
        "stability": "stable",
        "since": "1.0.0",
        "accessibility": {
            "pdf_metadata": "supported",
            "catalog_language": "supported",
            "bookmarks": "supported",
            "meaningful_links": "supported",
            "diagram_actual_text": "supported",
            "tagged_pdf": "unsupported",
            "tagged_pdf_reason": "The pinned LaTeX format has not yet passed the documented tagging spike.",
        },
    },
}

THEMES: dict[str, dict[str, Any]] = {
    "default": {
        "name": "default",
        "renderers": ["paged"],
        "required_engine": "pdflatex",
        "semantic_tokens": [
            "ink", "muted", "hairline", "surface", "primary", "secondary",
            "evidence", "warning", "danger", "data_series", "body", "heading",
            "metadata", "table", "chart", "diagram",
        ],
        "language_support": {
            "verified": ["en"],
            "metadata_only": ["vi"],
            "scripts": {"verified": ["Latn"], "metadata_only": []},
            "rtl": "unsupported",
        },
        "stability": "stable",
        "since": "1.0.0",
    },
    "institutional-research": {
        "name": "institutional-research",
        "renderers": ["paged"],
        "required_engine": "lualatex",
        "semantic_tokens": [
            "ink", "muted", "hairline", "surface", "primary", "secondary",
            "evidence", "warning", "danger", "data_series", "body", "heading",
            "metadata", "table", "chart", "diagram",
        ],
        "language_support": {
            "verified": ["en"],
            "metadata_only": ["vi"],
            "scripts": {"verified": ["Latn"], "metadata_only": []},
            "rtl": "unsupported",
        },
        "stability": "stable",
        "since": "1.7.0",
    },
}

PUBLICATION_TYPES: dict[str, dict[str, Any]] = {
    "technical-report": {
        "name": "technical-report",
        "renderer": "paged",
        "paper": "a4",
        "themes": ["default"],
        "selection_criteria": "General technical reports, guides, and long-form analytical documents.",
        "stability": "stable",
        "since": "1.0.0",
    },
    "equity-research": {
        "name": "equity-research",
        "renderer": "paged",
        "paper": "letter",
        "themes": ["institutional-research"],
        "selection_criteria": "Exhibit-led institutional equity research and investment analysis.",
        "stability": "stable",
        "since": "1.8.0",
    },
}


def compatibility_error(publication_type: str, theme: str) -> str | None:
    publication = PUBLICATION_TYPES.get(publication_type)
    if publication is None:
        return f"unknown publication type {publication_type!r}"
    if theme not in THEMES:
        return f"unknown theme {theme!r}"
    if theme not in publication["themes"]:
        choices = ", ".join(publication["themes"])
        return (
            f"theme {theme!r} does not support publication type {publication_type!r}; "
            f"compatible themes: {choices}"
        )
    return None


def availability_for(*, publication_type: str | None = None) -> dict[str, list[str]]:
    if publication_type:
        publication = PUBLICATION_TYPES[publication_type]
        return {
            "publication_types": [publication_type],
            "themes": list(publication["themes"]),
            "renderers": [publication["renderer"]],
        }
    return {
        "publication_types": list(PUBLICATION_TYPES),
        "themes": list(THEMES),
        "renderers": list(RENDERERS),
    }
