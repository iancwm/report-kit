from __future__ import annotations

import json
from pathlib import Path

from adapters.openai import build_tool_bundle, write_minimal_publication


REPO = Path(__file__).resolve().parents[1]


def test_checked_in_openai_bundle_is_generated_from_the_cli_contract() -> None:
    checked_in = json.loads((REPO / "adapters" / "openai" / "tools.json").read_text())
    generated = build_tool_bundle()
    assert checked_in == generated
    names = {tool["name"] for tool in generated["tools"]}
    assert {"reportkit_context", "reportkit_check", "reportkit_build"} <= names
    assert all("--json" not in json.dumps(tool) for tool in generated["tools"])


def test_openai_neutral_adapter_authors_and_validates_without_skill_prose(tmp_path: Path) -> None:
    result = write_minimal_publication(tmp_path)
    assert result["passed"] is True
    assert result["primitive"] == "principle"
    assert result["validation"]["passed"] is True
    assert not (tmp_path / "SKILL.md").exists()
    assert "reportkit principle" in (tmp_path / "manuscript" / "01-smoke.md").read_text()
