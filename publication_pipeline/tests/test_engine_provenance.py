"""The image has no .git; commit provenance must come from the build args."""
from __future__ import annotations

import publication_build


def test_commit_falls_back_to_image_environment(monkeypatch) -> None:
    monkeypatch.setattr(publication_build, "git_value", lambda args: "unknown")
    monkeypatch.setenv("REPORTKIT_COMMIT", "a" * 40)
    monkeypatch.setenv("REPORTKIT_REF", "v1.9.3")
    assert publication_build.engine_commit() == "a" * 40
    assert publication_build.engine_ref() == "v1.9.3"


def test_checkout_value_wins_over_environment(monkeypatch) -> None:
    monkeypatch.setattr(publication_build, "git_value", lambda args: "b" * 40)
    monkeypatch.setenv("REPORTKIT_COMMIT", "a" * 40)
    assert publication_build.engine_commit() == "b" * 40


def test_unknown_when_neither_is_available(monkeypatch) -> None:
    monkeypatch.setattr(publication_build, "git_value", lambda args: "unknown")
    monkeypatch.delenv("REPORTKIT_COMMIT", raising=False)
    monkeypatch.setenv("REPORTKIT_REF", "unknown")
    assert publication_build.engine_commit() == "unknown"
    assert publication_build.engine_ref() == "unknown"
