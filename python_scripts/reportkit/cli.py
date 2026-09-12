"""The stable ReportKit command-line facade."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from .analysis import analyse_history
from .authoring import validate_authoring
from .config import (
    CONFIG_NAME,
    load_publication_config,
    resolve_document,
    resolve_output,
    resolve_theme,
    theme_font_policy_conflict,
)
from .context import build_context
from .diagnostics import diagnostic_envelope, inspect_log, load_allowlist, load_maps, make_diagnostic, suggest
from .documentation import check_documentation, write_documentation
from .initialization import initialize, install_fonts
from .publications import (
    PUBLICATION_TYPES,
    THEMES,
    PublicationRegistryError,
    resolve_build_target,
)
from .registry import COMMAND_CONTRACT, PRIMITIVE_KINDS, ContractError, generate_registry
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
    if args.output_root:
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
        _json_or_print(payload, True)
    else:
        print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
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
        if args.json:
            _json_or_print(payload, True)
        else:
            print(f"FAIL [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
        return EXIT_CONFIG

    font_status = None
    if args.install_fonts:
        try:
            font_status = install_fonts(REPO_ROOT)
        except (OSError, ValueError) as exc:
            diagnostic = make_diagnostic(
                "environment_error", str(exc), code="RK_INIT_FONT_INSTALL", docs="#/commands/init",
            )
            payload = diagnostic_envelope([diagnostic], passed=False, target=str(target))
            if args.json:
                _json_or_print(payload, True)
            else:
                print(f"FAIL [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
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
            diagnostics,
            passed=doctor_payload.get("passed", not diagnostics),
            target=str(result.target), created=list(result.created), fonts=font_status,
            mode=doctor_payload.get("mode"), toolchain=doctor_payload.get("toolchain"),
            checks=doctor_payload.get("checks", []),
        )
        _json_or_print(payload, True)
    else:
        print("== ReportKit init ==")
        print(f"consumer project: {result.target}")
        print("created: " + (", ".join(result.created) if result.created else "nothing (already initialized)"))
        if font_status:
            print(font_status)
        if doctor.stdout:
            print(doctor.stdout, end="")
        if doctor.stderr:
            print(doctor.stderr, end="", file=sys.stderr)
    return doctor.returncode


def _run_context(args: argparse.Namespace) -> int:
    if args.schema:
        schema_name = "reportkit-context.schema.json" if args.schema == "context" else "reportkit-diagnostic.schema.json"
        print((REPO_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"), end="")
        return EXIT_OK
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
        _json_or_print(diagnostic_envelope([diagnostic], passed=False), True)
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
        _json_or_print(diagnostic_envelope([diagnostic], passed=False), True)
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
        _json_or_print(diagnostic_envelope([diagnostic], passed=False), True)
        return EXIT_CONFIG
    _json_or_print(payload, True)
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
    if args.json:
        _json_or_print(payload, True)
    elif diagnostics:
        print("FAIL: generated contract documentation is stale", file=sys.stderr)
        for diagnostic in diagnostics:
            print(f"- {diagnostic['message']}", file=sys.stderr)
    elif args.write:
        print(f"PASS: generated contract documentation ({len(changed)} file(s) changed)")
    else:
        print("PASS: generated contract documentation is current")
    return EXIT_OK if not diagnostics else EXIT_VALIDATION


def _run_check(args: argparse.Namespace) -> int:
    root = _source_root(args)
    diagnostics, version_exit = _contract_diagnostics(args.contract_version)
    if version_exit:
        payload = diagnostic_envelope(diagnostics, passed=False, errors=[item["message"] for item in diagnostics])
        _json_or_print(payload, args.json)
        if not args.json:
            print(payload["errors"][0], file=sys.stderr)
        return version_exit
    result = validate_publication(root)
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
    engine_override = getattr(args, "engine", None) or os.environ.get("REPORTKIT_TEX_ENGINE")
    if engine_override:
        document = {**document, "engine": engine_override}
    try:
        resolve_build_target(
            str(document.get("publication_type")),
            str(document.get("theme")),
            explicit_paper=str(document.get("paper")),
            engine=str(document.get("engine")),
            repo_root=REPO_ROOT,
        )
    except PublicationRegistryError as exc:
        diagnostics.append(exc.diagnostic)
    font_policy_conflict = theme_font_policy_conflict(resolve_theme(config, args.profile))
    if font_policy_conflict:
        diagnostics.append(make_diagnostic("configuration_error", font_policy_conflict, code="RK_CONFIG_FONT_POLICY", primitive="theme.font_policy"))
    errors = [item["message"] for item in diagnostics if item["severity"] == "error"]
    payload = diagnostic_envelope(
        diagnostics,
        passed=not errors,
        errors=errors,
        manuscript_files=result.manuscript_files,
        visuals=result.slugs,
        labels=result.labels,
        sources=authoring.sources,
        chapters=authoring.chapters,
        links=authoring.links,
    )
    if args.json:
        _json_or_print(payload, True)
    elif not errors:
        print(f"PASS: publication validation ({len(result.manuscript_files)} manuscripts, {len(result.slugs)} visuals, {len(result.labels)} labels)")
    else:
        print("FAIL: publication validation", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    if not errors:
        return EXIT_OK
    return EXIT_CONFIG if any(item["type"] == "configuration_error" for item in diagnostics if item["severity"] == "error") else EXIT_VALIDATION


def _run_build(args: argparse.Namespace) -> int:
    version_diagnostics, version_exit = _contract_diagnostics(args.contract_version)
    if version_exit:
        payload = diagnostic_envelope(version_diagnostics, passed=False, errors=[item["message"] for item in version_diagnostics])
        if args.json:
            _json_or_print(payload, True)
        else:
            print(payload["errors"][0], file=sys.stderr)
        return version_exit
    command = [sys.executable, str(PIPELINE_ROOT / "scripts" / "publication_build.py"), "--mode", args.mode]
    for name in ("source_root", "output_root", "profile", "engine", "title", "author", "version", "cover"):
        value = getattr(args, name, None)
        if value:
            command += [f"--{name.replace('_', '-')}", str(value)]
    section = args.section or args.chapter
    if section:
        command += ["--section", section]
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
        _json_or_print(payload, True)
        return proc.returncode
    if version_diagnostics:
        for diagnostic in version_diagnostics:
            print(f"WARN [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
    return subprocess.run(command).returncode


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
    log = _find_log(args, source_root)
    if not log:
        payload = _failure("configuration_error", "no publication.log found; pass a log path or build first", code="RK_DIAGNOSE_LOG_MISSING")
        if args.json:
            _json_or_print(payload, True)
        else:
            print("FAIL: no publication.log found; pass a log path or build first", file=sys.stderr)
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
    if args.json:
        _json_or_print(result, True)
    else:
        if result["passed"]:
            print(f"PASS: {log} contains no actionable diagnostics")
        else:
            print(f"FAIL: {log} contains actionable diagnostics", file=sys.stderr)
            for issue in result["issues"]:
                location = issue.get("file") or "unknown source"
                if issue.get("line"):
                    location += f":{issue['line']}"
                print(f"- {location} [{issue['type']} / {issue['owner']}]: {issue['message']}", file=sys.stderr)
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
    return next((path for path in sorted(build_dir.glob("*.pdf")) if path.name != "publication-template.pdf"), None)


def _run_inspect(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    pdf = Path(args.pdf).resolve() if args.pdf else _find_pdf(_output_root(args, source_root) / "combined")
    if not pdf or not pdf.is_file():
        payload = _failure("configuration_error", "no PDF found; pass a PDF path or build first", code="RK_INSPECT_PDF_MISSING")
        if args.json:
            _json_or_print(payload, True)
        else:
            print("FAIL: no PDF found; pass a PDF path or build first", file=sys.stderr)
        return EXIT_CONFIG
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
            return subprocess.run([str(candidate), str(inspector), str(pdf)]).returncode
    else:
        try:
            from publication_pipeline.scripts.inspect_pdf import inspect as inspect_pdf
            result = inspect_pdf(pdf)
        except ModuleNotFoundError as exc:
            message = f"PDF inspection requires PyMuPDF; run publication_pipeline/scripts/setup.sh or set REPORTKIT_PDF_PYTHON ({exc})"
            payload = _failure("environment_error", message, code="RK_PYMUPDF_MISSING")
            if args.json:
                _json_or_print(payload, True)
            else:
                print(f"FAIL: {message}", file=sys.stderr)
            return EXIT_ENVIRONMENT
    if args.json:
        _json_or_print(result, True)
    elif result["passed"]:
        print(f"PASS: PDF inspection ({result['page_count']} pages, {result['link_count']} links)")
    else:
        print(f"FAIL: {len(result['outside_media_box'])} glyph boxes fall outside the media box", file=sys.stderr)
    if result["passed"]:
        return EXIT_OK
    return EXIT_ENVIRONMENT if inspector_exit == EXIT_ENVIRONMENT else EXIT_VALIDATION


def _run_package(args: argparse.Namespace) -> int:
    source_root = _source_root(args)
    build_dir = Path(args.build_dir).resolve() if args.build_dir else _output_root(args, source_root) / "combined"
    report_path = build_dir / "build-report.json"
    if not report_path.is_file():
        message = f"missing combined build manifest: {report_path}"
        payload = _failure("configuration_error", message, code="RK_PACKAGE_MANIFEST_MISSING")
        if args.json:
            _json_or_print(payload, True)
        else:
            print(f"FAIL: {message}", file=sys.stderr)
        return EXIT_CONFIG
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        message = "package requires a passing combined build"
        payload = _failure("publication_validation", message, code="RK_PACKAGE_BUILD_FAILED")
        if args.json:
            _json_or_print(payload, True)
        else:
            print(f"FAIL: {message}", file=sys.stderr)
        return EXIT_VALIDATION
    pdf = _find_pdf(build_dir)
    if not pdf:
        message = "passing build has no PDF"
        payload = _failure("publication_validation", message, code="RK_PACKAGE_PDF_MISSING")
        if args.json:
            _json_or_print(payload, True)
        else:
            print(f"FAIL: {message}", file=sys.stderr)
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
    if args.json:
        _json_or_print(diagnostic_envelope([], **payload), True)
    else:
        print(f"PASS: packaged release in {destination}")
        for path in copied:
            print(f"- {path}")
    return 0


def _run_analysis(args: argparse.Namespace) -> int:
    history = Path(args.history_dir).resolve() if args.history_dir else _source_root(args) / "build" / "history"
    result = analyse_history(history)
    if args.json:
        _json_or_print(diagnostic_envelope([], **result), True)
    else:
        print(f"ReportKit history: {result['build_count']} builds, {len(result['recurring'])} recurring diagnostics")
        for item in result["recurring"]:
            print(f"- {item['type']}: {item['occurrences']} occurrences across {item['builds']} builds")
    return 0


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
    init.add_argument("--json", action="store_true")
    init.set_defaults(handler=_run_init)

    context = sub.add_parser("context", help=COMMAND_CONTRACT["context"]["summary"], description=COMMAND_CONTRACT["context"]["summary"])
    _add_publication_paths(context)
    context.add_argument("--publication-type")
    context.add_argument("--theme")
    context.add_argument("--kind", action="append", help="repeat to request multiple primitive kinds")
    context.add_argument("--schema", nargs="?", const="context", choices=("context", "diagnostic"))
    context.add_argument("--json", action="store_true")
    context.set_defaults(handler=_run_context)

    check = sub.add_parser("check", help=COMMAND_CONTRACT["check"]["summary"], description=COMMAND_CONTRACT["check"]["summary"])
    _add_publication_paths(check)
    check.add_argument("--engine")
    check.add_argument("--contract-version")
    check.add_argument("--json", action="store_true")
    check.set_defaults(handler=_run_check)

    build = sub.add_parser("build", help=COMMAND_CONTRACT["build"]["summary"], description=COMMAND_CONTRACT["build"]["summary"])
    _add_publication_paths(build)
    build.add_argument("--mode", choices=("combined", "section", "sections"), default="combined")
    build.add_argument("--section")
    build.add_argument("--chapter", help="compatibility alias for --section")
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
