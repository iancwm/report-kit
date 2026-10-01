"""The stable ReportKit command-line facade."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable

from .analysis import analyse_history
from .authoring import validate_authoring
from .config import (
    CONFIG_NAME,
    load_publication_config,
    resolve_declared_language,
    resolve_document,
    resolve_output,
    resolve_theme,
    resolve_validation,
    theme_font_policy_conflict,
)
from .composition_audit import audit_source, find_brief
from .context import build_context
from .context_budget import CONTEXT_SLICE_NAMES, build_context_slice
from .diagnostics import (
    diagnostic_envelope,
    inspect_log,
    load_allowlist,
    load_maps,
    make_diagnostic,
    registered_exit_code,
    suggest,
)
from .documentation import check_documentation, write_documentation
from .editorial_audit import audit_editorial_source
from .initialization import ensure_outside_repository, initialize, install_fonts, scaffold_target
from .languages import language_diagnostics
from .loop import next_step, target_line, target_payload
from .publications import (
    PUBLICATION_TYPES,
    THEMES,
    PublicationRegistryError,
    resolve_build_target,
)
from .registry import COMMAND_CONTRACT, PRIMITIVE_KINDS, ContractError, generate_registry
from .review import VISUAL_REVIEW_STATES, compare_intent, write_review
from .status import collect_status
from .target import (
    DECIDED_BY, SOURCE_MODES, TargetState, has_declared_source_mode, load_target, set_target, target_gate,
)
from .tex_target import engine_gate, tex_gates
from .version import CONTRACT_VERSION
from .publication_validation import validate_publication

PACKAGE_ROOT = Path(__file__).resolve().parent
PYTHON_ROOT = PACKAGE_ROOT.parent
REPO_ROOT = PYTHON_ROOT.parent
PIPELINE_ROOT = REPO_ROOT / "publication_pipeline"
DEFAULT_SOURCE_ROOT = PIPELINE_ROOT / "example_publication"
EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_VALIDATION = 3
EXIT_COMPILE = 4
EXIT_ENVIRONMENT = 5
EXIT_INTERNAL = 70


class ReportKitArgumentParser(argparse.ArgumentParser):
    """Keep argparse usage failures machine-readable when JSON was requested."""

    def error(self, message: str) -> None:
        if "--json" in sys.argv[1:]:
            diagnostic = make_diagnostic("configuration_error", message, code="RK_CLI_USAGE")
            print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
            self.exit(EXIT_CONFIG)
        super().error(message)


def _json_or_print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif isinstance(payload, str):
        print(payload)


def _loop_fields(payload: Any, state: TargetState | None, command: str) -> Any:
    """Add the reasoning loop's ``target`` and ``next_step`` to a JSON payload."""
    if not isinstance(payload, dict):
        return payload
    result = dict(payload)
    target = target_payload(state)
    if target:
        # `init --json` has reported its project path as `target` since v1;
        # there the loop's target object is `publication_target` instead.
        result.setdefault("publication_target" if isinstance(result.get("target"), str) else "target", target)
    step = next_step(command, state, result)
    if step:
        result.setdefault("next_step", step)
    return result


def _emit(
    payload: Any,
    state: TargetState | None,
    command: str,
    as_json: bool,
    *,
    human: Callable[[], None] | None = None,
) -> None:
    """The one output path for every command (agent reasoning loop spec §4.1).

    JSON output gains ``target`` and ``next_step``. Human output prints the
    TARGET line first, then the command's own text (``human``, or ``payload``
    when it is a string), then ``next step:`` last. ``next_step`` is computed
    after ``human`` runs, so ``human`` may still update a dict ``payload``.
    """
    if as_json:
        _json_or_print(_loop_fields(payload, state, command), True)
        return
    line = target_line(state)
    if line:
        print(line)
    if human is not None:
        human()
    elif isinstance(payload, str):
        print(payload)
    step = next_step(command, state, payload if isinstance(payload, dict) else {})
    if step:
        reason = f" ({step['reason']})" if step.get("reason") else ""
        print(f"next step: {step.get('command', '')}{reason}")


def _print_failures(diagnostics: list[dict[str, Any]]) -> None:
    for item in diagnostics:
        print(f"FAIL [{item['code']}]: {item['message']}", file=sys.stderr)


def _state(args: argparse.Namespace) -> TargetState | None:
    """Reload the project's target from disk for commands that name a project."""
    if not hasattr(args, "source_root"):
        return None
    return load_target(_source_root(args))


def _contract_diagnostics(requested: str | None) -> tuple[list[dict[str, Any]], int | None]:
    if not requested:
        return [], None
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", requested)
    if not match:
        return [make_diagnostic(
            "contract_version", f"contract version {requested!r} is not semantic version X.Y.Z",
            code="RK_CONTRACT_VERSION_INVALID", source=None, docs="#/contract_version",
        )], EXIT_CONFIG
    requested_parts = tuple(int(value) for value in match.groups())
    current_parts = tuple(int(value) for value in CONTRACT_VERSION.split("."))
    if requested_parts[0] != current_parts[0]:
        return [make_diagnostic(
            "contract_version",
            f"caller contract major {requested_parts[0]} is incompatible with installed major {current_parts[0]}",
            code="RK_CONTRACT_VERSION_MAJOR", docs="#/contract_version",
        )], EXIT_CONFIG
    if requested_parts > current_parts:
        return [make_diagnostic(
            "contract_version",
            f"caller contract {requested} is newer than installed contract {CONTRACT_VERSION}",
            code="RK_CONTRACT_VERSION_NEWER", docs="#/contract_version",
            remediation="Upgrade ReportKit or retry with the installed contract version.",
        )], EXIT_CONFIG
    if requested_parts < current_parts:
        return [make_diagnostic(
            "deprecated_contract",
            f"caller contract {requested} differs from installed contract {CONTRACT_VERSION}",
            code="RK_CONTRACT_VERSION_STALE", docs="#/contract_version",
        )], None
    return [], None


def _failure(kind: str, message: str, *, code: str, **payload: Any) -> dict[str, Any]:
    return diagnostic_envelope([make_diagnostic(kind, message, code=code)], passed=False, **payload)


def _source_root(args: argparse.Namespace) -> Path:
    return Path(args.source_root).resolve() if args.source_root else DEFAULT_SOURCE_ROOT.resolve()


def _output_root(args: argparse.Namespace, source_root: Path) -> Path:
    if getattr(args, "output_root", None):
        return Path(args.output_root).resolve()
    config = load_publication_config(source_root / CONFIG_NAME)
    configured = resolve_output(config, source_root, getattr(args, "profile", None))
    return configured or source_root / "build"


def _add_publication_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-root", help="consumer publication project")
    parser.add_argument("--output-root", help="where publication build artefacts live")
    parser.add_argument("--profile", default=None, help="publication config profile (for example, release)")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _run_doctor(args: argparse.Namespace) -> int:
    command = [sys.executable, str(REPO_ROOT / "python_scripts" / "reportkit_doctor.py")]
    if args.require:
        command += ["--require", args.require]
    if args.json:
        command.append("--json")
    proc = subprocess.run(command, text=True, capture_output=True)
    if args.json:
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = _failure("internal_error", proc.stderr or proc.stdout or "environment doctor failed", code="RK_DOCTOR_OUTPUT")
        _emit(payload, None, "doctor", True)
    else:
        def human() -> None:
            print(proc.stdout, end="")
            if proc.stderr:
                print(proc.stderr, end="", file=sys.stderr)
        _emit({"passed": proc.returncode == 0}, None, "doctor", False, human=human)
    return proc.returncode


def _default_init_target() -> Path:
    """Choose a safe default target outside the engine checkout."""
    cwd = Path.cwd().resolve()
    if cwd == REPO_ROOT or REPO_ROOT in cwd.parents:
        return REPO_ROOT.parent / f"{REPO_ROOT.name}-publication"
    return cwd / "publication"


def _run_init(args: argparse.Namespace) -> int:
    """Scaffold a consumer project, optionally install fonts, then report readiness."""
    target_value = getattr(args, "target_option", None) or getattr(args, "target", None)
    target = Path(target_value).expanduser() if target_value else _default_init_target()
    try:
        result = initialize(target, REPO_ROOT)
    except (OSError, ValueError) as exc:
        diagnostic = make_diagnostic(
            "configuration_error", str(exc), code="RK_INIT_FAILED", docs="#/commands/init",
        )
        payload = diagnostic_envelope([diagnostic], passed=False, target=str(target.resolve()))
        _emit(payload, None, "init", args.json, human=lambda: print(f"FAIL [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr))
        return EXIT_CONFIG

    # Agent reasoning loop spec §4.2: `init --publication-type/--theme/
    # --source-mode` locks the target the same way `target set` does.
    target_diagnostics: list[dict[str, Any]] = []
    target_created: tuple[str, ...] = ()
    if args.publication_type or args.theme or args.source_mode:
        _, target_diagnostics = set_target(
            result.target, publication_type=args.publication_type, theme=args.theme, source_mode=args.source_mode,
        )
        blocking = [item for item in target_diagnostics if item["severity"] == "error"]
        if blocking:
            payload = diagnostic_envelope(target_diagnostics, passed=False, target=str(result.target), created=list(result.created))
            _emit(payload, load_target(result.target), "init", args.json, human=lambda: _print_failures(blocking))
            return registered_exit_code(blocking) or EXIT_CONFIG
        state = load_target(result.target)
        try:
            target_created = scaffold_target(
                result.target, state.publication_type, state.theme, state.source_mode, main=state.main,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            diagnostic = make_diagnostic(
                "configuration_error", f"cannot scaffold target source: {exc}", code="RK_INIT_SCAFFOLD_FAILED",
                docs="#/commands/init",
            )
            payload = diagnostic_envelope(
                [*target_diagnostics, diagnostic], passed=False, target=str(result.target),
                created=[*result.created, *target_created],
            )
            _emit(payload, state, "init", args.json, human=lambda: print(f"FAIL [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr))
            return EXIT_CONFIG
    state = load_target(result.target)
    created = [*result.created, *target_created]

    font_status = None
    if args.install_fonts:
        try:
            font_status = install_fonts(REPO_ROOT)
        except (OSError, ValueError) as exc:
            diagnostic = make_diagnostic(
                "environment_error", str(exc), code="RK_INIT_FONT_INSTALL", docs="#/commands/init",
            )
            payload = diagnostic_envelope([diagnostic], passed=False, target=str(target))
            _emit(payload, state, "init", args.json, human=lambda: print(f"FAIL [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr))
            return EXIT_ENVIRONMENT

    doctor_command = [sys.executable, str(REPO_ROOT / "python_scripts" / "reportkit_doctor.py")]
    if args.json:
        doctor_command.append("--json")
    doctor = subprocess.run(doctor_command, text=True, capture_output=True)
    if args.json:
        try:
            doctor_payload = json.loads(doctor.stdout)
            diagnostics = doctor_payload.get("diagnostics", [])
        except json.JSONDecodeError:
            diagnostics = [make_diagnostic(
                "internal_error", doctor.stderr or doctor.stdout or "environment doctor failed", code="RK_DOCTOR_OUTPUT",
            )]
            doctor_payload = {}
        payload = diagnostic_envelope(
            [*target_diagnostics, *diagnostics],
            passed=doctor_payload.get("passed", not diagnostics),
            target=str(result.target), created=created, fonts=font_status,
            mode=doctor_payload.get("mode"), toolchain=doctor_payload.get("toolchain"),
            checks=doctor_payload.get("checks", []),
        )
        _emit(payload, state, "init", True)
    else:
        def human() -> None:
            print("== ReportKit init ==")
            print(f"consumer project: {result.target}")
            print("created: " + (", ".join(created) if created else "nothing (already initialized)"))
            for item in target_diagnostics:
                print(f"WARN [{item['code']}]: {item['message']}", file=sys.stderr)
            if font_status:
                print(font_status)
            if doctor.stdout:
                print(doctor.stdout, end="")
            if doctor.stderr:
                print(doctor.stderr, end="", file=sys.stderr)
        _emit({"passed": doctor.returncode == 0}, state, "init", False, human=human)
    return doctor.returncode


def _run_context(args: argparse.Namespace) -> int:
    if args.schema:
        schema_name = {
            "context": "reportkit-context.schema.json",
            "context-slice": "reportkit-context-slice.schema.json",
            "diagnostic": "reportkit-diagnostic.schema.json",
        }[args.schema]
        print((REPO_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"), end="")
        return EXIT_OK
    state = _state(args)
    try:
        payload = build_context(
            REPO_ROOT, _source_root(args), args.profile,
            publication_type=args.publication_type, theme=args.theme, kinds=args.kind,
        )
    except ContractError as exc:
        diagnostic = make_diagnostic(
            "contract_drift", str(exc), code="RK_CONTEXT_CONTRACT",
            docs="#/capabilities/primitives",
        )
        _emit(diagnostic_envelope([diagnostic], passed=False), state, "context", True)
        return EXIT_VALIDATION
    except PublicationRegistryError as exc:
        diagnostic = dict(exc.diagnostic)
        # Keep the registry API's complete valid-value list, while preserving
        # the CLI's long-standing typo-focused candidate suggestions.
        message = str(diagnostic.get("message", ""))
        if args.publication_type and message.startswith("unknown publication type"):
            diagnostic["candidates"] = sorted(set(suggest(args.publication_type, PUBLICATION_TYPES)))
        elif args.theme and message.startswith("unknown theme"):
            diagnostic["candidates"] = sorted(set(suggest(args.theme, THEMES)))
        _emit(diagnostic_envelope([diagnostic], passed=False), state, "context", True)
        return EXIT_CONFIG
    except ValueError as exc:
        candidates: list[str] = []
        if args.publication_type:
            candidates.extend(suggest(args.publication_type, PUBLICATION_TYPES))
        if args.theme:
            candidates.extend(suggest(args.theme, THEMES))
        for kind in args.kind or []:
            candidates.extend(suggest(kind, PRIMITIVE_KINDS))
        diagnostic = make_diagnostic(
            "configuration_error", str(exc), code="RK_CONTEXT_FILTER",
            candidates=sorted(set(candidates)), docs="#/capabilities",
        )
        _emit(diagnostic_envelope([diagnostic], passed=False), state, "context", True)
        return EXIT_CONFIG
    if args.context_slice:
        payload = build_context_slice(payload, args.context_slice)
    _emit(payload, state, "context", True)
    return EXIT_OK


def _run_docs(args: argparse.Namespace) -> int:
    registry = generate_registry(REPO_ROOT)
    errors = list(registry["contract_errors"])
    changed: list[str] = []
    if args.write and not errors:
        changed = write_documentation(REPO_ROOT, registry=registry)
    elif not args.write:
        errors.extend(check_documentation(REPO_ROOT, registry=registry))
    diagnostics = [make_diagnostic(
        "contract_drift", message, code="RK_CONTRACT_DRIFT", docs="#/commands/docs",
    ) for message in errors]
    payload = diagnostic_envelope(
        diagnostics, passed=not diagnostics, mode="write" if args.write else "check", changed=changed,
    )
    def human() -> None:
        if diagnostics:
            print("FAIL: generated contract documentation is stale", file=sys.stderr)
            for diagnostic in diagnostics:
                print(f"- {diagnostic['message']}", file=sys.stderr)
        elif args.write:
            print(f"PASS: generated contract documentation ({len(changed)} file(s) changed)")
        else:
            print("PASS: generated contract documentation is current")
    _emit(payload, None, "docs", args.json, human=human)
    return EXIT_OK if not diagnostics else EXIT_VALIDATION


def _composition_tex(args: argparse.Namespace, root: Path, state: TargetState) -> Path | None:
    """The TeX a composition audit reads: ``document.main`` in TeX mode, else
    the Markdown pipeline's generated ``publication.tex`` (spec §4.7)."""
    if state.source_mode == "tex":
        return root / state.main
    try:
        return _output_root(args, root) / "combined" / "publication.tex"
    except ValueError:
        return None


def _target_diagnostics(
    args: argparse.Namespace, root: Path, state: TargetState, engine: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """The reasoning loop's CHECK gates (spec §4.1): target lock, direct-TeX
    class options, engine, and the target's composition audit."""
    diagnostics = list(target_gate(state))
    if state.source_mode == "tex":
        diagnostics.extend(tex_gates(state, root / state.main))
    diagnostics.extend(engine_gate(state, engine))
    composition = None
    brief = find_brief(root, state)
    if brief is not None:
        tex = _composition_tex(args, root, state)
        if tex is not None and tex.is_file():
            composition = audit_source(tex, brief, state)
            diagnostics.extend(composition.get("diagnostics", []))
    return diagnostics, composition


def _run_check(args: argparse.Namespace) -> int:
    root = _source_root(args)
    state = load_target(root)
    diagnostics, version_exit = _contract_diagnostics(args.contract_version)
    if version_exit:
        payload = diagnostic_envelope(diagnostics, passed=False, errors=[item["message"] for item in diagnostics])
        _emit(payload, state, "check", args.json, human=lambda: print(payload["errors"][0], file=sys.stderr))
        return version_exit
    result = validate_publication(root, profile=args.profile or "draft")
    authoring = validate_authoring(root)
    diagnostics.extend(result.diagnostics)
    diagnostics.extend(authoring.diagnostics)
    try:
        config = load_publication_config(root / CONFIG_NAME)
    except ValueError as exc:
        diagnostic = make_diagnostic("configuration_error", str(exc), code="RK_CONFIG_INVALID", source={"file": CONFIG_NAME})
        diagnostics.append(diagnostic)
        config = {}
    document = resolve_document(config, args.profile)
    target_type = str(document.get("publication_type") or state.publication_type)
    state = replace(
        state,
        publication_type=target_type,
        theme=str(document.get("theme") or state.theme),
        renderer=str((PUBLICATION_TYPES.get(target_type) or {}).get("renderer", state.renderer)),
        source_mode=str(document.get("source_mode") or state.source_mode),
        main=str(document.get("main") or state.main),
        declared_by=str(document.get("declared_by") or state.declared_by),
        require_declared=bool(resolve_validation(config, args.profile).get("require_declared_target", state.require_declared)),
        source_mode_declared=has_declared_source_mode(config, args.profile),
    )
    engine_override = getattr(args, "engine", None) or os.environ.get("REPORTKIT_TEX_ENGINE")
    if engine_override:
        document = {**document, "engine": engine_override}
    try:
        resolve_build_target(
            str(document.get("publication_type")),
            str(document.get("theme")),
            explicit_paper=document.get("paper"),
            engine=str(document.get("engine")),
            repo_root=REPO_ROOT,
        )
    except PublicationRegistryError as exc:
        diagnostics.append(exc.diagnostic)
    theme_config = resolve_theme(config, args.profile)
    font_policy_conflict = theme_font_policy_conflict(theme_config)
    if font_policy_conflict:
        diagnostics.append(make_diagnostic("configuration_error", font_policy_conflict, code="RK_CONFIG_FONT_POLICY", primitive="theme.font_policy"))
    requested_theme = str(document.get("theme"))
    if requested_theme in THEMES:
        # Agent-contract spec section 13: fail early on RTL, malformed, or (under
        # strict) undeclared languages; warn on metadata-only languages.
        diagnostics.extend(language_diagnostics(
            resolve_declared_language(config, args.profile), requested_theme,
            font_policy=str(theme_config.get("font_policy", "fallback")),
        ))
    loop_diagnostics, composition = _target_diagnostics(args, root, state, engine_override)
    diagnostics.extend(loop_diagnostics)
    errors = [item["message"] for item in diagnostics if item["severity"] == "error"]
    payload = diagnostic_envelope(
        diagnostics,
        passed=not errors,
        errors=errors,
        manuscript_files=result.manuscript_files,
        visuals=result.slugs,
        labels=result.labels,
        profile=result.profile,
        image_slots={slug: asdict(slot) for slug, slot in result.image_slots.items()},
        unresolved_image_slots=[asdict(slot) for slot in result.unresolved_image_slots],
        sources=authoring.sources,
        chapters=authoring.chapters,
        links=authoring.links,
        **({"composition": composition} if composition is not None else {}),
    )

    def human() -> None:
        if not errors:
            print(f"PASS: publication validation ({len(result.manuscript_files)} manuscripts, {len(result.slugs)} visuals, {len(result.image_slots)} image slots, {len(result.labels)} labels)")
            for diagnostic in diagnostics:
                if diagnostic["severity"] == "warning":
                    print(f"WARN [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
        else:
            print("FAIL: publication validation", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
    _emit(payload, state, "check", args.json, human=human)
    if not errors:
        return EXIT_OK
    blocking = [item for item in diagnostics if item["severity"] == "error"]
    if registered_exit_code(blocking) == EXIT_ENVIRONMENT:
        return EXIT_ENVIRONMENT
    return EXIT_CONFIG if any(item["type"] == "configuration_error" for item in blocking) else EXIT_VALIDATION


def _run_build(args: argparse.Namespace) -> int:
    state = _state(args)
    version_diagnostics, version_exit = _contract_diagnostics(args.contract_version)
    if version_exit:
        payload = diagnostic_envelope(version_diagnostics, passed=False, errors=[item["message"] for item in version_diagnostics])
        _emit(payload, state, "build", args.json, human=lambda: print(payload["errors"][0], file=sys.stderr))
        return version_exit
    command = [sys.executable, str(PIPELINE_ROOT / "scripts" / "publication_build.py"), "--mode", args.mode]
    for name in ("source_root", "output_root", "profile", "engine", "title", "author", "version", "cover"):
        value = getattr(args, name, None)
        if value:
            command += [f"--{name.replace('_', '-')}", str(value)]
    section = args.section or args.chapter
    if section:
        command += ["--section", section]
    command += ["--workers", str(args.workers)]
    command += ["--compile-timeout-seconds", str(args.compile_timeout_seconds), "--memory-limit-mb", str(args.memory_limit_mb)]
    if args.json:
        command.append("--json")
        proc = subprocess.run(command, text=True, capture_output=True)
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            diagnostic = make_diagnostic(
                "compile_failure", proc.stderr or proc.stdout or "publication build failed without structured output",
                code="RK_BUILD_OUTPUT",
            )
            payload = diagnostic_envelope([*version_diagnostics, diagnostic], passed=False)
            proc = subprocess.CompletedProcess(proc.args, proc.returncode or EXIT_COMPILE, proc.stdout, proc.stderr)
        else:
            payload["diagnostics"] = [*version_diagnostics, *payload.get("diagnostics", [])]
            payload["issues"] = payload["diagnostics"]
        _emit(payload, state, "build", True)
        return proc.returncode
    outcome: dict[str, Any] = {"passed": False, "diagnostics": list(version_diagnostics)}

    def human() -> None:
        for diagnostic in version_diagnostics:
            print(f"WARN [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
        outcome["returncode"] = subprocess.run(command).returncode
        outcome["passed"] = outcome["returncode"] == 0
    _emit(outcome, state, "build", False, human=human)
    return int(outcome["returncode"])


def _find_log(args: argparse.Namespace, source_root: Path) -> Path | None:
    if args.log:
        candidate = Path(args.log).resolve()
        return candidate if candidate.is_file() else None
    output = _output_root(args, source_root)
    candidates = [output / "combined" / "publication.log"]
    candidates.extend(sorted(output.glob("section-*/publication.log"), reverse=True))
    return next((path for path in candidates if path.is_file()), None)


def _run_diagnose(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    state = load_target(source_root)
    log = _find_log(args, source_root)
    if not log:
        payload = _failure("configuration_error", "no publication.log found; pass a log path or build first", code="RK_DIAGNOSE_LOG_MISSING")
        _emit(payload, state, "diagnose", args.json, human=lambda: print("FAIL: no publication.log found; pass a log path or build first", file=sys.stderr))
        return EXIT_CONFIG
    allowlist_path = Path(args.allowlist).resolve() if args.allowlist else source_root / "build-log-allowlist.json"
    if not allowlist_path.is_file():
        allowlist_path = REPO_ROOT / "publication_pipeline" / "config" / "build-log-allowlist.json"
    result = inspect_log(
        log.read_text(encoding="utf-8", errors="replace"),
        underfull_badness=args.underfull_badness,
        allowlist=load_allowlist(allowlist_path),
        maps=load_maps(log.parent),
    )
    result["log"] = str(log)

    def human() -> None:
        if result["passed"]:
            print(f"PASS: {log} contains no actionable diagnostics")
        else:
            print(f"FAIL: {log} contains actionable diagnostics", file=sys.stderr)
            for issue in result["issues"]:
                location = issue.get("file") or "unknown source"
                if issue.get("line"):
                    location += f":{issue['line']}"
                print(f"- {location} [{issue['type']} / {issue['owner']}]: {issue['message']}", file=sys.stderr)
    _emit(result, state, "diagnose", args.json, human=human)
    return EXIT_OK if result["passed"] else EXIT_VALIDATION


def _find_pdf(build_dir: Path) -> Path | None:
    report = build_dir / "build-report.json"
    if report.is_file():
        try:
            value = json.loads(report.read_text(encoding="utf-8"))
            if value.get("pdf"):
                candidate = build_dir / value["pdf"]
                if candidate.is_file():
                    return candidate
        except json.JSONDecodeError:
            pass
    # Phase A5: the intermediate compiled artifact is always named
    # "publication.pdf" now (stable, independent of which entrypoint
    # template produced it -- publications.py's BuildTarget.template),
    # replacing the old literal "publication-template.pdf".
    return next((path for path in sorted(build_dir.glob("*.pdf")) if path.name != "publication.pdf"), None)


def _intent_diagnostics(pdf: Path, state: TargetState) -> list[dict[str, Any]]:
    """Compare the build's recorded selection with ``.reportkit/intent.json``
    (spec §4.8: ``inspect`` fails when the built target differs)."""
    report = pdf.parent / "build-report.json"
    try:
        selection = json.loads(report.read_text(encoding="utf-8")).get("selection") if report.is_file() else None
    except (OSError, json.JSONDecodeError, AttributeError):
        selection = None
    if not isinstance(selection, dict):
        return []
    _, diagnostics = compare_intent(selection, state)
    return diagnostics


def _run_inspect(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    state = load_target(source_root)
    pdf = Path(args.pdf).resolve() if args.pdf else _find_pdf(_output_root(args, source_root) / "combined")
    if not pdf or not pdf.is_file():
        payload = _failure("configuration_error", "no PDF found; pass a PDF path or build first", code="RK_INSPECT_PDF_MISSING")
        _emit(payload, state, "inspect", args.json, human=lambda: print("FAIL: no PDF found; pass a PDF path or build first", file=sys.stderr))
        return EXIT_CONFIG
    intent_diagnostics = _intent_diagnostics(pdf, state)
    intent_blocking = [item for item in intent_diagnostics if item["severity"] == "error"]
    inspector = PIPELINE_ROOT / "scripts" / "inspect_pdf.py"
    configured_python = os.environ.get("REPORTKIT_PDF_PYTHON")
    candidate = Path(configured_python).expanduser() if configured_python else _output_root(args, source_root) / ".venv" / "bin" / "python"
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).absolute()
    inspector_exit = EXIT_OK
    if candidate.is_file() and (configured_python or candidate != Path(sys.executable)):
        if args.json:
            with tempfile.TemporaryDirectory(prefix="reportkit-inspect-") as temp_dir:
                json_path = Path(temp_dir) / "inspection.json"
                proc = subprocess.run([str(candidate), str(inspector), str(pdf), "--json", str(json_path)], capture_output=True, text=True)
                inspector_exit = proc.returncode
                if proc.returncode and proc.stderr:
                    print(proc.stderr, end="", file=sys.stderr)
                if not json_path.is_file():
                    return EXIT_ENVIRONMENT if "requires PyMuPDF" in proc.stderr else EXIT_VALIDATION
                result = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            outcome: dict[str, Any] = {"passed": False, "diagnostics": intent_diagnostics}

            def run_inspector() -> None:
                outcome["returncode"] = subprocess.run([str(candidate), str(inspector), str(pdf)]).returncode
                _print_failures(intent_blocking)
                if intent_blocking and outcome["returncode"] == EXIT_OK:
                    outcome["returncode"] = EXIT_VALIDATION
                outcome["passed"] = outcome["returncode"] == EXIT_OK
            _emit(outcome, state, "inspect", False, human=run_inspector)
            return int(outcome["returncode"])
    else:
        try:
            from publication_pipeline.scripts.inspect_pdf import inspect as inspect_pdf
            result = inspect_pdf(pdf)
        except ModuleNotFoundError as exc:
            message = f"PDF inspection requires PyMuPDF; run publication_pipeline/scripts/setup.sh or set REPORTKIT_PDF_PYTHON ({exc})"
            payload = _failure("environment_error", message, code="RK_PYMUPDF_MISSING")
            _emit(payload, state, "inspect", args.json, human=lambda: print(f"FAIL: {message}", file=sys.stderr))
            return EXIT_ENVIRONMENT
    if intent_diagnostics:
        result = dict(result)
        result["diagnostics"] = [*result.get("diagnostics", []), *intent_diagnostics]
        if intent_blocking:
            result["passed"] = False

    def human() -> None:
        if result["passed"]:
            print(f"PASS: PDF inspection ({result['page_count']} pages, {result['link_count']} links)")
        else:
            if "outside_media_box" in result:
                print(f"FAIL: {len(result['outside_media_box'])} glyph boxes fall outside the media box", file=sys.stderr)
            _print_failures(intent_blocking)
    _emit(result, state, "inspect", args.json, human=human)
    if result["passed"]:
        return EXIT_OK
    return EXIT_ENVIRONMENT if inspector_exit == EXIT_ENVIRONMENT else EXIT_VALIDATION


def _run_render(args: argparse.Namespace) -> int:
    """Render selected PDF pages for the agent visual feedback loop."""
    source_root = _source_root(args)
    state = load_target(source_root)
    pdf = Path(args.pdf).resolve() if args.pdf else _find_pdf(_output_root(args, source_root) / "combined")
    if not pdf or not pdf.is_file():
        payload = _failure("configuration_error", "no PDF found; pass a PDF path or build first", code="RK_RENDER_PDF_MISSING")
        _emit(payload, state, "render", args.json, human=lambda: print("FAIL: no PDF found; pass a PDF path or build first", file=sys.stderr))
        return EXIT_CONFIG
    out_dir = Path(args.out).resolve() if args.out else _output_root(args, source_root) / "render"
    renderer = PIPELINE_ROOT / "scripts" / "render_pdf_pages.py"
    configured_python = os.environ.get("REPORTKIT_PDF_PYTHON")
    candidate = Path(configured_python).expanduser() if configured_python else _output_root(args, source_root) / ".venv" / "bin" / "python"
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).absolute()
    render_exit = EXIT_OK
    if candidate.is_file() and (configured_python or candidate != Path(sys.executable)):
        command = [str(candidate), str(renderer), str(pdf), str(out_dir), "--dpi", str(args.dpi)]
        if args.pages is not None:
            command += ["--pages", args.pages]
        if args.json:
            with tempfile.TemporaryDirectory(prefix="reportkit-render-") as temp_dir:
                json_path = Path(temp_dir) / "render.json"
                proc = subprocess.run([*command, "--json", str(json_path)], capture_output=True, text=True)
                render_exit = proc.returncode
                if proc.stderr:
                    print(proc.stderr, end="", file=sys.stderr)
                if not json_path.is_file():
                    payload = _failure(
                        "environment_error" if "requires PyMuPDF" in proc.stderr else "internal_error",
                        proc.stderr.strip() or "render helper produced no structured output",
                        code="RK_PYMUPDF_MISSING" if "requires PyMuPDF" in proc.stderr else "RK_RENDER_OUTPUT",
                    )
                    _emit(payload, state, "render", True)
                    return EXIT_ENVIRONMENT if "requires PyMuPDF" in proc.stderr else EXIT_INTERNAL
                result = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            outcome: dict[str, Any] = {"passed": False, "diagnostics": []}

            def run_renderer() -> None:
                outcome["returncode"] = subprocess.run(command).returncode
                outcome["passed"] = outcome["returncode"] == EXIT_OK
            _emit(outcome, state, "render", False, human=run_renderer)
            return int(outcome["returncode"])
    else:
        try:
            from publication_pipeline.scripts.render_pdf_pages import render as render_pages
            manifest = render_pages(pdf, out_dir, dpi=args.dpi, pages=args.pages)
            result = diagnostic_envelope([], passed=True, out_dir=str(out_dir), **manifest)
        except ModuleNotFoundError as exc:
            message = f"PDF rendering requires PyMuPDF; run publication_pipeline/scripts/setup.sh or set REPORTKIT_PDF_PYTHON ({exc})"
            payload = _failure("environment_error", message, code="RK_PYMUPDF_MISSING")
            _emit(payload, state, "render", args.json, human=lambda: print(f"FAIL: {message}", file=sys.stderr))
            return EXIT_ENVIRONMENT
        except ValueError as exc:
            payload = _failure("configuration_error", str(exc), code="RK_RENDER_PAGES_INVALID")
            error_text = f"FAIL: {exc}"
            _emit(payload, state, "render", args.json, human=lambda: print(error_text, file=sys.stderr))
            return EXIT_CONFIG

    def human() -> None:
        if result["passed"]:
            print(f"PASS: rendered {len(result['files'])} of {result['page_count']} page(s) to {out_dir} (dpi={args.dpi})")
    _emit(result, state, "render", args.json, human=human)
    if result["passed"]:
        return EXIT_OK
    return EXIT_ENVIRONMENT if render_exit == EXIT_ENVIRONMENT else EXIT_VALIDATION


def _run_package(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    state = load_target(source_root)
    build_dir = Path(args.build_dir).resolve() if args.build_dir else _output_root(args, source_root) / "combined"
    report_path = build_dir / "build-report.json"
    if not report_path.is_file():
        message = f"missing combined build manifest: {report_path}"
        payload = _failure("configuration_error", message, code="RK_PACKAGE_MANIFEST_MISSING")
        _emit(payload, state, "package", args.json, human=lambda: print(f"FAIL: {message}", file=sys.stderr))
        return EXIT_CONFIG
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        message = "package requires a passing combined build"
        payload = _failure("publication_validation", message, code="RK_PACKAGE_BUILD_FAILED")
        _emit(payload, state, "package", args.json, human=lambda: print(f"FAIL: {message}", file=sys.stderr))
        return EXIT_VALIDATION
    pdf = _find_pdf(build_dir)
    if not pdf:
        message = "passing build has no PDF"
        payload = _failure("publication_validation", message, code="RK_PACKAGE_PDF_MISSING")
        _emit(payload, state, "package", args.json, human=lambda: print(f"FAIL: {message}", file=sys.stderr))
        return EXIT_VALIDATION
    destination = Path(args.destination).resolve() if args.destination else source_root / "output"
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in (pdf, report_path, build_dir / "reportkit.lock", source_root / "reportkit.lock"):
        if path.is_file():
            target = destination / path.name
            shutil.copy2(path, target)
            copied.append(str(target))
    pages = build_dir / "pages"
    if pages.is_dir():
        target = destination / "pages"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(pages, target)
        copied.append(str(target))
    payload = {"passed": True, "destination": str(destination), "files": copied}

    def human() -> None:
        print(f"PASS: packaged release in {destination}")
        for path in copied:
            print(f"- {path}")
    _emit(diagnostic_envelope([], **payload), state, "package", args.json, human=human)
    return 0


def _run_analysis(args: argparse.Namespace) -> int:
    state = _state(args)
    history = Path(args.history_dir).resolve() if args.history_dir else _source_root(args) / "build" / "history"
    result = analyse_history(history)

    def human() -> None:
        print(f"ReportKit history: {result['build_count']} builds, {len(result['recurring'])} recurring diagnostics")
        for item in result["recurring"]:
            print(f"- {item['type']}: {item['occurrences']} occurrences across {item['builds']} builds")
    _emit(diagnostic_envelope([], **result), state, "analyse-history", args.json, human=human)
    return 0


def _tex_class_option_target(state: TargetState, tex: Path) -> TargetState:
    """Resolve an undeclared target from the TeX file's ``\\documentclass`` options.

    A project without ``publication.yaml`` that audits a file already naming
    ``publication-type=`` and ``theme=`` should be judged against that target
    rather than the silent technical-report default.
    """
    if state.declared_by != "default":
        return state
    try:
        head = tex.read_text(encoding="utf-8")[:4096]
    except (OSError, UnicodeError):
        return state
    match = re.search(r"\\documentclass\[([^\]]*)\]\{reportkit\}", head)
    if match is None:
        return state
    options = dict(
        (key.strip(), value.strip())
        for key, _, value in (item.partition("=") for item in match.group(1).split(","))
    )
    publication_type = options.get("publication-type")
    if publication_type not in PUBLICATION_TYPES:
        return state
    theme = options.get("theme", state.theme)
    return replace(
        state,
        publication_type=publication_type,
        theme=theme,
        renderer=str(PUBLICATION_TYPES[publication_type]["renderer"]),
        declared_by="tex-class-options",
    )


def _run_audit_editorial(args: argparse.Namespace) -> int:
    tex = Path(args.tex).resolve()
    brief = Path(args.brief).resolve()
    if not tex.is_file() or not brief.is_file():
        missing = tex if not tex.is_file() else brief
        payload = _failure("configuration_error", f"missing composition audit input: {missing}", code="RK_COMPOSITION_INPUT")
        _emit(payload, None, args.command, args.json)
        return EXIT_CONFIG
    try:
        if args.command == "audit-editorial":
            # Preserve the legacy alias's original feature-only behavior.
            state = None
            payload = audit_editorial_source(tex, brief)
        else:
            candidates = [*tex.parents, *brief.parents]
            source_root = next((path for path in candidates if (path / CONFIG_NAME).is_file()), tex.parent)
            state = _tex_class_option_target(load_target(source_root), tex)
            payload = audit_source(tex, brief, state)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        payload = _failure("configuration_error", str(exc), code="RK_COMPOSITION_BRIEF_INVALID")
        _emit(payload, None, args.command, args.json)
        return EXIT_CONFIG

    def human() -> None:
        print(f"{'PASS' if payload['passed'] else 'FAIL'}: publication composition audit")
        print("  Composition: " + ", ".join(f"{name}={count}" for name, count in payload["inventory"].items()))
        for item in payload["diagnostics"]:
            print(f"  {item['code']}: {item['message']}")
        print("  Manual page and evidence review is still required.")
    _emit(payload, state, args.command, args.json, human=human)
    return EXIT_OK if payload["passed"] else EXIT_VALIDATION


def _target_record(state: TargetState) -> dict[str, Any]:
    """The resolved target as ``target show`` reports it."""
    return {
        "publication_type": state.publication_type,
        "theme": state.theme,
        "renderer": state.renderer,
        "source_mode": state.source_mode,
        "main": state.main,
        "declared_by": state.declared_by,
        "require_declared": state.require_declared,
        "intent_path": str(state.intent_path) if state.intent_path is not None else None,
        "intent": state.intent,
    }


def _run_target(args: argparse.Namespace) -> int:
    """LOCK (spec §4.2): ``target set`` persists the decision; ``show`` reloads it."""
    root = _source_root(args)
    command = f"target {args.target_command}"
    diagnostics: list[dict[str, Any]] = []
    if args.target_command == "set":
        try:
            ensure_outside_repository(root, REPO_ROOT)
        except ValueError as exc:
            diagnostics = [make_diagnostic("configuration_error", str(exc), code="RK_TARGET_SOURCE_ROOT", docs="#/commands/target")]
            payload = diagnostic_envelope(diagnostics, passed=False, source_root=str(root))
            _emit(payload, None, command, args.json, human=lambda: _print_failures(diagnostics))
            return EXIT_CONFIG
        state, diagnostics = set_target(
            root, publication_type=args.publication_type, theme=args.theme, source_mode=args.source_mode,
            request=args.request, reference=args.reference, decided_by=args.decided_by,
        )
    else:
        state = load_target(root)
    blocking = [item for item in diagnostics if item["severity"] == "error"]
    record = _target_record(state)
    payload = diagnostic_envelope(diagnostics, passed=not blocking, source_root=str(root), target_state=record)

    def human() -> None:
        print(f"target: structure={state.publication_type} look={state.theme} renderer={state.renderer} "
              f"source={state.source_mode} declared={state.declared_by}")
        alias = (state.intent or {}).get("alias")
        if alias:
            print(f"alias: {alias} → structure={state.publication_type} look={state.theme}")
        _print_failures(blocking)
        for item in diagnostics:
            if item["severity"] != "error":
                print(f"WARN [{item['code']}]: {item['message']}", file=sys.stderr)
    _emit(payload, state, command, args.json, human=human)
    if not blocking:
        return EXIT_OK
    return registered_exit_code(blocking) or EXIT_CONFIG


def _run_status(args: argparse.Namespace) -> int:
    """DELIVER / re-hydrate (spec §4.8): the loop's state from disk alone."""
    root = _source_root(args)
    state = load_target(root)
    status = collect_status(root)
    diagnostics = list(status.pop("diagnostics", []))
    payload = diagnostic_envelope(diagnostics, source_root=str(root), **status)

    def human() -> None:
        intent = status.get("intent") or {}
        if intent.get("request"):
            print(f"intent: {intent['request']}")
        for key in ("last_step", "visual_review", "delivery_caveat"):
            if status.get(key):
                print(f"{key.replace('_', ' ')}: {status[key]}")
        _print_failures([item for item in diagnostics if item["severity"] == "error"])
    _emit(payload, state, "status", args.json, human=human)
    return EXIT_OK if payload["passed"] else EXIT_VALIDATION


def _run_review(args: argparse.Namespace) -> int:
    """REVIEW (spec §4.8): record the manual checklist and ``visual_review``."""
    root = _source_root(args)
    state = load_target(root)
    pdf = Path(args.pdf).resolve() if args.pdf else _find_pdf(_output_root(args, root) / "combined")
    if not pdf or not pdf.is_file():
        payload = _failure("configuration_error", "no PDF found; pass a PDF path or build first", code="RK_REVIEW_PDF_MISSING")
        _emit(payload, state, "review", args.json, human=lambda: print("FAIL: no PDF found; pass a PDF path or build first", file=sys.stderr))
        return EXIT_CONFIG
    record = write_review(pdf, state, args.visual_review)
    payload = diagnostic_envelope([], passed=True, review=record)

    def human() -> None:
        print(f"review: {pdf} visual_review={record.get('visual_review') or 'pending'}")
        for item in record.get("checklist", []):
            print(f"- [ ] {item.get('item', item) if isinstance(item, dict) else item}")
    _emit(payload, state, "review", args.json, human=human)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = ReportKitArgumentParser(prog="reportkit", description="Deterministic ReportKit publication engine")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help=COMMAND_CONTRACT["doctor"]["summary"], description=COMMAND_CONTRACT["doctor"]["summary"])
    doctor.add_argument("--require", choices=("full-build", "pinned-toolchain"))
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(handler=_run_doctor)

    init = sub.add_parser("init", help=COMMAND_CONTRACT["init"]["summary"], description=COMMAND_CONTRACT["init"]["summary"])
    init.add_argument("target", nargs="?", help="consumer publication project to scaffold")
    init.add_argument("--target", dest="target_option", help="consumer publication project to scaffold")
    init.add_argument("--install-fonts", action="store_true", help="install the bundled Libertinus fonts into TEXMFLOCAL")
    init.add_argument("--publication-type", help="lock the publication structure (see the quickstart selection table)")
    init.add_argument("--theme", help="lock the publication look")
    init.add_argument("--source-mode", choices=SOURCE_MODES, help="author as direct TeX or Markdown")
    init.add_argument("--json", action="store_true")
    init.set_defaults(handler=_run_init)

    target = sub.add_parser("target", help=COMMAND_CONTRACT["target"]["summary"], description=COMMAND_CONTRACT["target"]["summary"])
    target_sub = target.add_subparsers(dest="target_command", required=True)
    target_set = target_sub.add_parser(
        "set", help=COMMAND_CONTRACT["target"]["subcommands"]["set"]["summary"],
        description=COMMAND_CONTRACT["target"]["subcommands"]["set"]["summary"],
    )
    target_set.add_argument("--source-root", help="consumer publication project")
    target_set.add_argument("--publication-type", help="publication structure, or a natural-language alias such as 'magazine'")
    target_set.add_argument("--theme", help="publication look")
    target_set.add_argument("--source-mode", choices=SOURCE_MODES, help="author as direct TeX or Markdown")
    target_set.add_argument("--request", help="the user's verbatim request, stored in .reportkit/intent.json")
    target_set.add_argument("--reference", help="path to the user's visual reference, if any")
    target_set.add_argument("--decided-by", choices=DECIDED_BY, help="whether the user confirmed the target or the agent inferred it")
    target_set.add_argument("--json", action="store_true")
    target_set.set_defaults(handler=_run_target)
    target_show = target_sub.add_parser(
        "show", help=COMMAND_CONTRACT["target"]["subcommands"]["show"]["summary"],
        description=COMMAND_CONTRACT["target"]["subcommands"]["show"]["summary"],
    )
    target_show.add_argument("--source-root", help="consumer publication project")
    target_show.add_argument("--json", action="store_true")
    target_show.set_defaults(handler=_run_target)

    status = sub.add_parser("status", help=COMMAND_CONTRACT["status"]["summary"], description=COMMAND_CONTRACT["status"]["summary"])
    status.add_argument("--source-root", help="consumer publication project")
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=_run_status)

    context = sub.add_parser("context", help=COMMAND_CONTRACT["context"]["summary"], description=COMMAND_CONTRACT["context"]["summary"])
    _add_publication_paths(context)
    context.add_argument("--publication-type")
    context.add_argument("--theme")
    context.add_argument("--kind", action="append", help="repeat to request multiple primitive kinds")
    context.add_argument("--slice", dest="context_slice", choices=CONTEXT_SLICE_NAMES, help="return one compact contract slice")
    context.add_argument("--schema", nargs="?", const="context", choices=("context", "context-slice", "diagnostic"))
    context.add_argument("--json", action="store_true")
    context.set_defaults(handler=_run_context)

    check = sub.add_parser("check", help=COMMAND_CONTRACT["check"]["summary"], description=COMMAND_CONTRACT["check"]["summary"])
    _add_publication_paths(check)
    check.add_argument("--engine")
    check.add_argument("--contract-version")
    check.add_argument("--json", action="store_true")
    check.set_defaults(handler=_run_check)

    audit = sub.add_parser(
        "audit", aliases=COMMAND_CONTRACT["audit"]["aliases"],
        help=COMMAND_CONTRACT["audit"]["summary"], description=COMMAND_CONTRACT["audit"]["summary"],
    )
    audit.add_argument("tex", help="hand-authored TeX source")
    audit.add_argument("--brief", required=True, help="JSON composition brief naming the visual reference and expected roles")
    audit.add_argument("--json", action="store_true")
    audit.set_defaults(handler=_run_audit_editorial)

    build = sub.add_parser("build", help=COMMAND_CONTRACT["build"]["summary"], description=COMMAND_CONTRACT["build"]["summary"])
    _add_publication_paths(build)
    build.add_argument("--mode", choices=("combined", "section", "sections"), default="combined")
    build.add_argument("--section")
    build.add_argument("--chapter", help="compatibility alias for --section")
    build.add_argument("--workers", type=_positive_int, default=1, help="bounded parallel section builds in --mode sections (F2)")
    build.add_argument("--engine")
    build.add_argument("--title")
    build.add_argument("--author")
    build.add_argument("--version")
    build.add_argument("--cover")
    build.add_argument("--contract-version")
    build.add_argument("--compile-timeout-seconds", type=_positive_int, default=os.environ.get("REPORTKIT_COMPILE_TIMEOUT_SECONDS", "120"))
    build.add_argument("--memory-limit-mb", type=_positive_int, default=os.environ.get("REPORTKIT_MEMORY_LIMIT_MB", "2048"))
    build.add_argument("--json", action="store_true")
    build.set_defaults(handler=_run_build)

    diagnose = sub.add_parser("diagnose", help=COMMAND_CONTRACT["diagnose"]["summary"], description=COMMAND_CONTRACT["diagnose"]["summary"])
    _add_publication_paths(diagnose)
    diagnose.add_argument("log", nargs="?")
    diagnose.add_argument("--allowlist")
    diagnose.add_argument("--underfull-badness", type=int, default=4000)
    diagnose.add_argument("--json", action="store_true")
    diagnose.set_defaults(handler=_run_diagnose)

    inspect = sub.add_parser("inspect", help=COMMAND_CONTRACT["inspect"]["summary"], description=COMMAND_CONTRACT["inspect"]["summary"])
    _add_publication_paths(inspect)
    inspect.add_argument("pdf", nargs="?")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(handler=_run_inspect)

    render = sub.add_parser("render", help=COMMAND_CONTRACT["render"]["summary"], description=COMMAND_CONTRACT["render"]["summary"])
    _add_publication_paths(render)
    render.add_argument("pdf", nargs="?")
    render.add_argument("--out", help="page-image output directory (default: <output-root>/render)")
    render.add_argument("--pages", help="page selection, e.g. '1,3,5-7' (default: every page)")
    render.add_argument("--dpi", type=_positive_int, default=150)
    render.add_argument("--json", action="store_true")
    render.set_defaults(handler=_run_render)

    review = sub.add_parser("review", help=COMMAND_CONTRACT["review"]["summary"], description=COMMAND_CONTRACT["review"]["summary"])
    review.add_argument("pdf", nargs="?")
    review.add_argument("--source-root", help="consumer publication project")
    review.add_argument("--visual-review", choices=VISUAL_REVIEW_STATES, help="'unavailable' when the host cannot view rendered pages")
    review.add_argument("--json", action="store_true")
    review.set_defaults(handler=_run_review)

    package = sub.add_parser("package", help=COMMAND_CONTRACT["package"]["summary"], description=COMMAND_CONTRACT["package"]["summary"])
    _add_publication_paths(package)
    package.add_argument("--build-dir")
    package.add_argument("--destination")
    package.add_argument("--json", action="store_true")
    package.set_defaults(handler=_run_package)

    history = sub.add_parser("analyse-history", help=COMMAND_CONTRACT["analyse-history"]["summary"], description=COMMAND_CONTRACT["analyse-history"]["summary"])
    history.add_argument("--source-root", help="consumer publication project")
    history.add_argument("--history-dir", help="build history directory")
    history.add_argument("--json", action="store_true")
    history.set_defaults(handler=_run_analysis)

    docs = sub.add_parser("docs", help=COMMAND_CONTRACT["docs"]["summary"], description=COMMAND_CONTRACT["docs"]["summary"])
    mode = docs.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    docs.add_argument("--json", action="store_true")
    docs.set_defaults(handler=_run_docs)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        diagnostic = make_diagnostic("internal_error", str(exc), code="RK_INTERNAL_ERROR")
        if getattr(args, "json", False):
            _json_or_print(diagnostic_envelope([diagnostic], passed=False), True)
        else:
            print(f"FAIL [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
