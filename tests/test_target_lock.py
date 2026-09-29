from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "python_scripts"))

from reportkit.config import load_publication_config, resolve_document  # noqa: E402
from reportkit.diagnostics import registered_exit_code  # noqa: E402
from reportkit.initialization import initialize_project  # noqa: E402
from reportkit.publications import PUBLICATION_TYPES  # noqa: E402
from reportkit.target import _validate_intent, load_target, resolve_alias, set_target, target_gate  # noqa: E402


def test_load_target_resolves_blank_init_placeholder_and_blocks_it(tmp_path: Path) -> None:
    project, _ = initialize_project(tmp_path / "publication", REPO)

    state = load_target(project)

    assert (state.publication_type, state.theme, state.source_mode) == (
        "technical-report", "default", "markdown",
    )
    assert state.declared_by == "default"
    assert state.require_declared is True
    diagnostics = target_gate(state)
    assert [item["code"] for item in diagnostics] == ["RK_TARGET_UNDECLARED"]
    assert registered_exit_code(diagnostics) == 3


def test_legacy_default_target_only_adds_nonblocking_warning(tmp_path: Path) -> None:
    state = load_target(tmp_path)

    diagnostics = target_gate(state)

    assert [item["code"] for item in diagnostics] == ["RK_TARGET_IMPLICIT"]
    assert diagnostics[0]["severity"] == "warning"
    assert registered_exit_code(diagnostics) is None


def test_tex_class_options_are_a_fallback_but_yaml_remains_authoritative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from reportkit import tex_target

    monkeypatch.setattr(
        tex_target,
        "read_class_options",
        lambda _path: {"publication-type": "feature-article", "theme": "editorial"},
    )
    (tmp_path / "publication.yaml").write_text(
        "document:\n  source_mode: tex\n", encoding="utf-8",
    )

    tex_declared = load_target(tmp_path)

    assert (tex_declared.publication_type, tex_declared.theme, tex_declared.source_mode) == (
        "feature-article", "editorial", "tex",
    )
    assert tex_declared.declared_by == "tex-class-options"

    (tmp_path / "publication.yaml").write_text(
        "document:\n  publication_type: book\n  theme: editorial\n  source_mode: tex\n",
        encoding="utf-8",
    )
    yaml_declared = load_target(tmp_path)

    assert (yaml_declared.publication_type, yaml_declared.theme) == ("book", "editorial")
    assert yaml_declared.declared_by == "publication.yaml"


def test_set_target_persists_verbatim_intent_and_validates_its_schema(tmp_path: Path) -> None:
    (tmp_path / "publication.yaml").write_text("title: Port automation\n", encoding="utf-8")
    request = "  Magazine-style feature on port automation, like the attached QA PDF  "

    state, diagnostics = set_target(
        tmp_path,
        publication_type="feature-article",
        theme="editorial",
        source_mode="tex",
        request=request,
        reference="assets/reference/qa.pdf",
    )

    assert diagnostics == []
    assert (state.publication_type, state.theme, state.source_mode, state.main) == (
        "feature-article", "editorial", "tex", "report.tex",
    )
    assert state.declared_by == "publication.yaml"
    assert state.intent is not None
    assert state.intent["request"] == request
    assert state.intent["decided_by"] == "user-confirmed"
    assert state.intent["visual_reference"] == "assets/reference/qa.pdf"
    assert state.intent["composition_brief"] == "composition-brief.json"
    assert (tmp_path / ".reportkit" / "intent.json").is_file()

    schema = json.loads((REPO / "schemas" / "reportkit-intent.schema.json").read_text(encoding="utf-8"))
    _validate_intent(state.intent)
    try:
        import jsonschema
    except ImportError:
        with pytest.raises(ValueError):
            _validate_intent({**state.intent, "decided_by": "not-a-decision"})
        return
    with pytest.raises(jsonschema.exceptions.ValidationError):
        _validate_intent({**state.intent, "decided_by": "not-a-decision"})
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(state.intent)


def test_aliases_come_from_publication_registry() -> None:
    for publication_type, record in PUBLICATION_TYPES.items():
        expected = (publication_type, record["default_target"]["theme"])
        for alias in record["aliases"]:
            assert resolve_alias(alias) == expected, alias

    assert resolve_alias("Magazine-style feature on port automation") == ("feature-article", "editorial")
    assert resolve_alias("this could be either a book or an equity research note") is None


def test_alias_target_defaults_to_inferred_and_can_be_user_confirmed(tmp_path: Path) -> None:
    state, diagnostics = set_target(tmp_path, publication_type="magazine", source_mode="tex")
    assert diagnostics == []
    assert (state.publication_type, state.theme) == ("feature-article", "editorial")
    assert state.intent is not None
    assert state.intent["alias"] == "magazine"
    assert state.intent["request"] == "magazine"
    assert state.intent["decided_by"] == "agent-inferred"

    state, diagnostics = set_target(
        tmp_path,
        publication_type="magazine",
        source_mode="tex",
        decided_by="user-confirmed",
    )
    assert diagnostics == []
    assert state.intent is not None
    assert state.intent["decided_by"] == "user-confirmed"


def test_target_update_preserves_unrelated_yaml_keys_and_comments(tmp_path: Path) -> None:
    original = (
        "# Project-wide note\n"
        "title: Port automation # keep title comment\n"
        "document:\n"
        "  # keep document comment\n"
        "  publication_type:   # REQUIRED: run `reportkit target set` (see SKILL.md selection table)\n"
        "  theme: default # keep theme comment\n"
        "  class: reportkit # preserve non-target value\n"
        "validation:\n"
        "  require_declared_target: true\n"
        "output:\n"
        "  directory: rendered\n"
    )
    (tmp_path / "publication.yaml").write_text(original, encoding="utf-8")

    state, diagnostics = set_target(
        tmp_path,
        publication_type="book",
        theme="editorial",
        source_mode="markdown",
        request="A book in the editorial look",
    )

    assert diagnostics == []
    updated = (tmp_path / "publication.yaml").read_text(encoding="utf-8")
    assert "# Project-wide note\n" in updated
    assert "title: Port automation # keep title comment\n" in updated
    assert "  # keep document comment\n" in updated
    assert "  theme: editorial # keep theme comment\n" in updated
    assert "  class: reportkit # preserve non-target value\n" in updated
    assert "validation:\n  require_declared_target: true\n" in updated
    assert "output:\n  directory: rendered\n" in updated
    assert "  main:" not in updated
    parsed = load_publication_config(tmp_path / "publication.yaml")
    assert parsed["document"]["publication_type"] == "book"
    assert parsed["document"]["theme"] == "editorial"
    assert parsed["document"]["source_mode"] == "markdown"
    assert state.intent is not None


def test_invalid_type_theme_pair_does_not_write_and_exits_as_validation(tmp_path: Path) -> None:
    (tmp_path / "publication.yaml").write_text("title: Keep me\n", encoding="utf-8")

    state, diagnostics = set_target(
        tmp_path,
        publication_type="book",
        theme="executive",
        source_mode="markdown",
        request="A book in the executive look",
    )

    assert diagnostics[0]["code"] == "RK_TARGET_MISMATCH"
    assert registered_exit_code(diagnostics) == 3
    assert state.declared_by == "default"
    assert (tmp_path / "publication.yaml").read_text(encoding="utf-8") == "title: Keep me\n"
    assert not (tmp_path / ".reportkit" / "intent.json").exists()


def test_feature_article_rejects_markdown_with_tex_remediation(tmp_path: Path) -> None:
    _, diagnostics = set_target(
        tmp_path,
        publication_type="feature-article",
        theme="editorial",
        source_mode="markdown",
        request="A magazine-style feature",
    )

    assert [item["code"] for item in diagnostics] == ["RK_SOURCE_MODE_UNSUPPORTED"]
    assert registered_exit_code(diagnostics) == 3
    assert "--source-mode tex" in diagnostics[0]["remediation"]
    assert not (tmp_path / ".reportkit" / "intent.json").exists()


def test_init_flags_lock_target_and_cli_validation_errors_exit_three(tmp_path: Path) -> None:
    project = tmp_path / "initialized"
    result = subprocess.run(
        [
            str(REPO / "reportkit"), "init", str(project), "--publication-type", "feature-article",
            "--theme", "editorial", "--source-mode", "tex",
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    state = load_target(project)
    assert (state.publication_type, state.theme, state.source_mode) == (
        "feature-article", "editorial", "tex",
    )
    assert state.intent is not None and state.intent["request"] == ""

    invalid = subprocess.run(
        [
            str(REPO / "reportkit"), "target", "set", "--source-root", str(tmp_path),
            "--publication-type", "feature-article", "--theme", "editorial",
            "--source-mode", "markdown", "--json",
        ],
        capture_output=True, text=True, check=False,
    )
    assert invalid.returncode == 3
    assert json.loads(invalid.stdout)["diagnostics"][0]["code"] == "RK_SOURCE_MODE_UNSUPPORTED"


def test_resolve_document_records_declaration_without_changing_values() -> None:
    resolved_default = resolve_document({})
    assert resolved_default["declared_by"] == "default"
    assert resolved_default["publication_type"] == "technical-report"
    assert resolved_default["theme"] == "default"
    assert resolved_default["source_mode"] == "markdown"

    resolved_declared = resolve_document({"document": {"publication_type": "feature-article", "theme": "editorial"}})
    assert resolved_declared["declared_by"] == "publication.yaml"
    assert resolved_declared["publication_type"] == "feature-article"
    assert resolved_declared["theme"] == "editorial"
