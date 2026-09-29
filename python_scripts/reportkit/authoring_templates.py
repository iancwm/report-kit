"""Per-target authoring skeletons (agent reasoning loop spec §4.5).

Each target's ``authoring.document_template`` comes from its canonical
example: preamble, opening primitive, and one example per native role.

Wave 0 stub: returns the ``\\maketitle`` skeleton every target used before
(moved verbatim from ``context.py``).
"""
from __future__ import annotations

from .publications import PUBLICATION_TYPES, RENDERERS


def document_template(publication_type: str, theme: str) -> str:
    """Return the starter TeX document for ``publication_type`` under ``theme``."""
    renderer = PUBLICATION_TYPES[publication_type]["renderer"]
    class_name = RENDERERS[renderer]["class_adapter"]
    document_options = f"theme={theme},publication-type={publication_type}"
    return (
        f"\\documentclass[{document_options}]{{{class_name}}}\n"
        "\\title{Contract acceptance}\n\\author{ReportKit}\n"
        "\\begin{document}\n\\maketitle\n{{body}}\n\\end{document}\n"
    )
