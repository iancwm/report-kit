from __future__ import annotations

import json
from pathlib import Path
import subprocess

from reportkit.context import build_context
from reportkit.context_budget import build_context_slice, estimate_tokens
from reportkit.diagnostics import make_diagnostic
from reportkit.loop import LOOP_STEPS, next_step, target_line, target_payload
from reportkit.target import TargetState


REPO = Path(__file__).resolve().parents[1]


def _state(root: Path | None = None) -> TargetState:
    return TargetState(
        publication_type="feature-article", theme="editorial", renderer="paged",
        source_mode="tex", main="report.tex", declared_by="publication.yaml",
        intent=None, require_declared=False, source_root=root,
    )


def test_target_line_names_structure_and_look_and_payload_matches() -> None:
    state = _state(Path("/tmp/publication"))
    line = target_line(state)
    assert line == (
        "TARGET structure=feature-article look=editorial renderer=paged  source=tex  "
        "declared=publication.yaml  intent=.reportkit/intent.json"
    )
    payload = target_payload(state)
    assert payload["line"] == line
    assert payload["structure"] == payload["publication_type"] == "feature-article"
    assert payload["look"] == payload["theme"] == "editorial"
    assert payload["source_mode"] == "tex"
    assert target_line(None) == ""
    assert target_payload(None) == {}


def test_next_step_success_follows_the_loop_table() -> None:
    state = _state()
    outcomes = [
        ("context", {"slice": "quickstart"}, LOOP_STEPS[1].command),
        ("target set", {}, LOOP_STEPS[2].command),
        ("init", {}, LOOP_STEPS[3].command),
        ("context", {"slice": "primitives"}, LOOP_STEPS[4].command),
        ("check", {}, LOOP_STEPS[5].command),
        ("build", {}, LOOP_STEPS[6].command),
        ("review", {}, LOOP_STEPS[7].command),
    ]
    for command, outcome, expected in outcomes:
        assert next_step(command, state, {"passed": True, **outcome})["command"] == expected


def test_failed_target_gate_returns_remediation_command() -> None:
    diagnostic = make_diagnostic("target_contract", "declare the target", code="RK_TARGET_UNDECLARED")
    result = next_step("check", _state(), {"passed": False, "diagnostics": [diagnostic]})
    assert result["command"].startswith("reportkit target set --publication-type feature-article")
    assert "--theme editorial" in result["command"]
    assert result["reason"] == diagnostic["remediation"]


def test_quickstart_has_axis_explanation_selection_table_and_source_modes(tmp_path: Path) -> None:
    (tmp_path / "publication.yaml").write_text("title: Loop fixture\n", encoding="utf-8")
    context = build_context(REPO, tmp_path)
    payload = build_context_slice(context, "quickstart")
    text = payload["content"]["text"]
    assert "Structure selects the publication type; look selects its visual theme." in text
    assert "| Structure | Choose it for | Compatible looks | Renderer | Source modes |" in text
    assert "tex=required, markdown=opening-only" in text
    assert "TARGET NOT DECLARED" in text
    assert "The current target is" not in text
    assert payload["estimated_tokens"] <= 2_000
    assert estimate_tokens(payload["content"]) <= 2_000


def test_json_commands_include_target_and_next_step_and_human_starts_with_target(tmp_path: Path) -> None:
    (tmp_path / "publication.yaml").write_text(
        "title: Loop fixture\ndocument:\n  publication_type: technical-report\n  theme: default\n  source_mode: markdown\n",
        encoding="utf-8",
    )
    commands = [
        ["context", "--source-root", str(tmp_path), "--slice", "quickstart", "--json"],
        ["target", "show", "--source-root", str(tmp_path), "--json"],
        ["status", "--source-root", str(tmp_path), "--json"],
    ]
    for command in commands:
        result = subprocess.run([str(REPO / "reportkit"), *command], capture_output=True, text=True)
        payload = json.loads(result.stdout)
        assert payload["target"]["line"].startswith("TARGET structure=technical-report look=default")
        assert payload["next_step"]["command"]

    human = subprocess.run(
        [str(REPO / "reportkit"), "target", "show", "--source-root", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert human.stdout.startswith("TARGET structure=technical-report look=default")
