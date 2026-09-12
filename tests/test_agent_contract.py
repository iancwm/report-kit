from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]

from reportkit.cli import _contract_diagnostics, build_parser  # noqa: E402
from reportkit.context import build_context  # noqa: E402
from reportkit.diagnostics import DIAGNOSTIC_DEFINITIONS, make_diagnostic  # noqa: E402
from reportkit.documentation import check_documentation  # noqa: E402
from reportkit.latex import tex_escape as shared_tex_escape  # noqa: E402
from reportkit.registry import (  # noqa: E402
    COMMAND_CONTRACT,
    ContractError,
    _latex_primitives,
    _merge_record,
    generate_registry,
    parse_xparse_signature,
    _python_signature,
)
from reportkit.toolchain import load_toolchain_lock, toolchain_fingerprint  # noqa: E402
from reportkit.version import REPORTKIT_VERSION  # noqa: E402
from publication_build import _reproducible_datetime, run_limited, tex_escape as pipeline_tex_escape  # noqa: E402
from publication_validation import validate_publication  # noqa: E402
from scripts.contract_acceptance import acceptance_source, run_acceptance  # noqa: E402


def test_xparse_signature_handles_nested_defaults_and_supported_tokens() -> None:
    parsed = parse_xparse_signature(r"O{{inner={value}}} m o s")
    assert [value["specifier"] for value in parsed] == ["O", "m", "o", "s"]
    assert parsed[0]["default"] == "{inner={value}}"
    assert sum(value["required"] for value in parsed) == 1


def test_xparse_signature_rejects_unknown_tokens() -> None:
    with pytest.raises(ContractError, match="unsupported xparse"):
        parse_xparse_signature("r()")


@pytest.mark.parametrize("character", list(r"\&%$#_{}~^"))
def test_all_latex_metacharacters_use_one_shared_escaper(character: str) -> None:
    assert pipeline_tex_escape is shared_tex_escape
    assert pipeline_tex_escape(character) == shared_tex_escape(character)


def test_python_signature_is_extracted_from_ast() -> None:
    node = ast.parse("def chart(data, scale=1, *, title=None, required): pass").body[0]
    signature, arguments = _python_signature(node)
    assert signature == "data, scale=1, *, title=None, required"
    assert [(item["name"], item["required"]) for item in arguments] == [
        ("data", True), ("scale", False), ("title", False), ("required", True),
    ]


def test_every_in_tree_xparse_specifier_is_supported() -> None:
    registry = generate_registry(REPO, strict=True)
    found = {
        argument["specifier"]
        for group in registry["primitives"].values()
        for record in group.values()
        for argument in record["arguments"]
        if argument["specifier"] in {"m", "O", "o", "s"}
    }
    assert found == {"m", "O", "o"}
    assert parse_xparse_signature("s")[0]["specifier"] == "s"


def test_registry_is_complete_and_preserves_legacy_inventory() -> None:
    registry = generate_registry(REPO, strict=True)
    assert {kind: len(records) for kind, records in registry["primitives"].items()} == {
        "callout": 14, "figure": 19, "chart": 13, "composition": 17, "command": 62,
    }
    assert len(registry["figures"]) == 19
    assert len(registry["callouts"]["public"]) == 10
    assert len(registry["charts"]) == 11
    assert "risk_reward_chart" in registry["primitives"]["chart"]
    assert "donut_chart" in registry["primitives"]["chart"]
    assert "pd.Series | pd.DataFrame" in registry["primitives"]["chart"]["timeseries"]["source_signature"]
    assert "RKLink" in registry["primitives"]["command"]
    assert registry["primitives"]["command"]["RKLink"]["source"]["file"] == "latex_templates/reportkit-core.sty"
    assert registry["primitives"]["figure"]["reportflow"]["contract_pointer"] == "#/capabilities/primitives/figure/reportflow"


def test_missing_adjacent_metadata_is_a_contract_error(tmp_path: Path) -> None:
    path = tmp_path / "public.sty"
    path.write_text(r"\NewDocumentEnvironment{example}{m}{}{}" + "\n", encoding="utf-8")
    records, errors = _latex_primitives(path, tmp_path)
    assert records[0]["name"] == "example"
    assert any("no adjacent contract metadata" in error for error in errors)


def test_private_xparse_declaration_requires_explicit_internal_marker(tmp_path: Path) -> None:
    path = tmp_path / "private.sty"
    path.write_text(r"\NewDocumentCommand{\rk@private}{m}{}" + "\n", encoding="utf-8")
    records, errors = _latex_primitives(path, tmp_path)
    assert records == []
    assert any("reportkit-contract: internal" in error for error in errors)

    path.write_text(
        "% reportkit-contract: internal\n" + r"\NewDocumentCommand{\rk@private}{m}{}" + "\n",
        encoding="utf-8",
    )
    records, errors = _latex_primitives(path, tmp_path)
    assert records == []
    assert errors == []


def test_conflicting_xparse_default_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "conflict.sty"
    path.write_text(
        "% <reportkit-contract>\n"
        "% {\"kind\":\"command\",\"arguments\":[{\"name\":\"value\",\"default\":\"other\"}],\"example\":\"\\\\example\",\"stability\":\"stable\",\"since\":\"1.0.0\"}\n"
        "% </reportkit-contract>\n"
        r"\NewDocumentCommand{\example}{O{source}}{}" + "\n",
        encoding="utf-8",
    )
    _, errors = _latex_primitives(path, tmp_path)
    assert any("default disagrees" in error for error in errors)


def test_duplicate_primitive_with_conflicting_signature_is_reported() -> None:
    primitives = {kind: {} for kind in ("callout", "figure", "chart", "composition", "command")}
    errors: list[str] = []
    base = {
        "name": "example", "kind": "command", "available_in": {
            "publication_types": ["technical-report"], "themes": ["default"], "renderers": ["paged"],
        },
    }
    _merge_record(primitives, {**base, "signature": "m"}, errors)
    _merge_record(primitives, {**base, "signature": "o"}, errors)
    assert errors == ["duplicate primitive 'example' has conflicting signatures"]


def test_context_is_versioned_filterable_and_legacy_compatible() -> None:
    context = build_context(REPO, kinds=["chart"], publication_type="equity-research")
    assert context["schema_version"] == "1.0.0"
    assert context["contract_version"] == "1.1.0"
    assert context["reportkit_version"] == "1.9.3"
    assert context["selection"] == {
        "publication_type": "equity-research", "requested_theme": "institutional-research",
        "requested_name": "institutional-research",
        "theme": "institutional-research", "alias_of": None, "renderer": "paged",
        "class": "reportkit", "template": "publication-template.tex", "writer": "latex",
        "engine": "lualatex", "paper": "letter", "canvas": None,
        "geometry": {"kind": "paper", "papers": ["a4", "letter"], "paper": "letter"},
        "accessibility": {
            "pdf_metadata": "supported", "catalog_language": "supported", "bookmarks": "supported",
            "meaningful_links": "supported", "diagram_actual_text": "supported",
            "tagged_pdf": "unsupported",
            "tagged_pdf_reason": "The pinned LaTeX format has not yet passed the documented tagging spike.",
        },
        "common_package": "reportkit-theme-institutional-research",
        "renderer_adapter": "reportkit-theme-institutional-research",
        "publication_package": "reportkit-equity-research", "brand_overrides": False,
        "language_support": {
            "verified": ["en"], "metadata_only": ["vi"],
            "scripts": {"verified": ["Latn"], "metadata_only": []}, "rtl": "unsupported",
        },
        "profile": "draft",
    }
    assert "theme=institutional-research,publication-type=equity-research" in context["capabilities"]["authoring"]["document_template"]
    assert "apply_theme('institutional-research')" in context["capabilities"]["authoring"]["chart_prelude"]
    assert set(context["capabilities"]["primitives"]) == {"chart"}
    assert isinstance(context["commands"]["context"], str)
    assert context["components"]["figures"] == []
    records = context["capabilities"]["primitives"]["chart"].values()
    assert all(record["available_in"]["publication_types"] == ["equity-research"] for record in records)
    assert all(record["available_in"]["themes"] == ["institutional-research"] for record in records)


def test_context_and_toolchain_match_published_schemas() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    context_schema = json.loads((REPO / "schemas" / "reportkit-context.schema.json").read_text())
    toolchain_schema = json.loads((REPO / "schemas" / "reportkit-toolchain.schema.json").read_text())
    validator = jsonschema.Draft202012Validator(context_schema)
    validator.validate(build_context(REPO))
    validator.validate(build_context(
        REPO, publication_type="equity-research", theme="institutional-research", kinds=["callout", "chart"],
    ))
    jsonschema.Draft202012Validator(toolchain_schema).validate(load_toolchain_lock(REPO))


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("pdflatex", "pandoc")),
    reason="authoritative build-report validation runs in the pinned toolchain",
)
def test_full_build_emits_schema_v3_report_and_lock(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    source = tmp_path / "publication"
    output = tmp_path / "build"
    shutil.copytree(REPO / "publication_pipeline" / "example_publication", source)
    result = subprocess.run(
        [
            str(REPO / "reportkit"), "build", "--source-root", str(source),
            "--output-root", str(output), "--json",
        ],
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0, payload
    report = payload["report"]
    schema = json.loads((REPO / "schemas" / "reportkit-build-report.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(report)
    lock = json.loads((source / "reportkit.lock").read_text())
    assert lock["schema_version"] == 2
    assert lock["toolchain_fingerprint"] == toolchain_fingerprint(load_toolchain_lock(REPO))


def test_context_catalog_contains_only_the_current_publication_matrix() -> None:
    capabilities = build_context(REPO)["capabilities"]
    assert set(capabilities["publication_types"]) == {"technical-report", "equity-research"}
    assert capabilities["publication_types"]["technical-report"]["themes"] == ["default", "technical"]
    assert capabilities["publication_types"]["equity-research"]["themes"] == ["institutional-research"]
    assert set(capabilities["renderers"]) == {"paged"}
    assert set(capabilities["themes"]) == {"default", "technical", "institutional-research"}
    assert all(theme["language_support"]["rtl"] == "unsupported" for theme in capabilities["themes"].values())
    assert all(theme["language_support"]["scripts"]["verified"] == ["Latn"] for theme in capabilities["themes"].values())


def test_diagnostic_records_and_envelopes_match_published_schemas() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    diagnostic_schema = json.loads((REPO / "schemas" / "reportkit-diagnostic.schema.json").read_text())
    envelope_schema = json.loads((REPO / "schemas" / "reportkit-diagnostic-envelope.schema.json").read_text())
    record = make_diagnostic("configuration_error", "Example failure")
    jsonschema.Draft202012Validator(diagnostic_schema).validate(record)
    jsonschema.Draft202012Validator(envelope_schema).validate({
        "schema_version": "1.0.0", "passed": False, "diagnostics": [record],
    })


def test_all_diagnostic_definitions_have_actionable_remediation() -> None:
    assert DIAGNOSTIC_DEFINITIONS
    for kind, definition in DIAGNOSTIC_DEFINITIONS.items():
        assert definition["code"].startswith("RK_")
        assert definition["type"] == kind
        assert definition["docs"] == "references/agent-contract.md#diagnostic-envelope-and-exits"
        assert definition["severity"] in {"error", "warning", "info"}
        assert len(definition["remediation"].split()) >= 4, kind
        record = make_diagnostic(kind, "Example")
        assert record["code"].startswith("RK_")
        assert record["remediation"]


def test_generated_documentation_is_current() -> None:
    assert check_documentation(REPO, registry=generate_registry(REPO)) == []


def test_every_chart_contract_example_executes_in_isolation() -> None:
    pd = pytest.importorskip("pandas")
    np = pytest.importorskip("numpy")
    import reportkit_viz as rkv

    for record in generate_registry(REPO, strict=True)["primitives"]["chart"].values():
        namespace = {"pd": pd, "np": np, "rkv": rkv}
        exec(record["example"], namespace)
        if "fig" in namespace:
            rkv.plt.close(namespace["fig"])


def test_contract_only_acceptance_source_uses_emitted_examples() -> None:
    context = build_context(
        REPO, publication_type="technical-report", theme="default",
        kinds=["callout", "figure", "chart"],
    )
    source = acceptance_source(context)
    assert context["capabilities"]["primitives"]["callout"]["principle"]["example"] in source
    assert context["capabilities"]["primitives"]["figure"]["reportflow"]["example"] in source
    assert "contract-chart.pdf" in source


@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="pdflatex not on PATH")
def test_contract_acceptance_document_has_no_blocking_diagnostics(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    code, payload = run_acceptance(tmp_path)
    assert code == 0, json.dumps(payload, indent=2, sort_keys=True)
    assert not any(item["blocking"] for item in payload["diagnostics"])


def test_command_contract_covers_every_public_cli_option() -> None:
    parser = build_parser()
    subcommands = next(action for action in parser._actions if action.dest == "command").choices
    for name, subparser in subcommands.items():
        actual = {
            option for action in subparser._actions for option in action.option_strings
            if option not in {"-h", "--help"}
        }
        declared = {value for value in COMMAND_CONTRACT[name]["arguments"] if value.startswith("-")}
        assert actual == declared, name
        assert subparser.description == COMMAND_CONTRACT[name]["summary"]


def test_contract_major_mismatch_is_structured_exit_two() -> None:
    result = subprocess.run(
        [str(REPO / "reportkit"), "check", "--source-root", str(REPO / "publication_pipeline" / "example_publication"),
         "--contract-version", "2.0.0", "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["diagnostics"][0]["code"] == "RK_CONTRACT_VERSION_MAJOR"


def test_newer_same_major_contract_is_structured_exit_two() -> None:
    result = subprocess.run(
        [str(REPO / "reportkit"), "check", "--source-root", str(REPO / "publication_pipeline" / "example_publication"),
         "--contract-version", "1.2.0", "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["passed"] is False
    assert payload["diagnostics"][0]["code"] == "RK_CONTRACT_VERSION_NEWER"


def test_older_same_major_contract_warns_and_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reportkit.cli.CONTRACT_VERSION", "1.2.0")
    diagnostics, exit_code = _contract_diagnostics("1.1.0")
    assert exit_code is None
    assert diagnostics[0]["code"] == "RK_CONTRACT_VERSION_STALE"
    assert diagnostics[0]["severity"] == "warning"


@pytest.mark.parametrize(
    ("arguments", "expected_exit"),
    [
        (["context", "--json"], 0),
        (["doctor", "--json"], 0),
        (["docs", "--check", "--json"], 0),
        (["check", "--json"], 0),
        (["analyse-history", "--history-dir", "/path/that/does/not/exist", "--json"], 0),
        (["diagnose", "/path/that/does/not/exist.log", "--json"], 2),
        (["inspect", "/path/that/does/not/exist.pdf", "--json"], 2),
        (["package", "--build-dir", "/path/that/does/not/exist", "--json"], 2),
        (["build", "--source-root", "/path/that/does/not/exist", "--json"], 3),
    ],
)
def test_every_json_capable_command_uses_the_common_envelope(arguments: list[str], expected_exit: int) -> None:
    result = subprocess.run([str(REPO / "reportkit"), *arguments], capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert result.returncode == expected_exit
    assert {"passed", "schema_version", "diagnostics", "issues", "errors"} <= payload.keys()
    jsonschema = pytest.importorskip("jsonschema")
    envelope_schema = json.loads((REPO / "schemas" / "reportkit-diagnostic-envelope.schema.json").read_text())
    diagnostic_schema = json.loads((REPO / "schemas" / "reportkit-diagnostic.schema.json").read_text())
    jsonschema.Draft202012Validator(envelope_schema).validate(payload)
    for diagnostic in payload["diagnostics"]:
        jsonschema.Draft202012Validator(diagnostic_schema).validate(diagnostic)


def test_json_cli_usage_error_is_a_structured_exit_two() -> None:
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--compile-timeout-seconds", "0", "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["diagnostics"][0]["code"] == "RK_CLI_USAGE"


def test_invalid_context_filter_has_deterministic_candidate() -> None:
    result = subprocess.run(
        [str(REPO / "reportkit"), "context", "--publication-type", "eqity-research", "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["diagnostics"][0]["candidates"] == ["equity-research"]


def test_publication_validation_rejects_tex_path_escape(tmp_path: Path) -> None:
    (tmp_path / "manuscript").mkdir()
    (tmp_path / "fragments").mkdir()
    (tmp_path / "manuscript" / "order.txt").write_text("01.md\n")
    (tmp_path / "manuscript" / "01.md").write_text("[[REPORTKIT-VISUAL:fig:escape]]\n")
    (tmp_path / "fragments" / "fig-escape.tex").write_text(
        "\\begin{diagram}[label={fig:escape}]\n\\input{../../secret}\n\\end{diagram}\n"
    )
    result = validate_publication(tmp_path)
    assert not result.ok
    assert any(item["type"] == "security_violation" for item in result.diagnostics)


def test_publication_validation_rejects_unbraced_tex_path_and_spaced_write18(tmp_path: Path) -> None:
    (tmp_path / "manuscript").mkdir()
    (tmp_path / "fragments").mkdir()
    (tmp_path / "manuscript" / "order.txt").write_text("01.md\n")
    (tmp_path / "manuscript" / "01.md").write_text("[[REPORTKIT-VISUAL:fig:escape]]\n")
    (tmp_path / "fragments" / "fig-escape.tex").write_text(
        "\\begin{diagram}[label={fig:escape}]\n"
        "\\input ../../secret\n"
        "\\immediate\\write 18{forbidden}\n"
        "\\end{diagram}\n"
    )
    result = validate_publication(tmp_path)
    assert {item["code"] for item in result.diagnostics} >= {
        "RK_VALIDATION_TEX_PATH_ESCAPE", "RK_VALIDATION_SHELL_ESCAPE",
    }


def test_publication_validation_rejects_tex_output_escape(tmp_path: Path) -> None:
    (tmp_path / "manuscript").mkdir()
    (tmp_path / "fragments").mkdir()
    (tmp_path / "manuscript" / "order.txt").write_text("01.md\n")
    (tmp_path / "manuscript" / "01.md").write_text("[[REPORTKIT-VISUAL:fig:escape]]\n")
    (tmp_path / "fragments" / "fig-escape.tex").write_text(
        "\\begin{diagram}[label={fig:escape}]\n\\openout\\payload=../../escape.txt\n\\end{diagram}\n"
    )
    result = validate_publication(tmp_path)
    assert any(item["code"] == "RK_VALIDATION_TEX_OUTPUT_PATH_ESCAPE" for item in result.diagnostics)


def test_publication_validation_rejects_markdown_asset_escape(tmp_path: Path) -> None:
    (tmp_path / "manuscript").mkdir()
    (tmp_path / "fragments").mkdir()
    (tmp_path / "manuscript" / "order.txt").write_text("01.md\n")
    (tmp_path / "manuscript" / "01.md").write_text("![escape](../../secret.png)\n")
    result = validate_publication(tmp_path)
    assert any(item["code"] == "RK_VALIDATION_ASSET_PATH_ESCAPE" for item in result.diagnostics)


def test_no_process_invocation_enables_shell_escape() -> None:
    for path in [*REPO.glob("python_scripts/**/*.py"), *REPO.glob("publication_pipeline/**/*.py"), *REPO.glob("scripts/*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if isinstance(node.args[0], (ast.List, ast.Tuple)):
                values = {value.value for value in node.args[0].elts if isinstance(value, ast.Constant)}
                assert not values.intersection({
                    "-shell-escape", "--shell-escape", "-enable-write18", "--enable-write18",
                }), path


def test_limited_runner_refuses_shell_escape(tmp_path: Path) -> None:
    for flag in ("-shell-escape", "--shell-escape=true", "-enable-write18"):
        with pytest.raises(ValueError, match="shell escape"):
            run_limited(["pdflatex", flag, "report.tex"], cwd=tmp_path, timeout=1, memory_limit_mb=128)


def test_limited_runner_enforces_wall_clock_timeout(tmp_path: Path) -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        run_limited(
            [sys.executable, "-c", "while True: pass"], cwd=tmp_path,
            timeout=0.05, memory_limit_mb=256, capture_output=True, text=True,
        )


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="RLIMIT_AS is authoritative in the pinned Linux toolchain")
def test_limited_runner_enforces_address_space_limit(tmp_path: Path) -> None:
    result = run_limited(
        [sys.executable, "-c", "bytearray(512 * 1024 * 1024)"], cwd=tmp_path,
        timeout=5, memory_limit_mb=256, capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_invalid_resource_environment_override_is_structured_exit_two() -> None:
    env = {**os.environ, "REPORTKIT_MEMORY_LIMIT_MB": "invalid"}
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--json"], capture_output=True, text=True, env=env,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["diagnostics"][0]["code"] == "RK_CLI_USAGE"


def test_pdf_visible_build_date_uses_fixed_source_date_epoch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "999999999")
    assert _reproducible_datetime().timestamp() == 1


def test_section_build_rejects_path_escape_before_conversion() -> None:
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--mode", "section", "--section", "../escape.md", "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 2
    assert payload["diagnostics"][0]["type"] == "configuration_error"


def test_toolchain_fingerprint_and_release_version_are_stable() -> None:
    lock = load_toolchain_lock(REPO)
    assert set(lock["apt_packages"]) == set(lock["apt_package_versions"])
    fingerprint = toolchain_fingerprint(lock)
    assert fingerprint == "6e0fc8ea7889634d3c337eacc4e4f68adb10c2c968e2e7e683f5c24de07408e5"
    assert REPORTKIT_VERSION == "1.9.3"
    assert generate_registry(REPO)["class_version"] == REPORTKIT_VERSION
    assert load_toolchain_lock(REPO)["apt_package_versions"]
    dockerfile = (REPO / "toolchain" / "Dockerfile").read_text()
    assert f"FROM {lock['base_image']}" in dockerfile
    assert lock["debian_snapshot"] in dockerfile
    assert "rm -f /etc/apt/sources.list.d/debian.sources" in dockerfile
    for package, version in lock["apt_package_versions"].items():
        assert f"{package}={version}" in dockerfile
    for digest in [lock["python_lock_sha256"], *lock["fonts"].values(), fingerprint]:
        assert digest in dockerfile
