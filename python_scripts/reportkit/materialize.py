"""Materialize a target's authoring guidance into a consumer project.

The engine clone is read-only reference. Agents exploring it for primitive
syntax and validation gotchas waste context and make mistakes. This module
copies the reference docs that matter for the locked target, plus the
target-scoped context slice and a preflight checklist, into
``<project>/.reportkit/`` so the agent reads local files instead.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

# Reference docs copied for every target: primitive syntax and the shared
# gotchas. Kept minimal so the agent opens only what it needs.
CORE_REFERENCES: tuple[str, ...] = (
    "diagrams-and-algorithms.md",
    "charts.md",
    "markdown-authoring.md",
    "troubleshooting.md",
    "known-fixes.md",
    "callouts-and-image-slots.md",
    "visual-grammar.md",
    "licensing.md",
)

# One extra guide per publication structure (the SKILL.md "Read next" column).
TYPE_REFERENCE: dict[str, str] = {
    "equity-research": "institutional-research-theme.md",
    "executive-brief": "executive-brief-authoring.md",
    "feature-article": "feature-article-authoring.md",
    "book": "book-authoring.md",
    "presentation": "presentation-authoring.md",
}

# One extra guide per look.
THEME_REFERENCE: dict[str, str] = {
    "operator": "operator-theme.md",
    "institutional-research": "institutional-research-theme.md",
}

CHECKLIST_TEXT = """\
# ReportKit consumer preflight

Work from these local files — `.reportkit/references/` (syntax) and
`.reportkit/context.json` (allowed primitives + Markdown forms). Do not explore
the engine clone to infer fixes; every `check`/`build` diagnostic carries a
`remediation` string that is authoritative.

Run these in order:

1. `reportkit status --source-root . --json` — recover the declared target and
   follow its `next_step`. Do not re-derive the target.
2. `reportkit context --source-root . --slice primitives --json` — read the
   FULL output, especially `markdown_forms`. The visual marker
   `[[REPORTKIT-VISUAL:fig:<slug>]]` is the ONLY way to place a diagram or chart
   in a Markdown manuscript.
3. Confirm `fragments/` exists (empty is fine). Missing it fails
   `MISSING_FRAGMENT_DIRECTORY`.
4. `composition-brief.json`: for `technical-report` the `required` array must be
   `[]` (that structure has no role patterns; any entry is an "unknown
   composition role"), and `visual_reference` must be non-empty.
5. Each `fragments/fig-<slug>.tex` holds EXACTLY ONE `diagram` environment with
   `label={fig:<slug>}`, a `caption=`, a `description=` (alt text), and a
   `source=`. Omitting the label fails `DIAGRAM_LABEL_COUNT`; an empty
   `description` drops the figure's alt text.
6. Heading text becomes a LaTeX label — two headings with identical text
   collide as "multiply defined".
7. `reportkit check --source-root . --json` — read EVERY diagnostic's
   `remediation` and fix top-down. Never read engine source to guess the fix.
8. A combined build writes exactly one PDF, `<slug>.pdf`, into `build/combined/`;
   the directory is rebuilt from scratch each run and the intermediate
   `publication.pdf` is renamed, never duplicated. `reportkit package` copies
   the single PDF into `output/`.
"""


def reference_names(publication_type: str, theme: str) -> tuple[str, ...]:
    """Reference docs to copy for a (structure, look) pair, deduplicated."""
    names = list(CORE_REFERENCES)
    if publication_type in TYPE_REFERENCE:
        names.append(TYPE_REFERENCE[publication_type])
    if theme in THEME_REFERENCE:
        names.append(THEME_REFERENCE[theme])
    return tuple(dict.fromkeys(names))


def materialize(
    source_root: Path,
    repo_root: Path,
    context_slice: dict[str, Any],
    publication_type: str,
    theme: str,
) -> dict[str, Any]:
    """Copy references, context, and a checklist into ``<project>/.reportkit/``.

    Returns a summary mapping ``references`` (relative filenames copied),
    ``context`` and ``checklist`` (absolute paths), and ``directory``.
    """
    dest = source_root / ".reportkit"
    refs_dir = dest / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for name in reference_names(publication_type, theme):
        src = repo_root / "references" / name
        if src.is_file():
            shutil.copy2(src, refs_dir / name)
            copied.append(name)

    context_path = dest / "context.json"
    context_path.write_text(
        json.dumps(context_slice, indent=2, sort_keys=True), encoding="utf-8"
    )
    checklist_path = dest / "CHECKLIST.md"
    checklist_path.write_text(CHECKLIST_TEXT, encoding="utf-8")

    return {
        "directory": str(dest.resolve()),
        "references": copied,
        "context": str(context_path.resolve()),
        "checklist": str(checklist_path.resolve()),
    }
