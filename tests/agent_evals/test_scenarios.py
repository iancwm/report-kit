"""Opt-in CLI scenarios from reasoning-loop spec §4.9."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_evals.harness import OracleDriver, REPO_ROOT, Transcript
from reportkit.initialization import initialize
from reportkit.publications import PUBLICATION_TYPES


pytestmark = pytest.mark.agent_eval


def _build_report(workdir: Path) -> dict:
    path = workdir / "build" / "combined" / "build-report.json"
    assert path.is_file(), f"missing build report: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_published(
    transcript: Transcript,
    *,
    publication_type: str,
    theme: str | None,
) -> None:
    assert transcript.succeeded, transcript.summary()
    report = _build_report(transcript.workdir)
    selection = report.get("selection")
    assert isinstance(selection, dict), report
    assert selection.get("publication_type") == publication_type
    if theme is None:
        allowed_themes = PUBLICATION_TYPES[publication_type]["themes"]
        assert selection.get("theme") in allowed_themes, selection
    else:
        assert selection.get("theme") == theme, selection

    audit = transcript.event("CHECK").json().get("composition")
    assert isinstance(audit, dict), transcript.event("CHECK").stdout
    assert audit.get("passed") is True, audit


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Start with a consumer project directory, as the loop's workdir."""
    workdir = tmp_path / "publication"
    initialize(workdir, REPO_ROOT)
    return workdir


@pytest.mark.parametrize(
    ("prompt", "publication_type", "theme"),
    [
        ("Write a magazine-style feature about X, like this reference.", "feature-article", "editorial"),
        ("Prepare a 4-page decision brief for the CFO.", "executive-brief", None),
        ("Create a 10-slide consulting deck.", "presentation", "executive"),
    ],
)
def test_prompt_selects_target_and_audit_passes(
    project: Path,
    prompt: str,
    publication_type: str,
    theme: str | None,
) -> None:
    transcript = OracleDriver().run(prompt, project)
    _assert_published(transcript, publication_type=publication_type, theme=theme)


def test_context_reset_reloads_target_from_the_project(
    project: Path,
) -> None:
    original_prompt = "Write a magazine-style feature about X, like this reference."
    first = OracleDriver(stop_after="AUTHOR").run(original_prompt, project)
    assert first.succeeded, first.summary()
    assert not (project / "build" / "combined" / "build-report.json").exists()

    intent_path = project / ".reportkit" / "intent.json"
    assert intent_path.is_file()
    persisted_intent = json.loads(intent_path.read_text(encoding="utf-8"))
    assert persisted_intent.get("request") == original_prompt

    continuation = f"continue the publication in {project}"
    fresh_driver = OracleDriver()
    resumed = fresh_driver.run(continuation, project)

    assert resumed.event("REHYDRATE").returncode == 0, resumed.summary()
    assert resumed.target == {"publication_type": "feature-article", "theme": "editorial", "source_mode": "tex"}
    assert json.loads(intent_path.read_text(encoding="utf-8")).get("request") == original_prompt
    _assert_published(resumed, publication_type="feature-article", theme="editorial")
