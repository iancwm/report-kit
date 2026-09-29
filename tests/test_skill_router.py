from __future__ import annotations

import re
from pathlib import Path

from reportkit.publications import PUBLICATION_TYPES
from reportkit.registry import COMMAND_CONTRACT


REPO = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO / "SKILL.md"
SKILL_TEXT = SKILL_PATH.read_text(encoding="utf-8")
FRONTMATTER = SKILL_TEXT.split("---", 2)[1]
DESCRIPTION_MATCH = re.search(r'^description: "([^"]*)"$', FRONTMATTER, re.MULTILINE)
if DESCRIPTION_MATCH is None:
    raise AssertionError("quoted description is missing from SKILL.md frontmatter")
SKILL_DESCRIPTION = DESCRIPTION_MATCH.group(1)


def test_skill_router_is_within_size_budget() -> None:
    assert len(SKILL_TEXT.encode("utf-8")) <= 12 * 1024


def test_description_and_selection_table_cover_every_publication_type() -> None:
    for publication_type in PUBLICATION_TYPES:
        assert publication_type in SKILL_DESCRIPTION

    table_start = next(
        index for index, line in enumerate(SKILL_TEXT.splitlines(), start=1)
        if line.startswith("| Requested output | Structure (")
    )
    assert table_start < 60
    selection_table = "\n".join(SKILL_TEXT.splitlines()[table_start - 1:])
    for publication_type in PUBLICATION_TYPES:
        assert f"`{publication_type}`" in selection_table

    header = SKILL_TEXT.splitlines()[table_start - 1]
    for concept in ("Structure", "Look", "Source mode", "engine", "Worked example", "composition brief", "Read next"):
        assert concept.casefold() in header.casefold()


def test_skill_router_uses_positive_target_guidance_without_template_prohibition() -> None:
    assert "The build refuses an undeclared target. Declare it; do not accept the default." in SKILL_TEXT
    assert "If LuaLaTeX is missing, fix the environment; keep the theme." in SKILL_TEXT
    assert "Use only primitives listed by `reportkit context --slice primitives --json` for your target." in SKILL_TEXT
    assert "If you cannot view rendered pages, say so in the delivery message." in SKILL_TEXT
    assert re.search(r"(?i)do not\s+copy[^\n]*REPORT_TEMPLATE(?:\.tex)?", SKILL_TEXT) is None


def test_every_cli_command_mentioned_in_skill_exists_in_command_contract() -> None:
    commands = set(re.findall(r"(?<![\w/.-])reportkit[ \t]+([a-z][a-z0-9-]*)", SKILL_TEXT))
    assert commands
    assert commands <= set(COMMAND_CONTRACT)


def test_skill_router_includes_status_transcript_example() -> None:
    assert "### Example status transcript" in SKILL_TEXT
    assert "TARGET structure=technical-report look=default renderer=paged  source=markdown  declared=publication.yaml  intent=.reportkit/intent.json" in SKILL_TEXT
    assert "intent: A concise technical report" in SKILL_TEXT
    assert "next step: deliver (Quote this status TARGET line in the delivery message.)" in SKILL_TEXT
