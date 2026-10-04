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
                    "In a Markdown project, trusted fragments in fragments/ reference a link with \\RKLink{<key>}; a direct-TeX project uses \\href instead.",
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
