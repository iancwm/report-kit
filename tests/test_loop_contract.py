"""Wave 0 contract freeze for the agent reasoning loop.

Agent reasoning loop spec: docs/superpowers/specs/2026-09-28-reportkit-agent-reasoning-loop-spec.md
Plan §3: docs/superpowers/plans/2026-09-28-reportkit-agent-reasoning-loop-implementation-plan.md

These tests pin the shared interfaces the Wave 1 lanes code against: the
command contract, the diagnostic codes, the publication-registry fields, the
schemas, and the stub hook modules' public signatures.
"""
from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path
import subprocess

import pytest

from adapters.openai import build_tool_bundle
from reportkit.cli import build_parser
from reportkit.diagnostics import DIAGNOSTIC_CODES, DIAGNOSTIC_DEFINITIONS, make_diagnostic, registered_exit_code
from reportkit.publications import PUBLICATION_TYPES, SOURCE_MODE_VALUES, check_publication_registry
from reportkit.registry import COMMAND_CONTRACT


REPO = Path(__file__).resolve().parents[1]
LOOP_CODES = (
    "RK_TARGET_UNDECLARED", "RK_TARGET_IMPLICIT", "RK_TARGET_MISMATCH", "RK_ENGINE_DOWNGRADE",
    "RK_SOURCE_MODE_UNSUPPORTED", "RK_PRIMITIVE_OFF_TARGET", "RK_LOCAL_STYLE", "RK_INTENT_MISMATCH",
)


def _subcommands(parser) -> dict:
    return next(action for action in parser._actions if action.dest in {"command", "target_command"}).choices


# -- command contract ---------------------------------------------------------

def test_new_commands_are_in_the_contract_and_the_parser() -> None:
    parsers = _subcommands(build_parser())
    for name in ("target", "status", "review", "audit", "audit-editorial"):
        assert name in COMMAND_CONTRACT, name
        assert name in parsers, name
    assert set(COMMAND_CONTRACT["target"]["subcommands"]) == {"set", "show"}
    assert COMMAND_CONTRACT["audit"]["aliases"] == ["audit-editorial"]
    assert COMMAND_CONTRACT["audit-editorial"]["alias_of"] == "audit"
    # The alias is the same parser, so both spellings keep one contract.
    assert parsers["audit"] is parsers["audit-editorial"]
    assert COMMAND_CONTRACT["audit"]["summary"] == COMMAND_CONTRACT["audit-editorial"]["summary"]
    assert {"--publication-type", "--theme", "--source-mode"} <= set(COMMAND_CONTRACT["init"]["arguments"])


def test_command_group_contract_covers_every_subcommand_option() -> None:
    parsers = _subcommands(build_parser())
    for name, record in COMMAND_CONTRACT.items():
        for sub_name, sub_record in (record.get("subcommands") or {}).items():
            subparser = _subcommands(parsers[name])[sub_name]
            actual = {
                option for action in subparser._actions for option in action.option_strings
                if option not in {"-h", "--help"}
            }
            assert actual == set(sub_record["arguments"]), f"{name} {sub_name}"
            assert subparser.description == sub_record["summary"]


def test_target_set_arguments_match_the_plan() -> None:
    assert COMMAND_CONTRACT["target"]["subcommands"]["set"]["arguments"] == [
        "--source-root", "--publication-type", "--theme", "--source-mode", "--request", "--reference",
        "--decided-by", "--json",
    ]
    assert COMMAND_CONTRACT["status"]["arguments"] == ["--source-root", "--json"]
    assert COMMAND_CONTRACT["review"]["arguments"] == ["pdf", "--source-root", "--visual-review", "--json"]


def test_openai_bundle_exposes_the_loop_tools() -> None:
    checked_in = json.loads((REPO / "adapters" / "openai" / "tools.json").read_text())
    assert checked_in == build_tool_bundle()
    names = {tool["name"] for tool in checked_in["tools"]}
    assert {
        "reportkit_target_set", "reportkit_target_show", "reportkit_status", "reportkit_review",
        "reportkit_audit", "reportkit_audit_editorial",
    } <= names


# -- diagnostics --------------------------------------------------------------

def test_loop_diagnostic_kinds_are_registered() -> None:
    assert DIAGNOSTIC_DEFINITIONS["target_contract"]["severity"] == "error"
    assert DIAGNOSTIC_DEFINITIONS["off_target"]["severity"] == "warning"


@pytest.mark.parametrize("code", LOOP_CODES)
def test_every_loop_code_resolves_through_make_diagnostic(code: str) -> None:
    registered = DIAGNOSTIC_CODES[code]
    diagnostic = make_diagnostic(registered["type"], "message", code=code)
    assert diagnostic["code"] == code
    assert diagnostic["type"] == registered["type"]
    assert diagnostic["severity"] == registered["severity"]
    assert diagnostic["remediation"] == registered["remediation"]
    assert "reportkit" in diagnostic["remediation"] or "setup_tex.sh" in diagnostic["remediation"]
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REPO / "schemas" / "reportkit-diagnostic.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(diagnostic)


def test_loop_code_severity_and_exit_codes() -> None:
    assert DIAGNOSTIC_CODES["RK_TARGET_IMPLICIT"]["severity"] == "warning"
    for code in ("RK_TARGET_UNDECLARED", "RK_TARGET_MISMATCH", "RK_SOURCE_MODE_UNSUPPORTED"):
        assert DIAGNOSTIC_CODES[code]["exit_code"] == 3
    assert DIAGNOSTIC_CODES["RK_ENGINE_DOWNGRADE"]["exit_code"] == 5
    undeclared = make_diagnostic("target_contract", "x", code="RK_TARGET_UNDECLARED")
    downgrade = make_diagnostic("environment_error", "x", code="RK_ENGINE_DOWNGRADE")
    implicit = make_diagnostic("target_contract", "x", code="RK_TARGET_IMPLICIT")
    assert registered_exit_code([undeclared]) == 3
    assert registered_exit_code([undeclared, downgrade]) == 5
    assert registered_exit_code([implicit]) is None


def test_engine_downgrade_remediation_never_suggests_changing_the_theme() -> None:
    remediation = DIAGNOSTIC_CODES["RK_ENGINE_DOWNGRADE"]["remediation"].casefold()
    assert "lualatex" in remediation and "setup_tex.sh" in remediation
    assert "keep the declared theme" in remediation
    for suggestion in ("change the theme", "remove the theme", "theme=default", "switch theme"):
        assert suggestion not in remediation


def test_explicit_remediation_still_wins_over_the_registered_default() -> None:
    diagnostic = make_diagnostic("target_contract", "x", code="RK_TARGET_MISMATCH", remediation="custom")
    assert diagnostic["remediation"] == "custom"


# -- publication registry -----------------------------------------------------

@pytest.mark.parametrize("name", sorted(PUBLICATION_TYPES))
def test_every_publication_type_declares_loop_fields(name: str) -> None:
    record = PUBLICATION_TYPES[name]
    assert set(record["source_modes"]) == set(SOURCE_MODE_VALUES)
    for mode, value in record["source_modes"].items():
        assert value in SOURCE_MODE_VALUES[mode]
    assert record["aliases"] and all(isinstance(alias, str) for alias in record["aliases"])
    assert (REPO / record["canonical_example"]).is_dir()
    assert record["composition_brief_example"].startswith(record["canonical_example"])


def test_feature_article_requires_tex_and_names_the_magazine_aliases() -> None:
    record = PUBLICATION_TYPES["feature-article"]
    assert record["source_modes"] == {"tex": "required", "markdown": "opening-only"}
    assert {"magazine", "feature", "editorial article"} <= set(record["aliases"])


def test_registry_integrity_check_covers_the_loop_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    assert check_publication_registry(REPO) == []
    broken = {**PUBLICATION_TYPES["book"], "source_modes": {"tex": "supported"}, "canonical_example": "missing/"}
    monkeypatch.setitem(PUBLICATION_TYPES, "book", broken)
    errors = check_publication_registry(REPO)
    assert any("source_modes" in error for error in errors)
    assert any("canonical_example" in error for error in errors)


# -- schemas ------------------------------------------------------------------

def test_loop_schemas_are_valid_and_versioned() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    for name in ("intent", "status", "review", "build-report", "diagnostic-envelope", "context", "context-slice"):
        schema = json.loads((REPO / "schemas" / f"reportkit-{name}.schema.json").read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
    report = json.loads((REPO / "schemas" / "reportkit-build-report.schema.json").read_text())
    assert report["properties"]["schema_version"] == {"const": 4}
    assert {"declared_by", "matches_intent"} <= set(report["properties"]["selection"]["properties"])
    for name in ("diagnostic-envelope", "context", "context-slice", "status"):
        schema = json.loads((REPO / "schemas" / f"reportkit-{name}.schema.json").read_text())
        assert {"target", "next_step"} <= set(schema["properties"]), name


def test_intent_schema_accepts_the_spec_example() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REPO / "schemas" / "reportkit-intent.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate({
        "schema_version": "1.0.0",
        "request": "Magazine-style feature on port automation, like the attached QA PDF",
        "publication_type": "feature-article",
        "theme": "editorial",
        "source_mode": "tex",
        "visual_reference": "assets/reference/qa.pdf",
        "composition_brief": "composition-brief.json",
        "decided_by": "user-confirmed",
        "locked_at": "2026-09-28T10:00:00Z",
    })


# -- stub hook modules --------------------------------------------------------

FROZEN_SIGNATURES = {
    "reportkit.target": {
        "load_target": ["source_root"],
        "set_target": ["source_root", "publication_type", "theme", "source_mode", "request", "reference", "decided_by"],
        "resolve_alias": ["text"],
        "target_gate": ["state"],
    },
    "reportkit.loop": {
        "target_line": ["state"],
        "target_payload": ["state"],
        "next_step": ["command", "state", "outcome"],
    },
    "reportkit.tex_target": {
        "read_class_options": ["tex"],
        "tex_gates": ["state", "tex"],
        "engine_gate": ["state", "requested_engine"],
    },
    "reportkit.primitive_targets": {"role_for": ["primitive_name", "kind", "publication_type"]},
    "reportkit.authoring_templates": {"document_template": ["publication_type", "theme"]},
    "reportkit.composition_audit": {
        "audit_source": ["tex", "brief", "state"],
        "find_brief": ["source_root", "state"],
    },
    "reportkit.review": {
        "write_review": ["pdf", "state", "visual_review"],
        "read_review": ["source_root"],
        "compare_intent": ["selection", "state"],
    },
    "reportkit.status": {"collect_status": ["source_root"]},
}


@pytest.mark.parametrize("module_name", sorted(FROZEN_SIGNATURES))
def test_stub_modules_expose_the_frozen_signatures(module_name: str) -> None:
    module = importlib.import_module(module_name)
    for function, parameters in FROZEN_SIGNATURES[module_name].items():
        assert list(inspect.signature(getattr(module, function)).parameters) == parameters, f"{module_name}.{function}"


def test_frozen_data_members() -> None:
    from reportkit.composition_audit import ROLE_REGISTRIES, RoleRegistry
    from reportkit.loop import LOOP_STEPS
    from reportkit.primitive_targets import ROLE_TABLE, ROLES
    from reportkit.target import TargetState

    assert [step.name for step in LOOP_STEPS] == [
        "SELECT", "LOCK", "SCAFFOLD", "AUTHOR", "CHECK", "BUILD", "REVIEW", "DELIVER",
    ]
    assert ROLES == ("native", "allowed", "discouraged", "absent")
    assert isinstance(ROLE_TABLE, dict) and isinstance(ROLE_REGISTRIES, dict)
    assert list(inspect.signature(RoleRegistry).parameters) == [
        "required_roles", "role_patterns", "manual_review", "local_style_forbidden",
    ]
    assert list(inspect.signature(TargetState).parameters)[:8] == [
        "publication_type", "theme", "renderer", "source_mode", "main", "declared_by", "intent", "require_declared",
    ]


def test_load_target_distinguishes_declared_from_defaulted(tmp_path: Path) -> None:
    from reportkit.target import load_target

    legacy = load_target(tmp_path)
    assert (legacy.publication_type, legacy.theme, legacy.declared_by) == ("technical-report", "default", "default")
    assert legacy.require_declared is False
    (tmp_path / "publication.yaml").write_text(
        "title: Loop\ndocument:\n  publication_type: feature-article\n  theme: editorial\n  source_mode: tex\n"
        "validation:\n  require_declared_target: true\n",
        encoding="utf-8",
    )
    declared = load_target(tmp_path)
    assert (declared.publication_type, declared.theme, declared.source_mode) == ("feature-article", "editorial", "tex")
    assert declared.declared_by == "publication.yaml"
    assert declared.require_declared is True
    assert declared.intent_path == tmp_path / ".reportkit" / "intent.json"


def test_authoring_template_stub_is_the_previous_skeleton() -> None:
    from reportkit.authoring_templates import document_template

    assert document_template("feature-article", "editorial") == (
        "\\documentclass[theme=editorial,publication-type=feature-article]{reportkit}\n"
        "\\title{Contract acceptance}\n\\author{ReportKit}\n"
        "\\begin{document}\n\\maketitle\n{{body}}\n\\end{document}\n"
    )


# -- CLI wiring ---------------------------------------------------------------

def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(REPO / "reportkit"), *arguments], capture_output=True, text=True)


def test_target_show_and_status_use_the_common_envelope(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    envelope = json.loads((REPO / "schemas" / "reportkit-diagnostic-envelope.schema.json").read_text())
    status_schema = json.loads((REPO / "schemas" / "reportkit-status.schema.json").read_text())
    shown = _run("target", "show", "--source-root", str(tmp_path), "--json")
    assert shown.returncode == 0, shown.stderr
    payload = json.loads(shown.stdout)
    jsonschema.Draft202012Validator(envelope).validate(payload)
    assert payload["target_state"]["declared_by"] == "default"
    status = _run("status", "--source-root", str(tmp_path), "--json")
    assert status.returncode == 0, status.stderr
    status_payload = json.loads(status.stdout)
    jsonschema.Draft202012Validator(envelope).validate(status_payload)
    jsonschema.Draft202012Validator(status_schema).validate(status_payload)


def test_target_set_refuses_a_source_root_inside_the_engine() -> None:
    result = _run("target", "set", "--source-root", str(REPO / "publication_pipeline" / "example_publication"),
                  "--publication-type", "book", "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "RK_TARGET_SOURCE_ROOT"


def test_review_writes_build_review_json(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    pdf = tmp_path / "build" / "combined" / "report.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n")
    result = _run("review", str(pdf), "--source-root", str(tmp_path), "--visual-review", "unavailable", "--json")
    assert result.returncode == 0, result.stderr
    record = json.loads((tmp_path / "build" / "review.json").read_text())
    assert record["visual_review"] == "unavailable"
    schema = json.loads((REPO / "schemas" / "reportkit-review.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(record)


def test_review_without_a_pdf_is_a_configuration_error(tmp_path: Path) -> None:
    result = _run("review", "--source-root", str(tmp_path), "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["diagnostics"][0]["code"] == "RK_REVIEW_PDF_MISSING"


def test_audit_and_its_alias_share_one_handler() -> None:
    example = REPO / "latex_templates" / "examples" / "editorial-feature"
    for command in ("audit", "audit-editorial"):
        result = _run(command, str(example / "report.tex"), "--brief", str(example / "editorial-brief.json"), "--json")
        assert result.returncode == 0, (command, result.stdout)
        assert json.loads(result.stdout)["passed"] is True


def test_emit_always_adds_loop_fields_and_preserves_hook_overrides(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from reportkit import cli
    from reportkit.target import load_target

    state = load_target(REPO / "publication_pipeline" / "example_publication")
    cli._emit({"passed": True, "diagnostics": []}, state, "check", True)
    payload = json.loads(capsys.readouterr().out)
    assert {"passed", "diagnostics", "target", "next_step"} <= set(payload)
    assert payload["target"]["line"].startswith("TARGET structure=technical-report look=default")
    assert payload["next_step"]["command"] == "reportkit build --json"
    monkeypatch.setattr(cli, "target_payload", lambda _state: {"publication_type": "book"})
    monkeypatch.setattr(cli, "target_line", lambda _state: "TARGET book/default/paged")
    monkeypatch.setattr(cli, "next_step", lambda *_args: {"command": "reportkit build --json", "reason": "check passed"})
    cli._emit({"passed": True, "diagnostics": []}, state, "check", True)
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"] == {"publication_type": "book"}
    assert payload["next_step"]["command"] == "reportkit build --json"
    cli._emit({"passed": True, "target": "/tmp/project"}, state, "init", True)
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"] == "/tmp/project"
    assert payload["publication_target"] == {"publication_type": "book"}
    cli._emit({"passed": True}, state, "check", False, human=lambda: print("PASS: body"))
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "TARGET book/default/paged"
    assert lines[1] == "PASS: body"
    assert lines[-1] == "next step: reportkit build --json (check passed)"
