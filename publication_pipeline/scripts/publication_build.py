#!/usr/bin/env python3
"""Build one section, or the canonical combined publication, from a project.

The publication being built lives outside this repository: pass --source-root
at the consumer project and --output-root wherever its build artefacts belong.
See references/repository-boundary.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from publication_validation import validate_publication

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_ROOT.parent
TEMPLATE = PIPELINE_ROOT / "templates" / "publication-template.tex"
LICENSE_FILE = REPO_ROOT / "metadata" / "licenses.yml"
# With no --source-root the pipeline builds its own generic example, so a bare
# invocation exercises the toolchain without assuming any real publication.
DEFAULT_SOURCE_ROOT = PIPELINE_ROOT / "example_publication"


def _load_reportkit_package() -> None:
    if "reportkit" in sys.modules:
        return
    package = REPO_ROOT / "python_scripts" / "reportkit"
    spec = importlib.util.spec_from_file_location(
        "reportkit", package / "__init__.py", submodule_search_locations=[str(package)]
    )
    if not spec or not spec.loader:
        raise ImportError(f"cannot load ReportKit package from {package}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["reportkit"] = module
    spec.loader.exec_module(module)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_load_reportkit_package()

from reportkit.authoring import render_links_tex, validate_authoring  # noqa: E402
from reportkit.config import (  # noqa: E402
    CONFIG_NAME,
    load_publication_config,
    resolve_document,
    resolve_identity,
    resolve_validation,
)
from reportkit.manifest import unique_build_id, write_report  # noqa: E402

load_license_metadata = _load_module("reportkit_license_metadata", REPO_ROOT / "python_scripts" / "license_metadata.py").load_license_metadata


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tex_escape(value: str) -> str:
    return "".join({"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}.get(char, char) for char in value)


def version_line(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        return "not found"
    proc = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10)
    return ((proc.stdout or proc.stderr).splitlines() or [executable])[0].strip()


def order_entries(root: Path) -> list[str]:
    return [line.strip() for line in (root / "manuscript" / "order.txt").read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]


def render_markdown(root: Path, manuscript: Path, output: Path, map_path: Path | None = None) -> None:
    proc = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex", str(manuscript)], cwd=root.parent, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr or f"Pandoc failed for {manuscript}")
    source_lines = manuscript.read_text(encoding="utf-8").splitlines()
    source_locations = {
        match.group(1): line_number
        for line_number, raw in enumerate(source_lines, 1)
        if (match := re.search(r"REPORTKIT-VISUAL:fig:([a-z0-9]+(?:-[a-z0-9]+)*)", raw))
    }
    lines: list[str] = []
    fragments: list[dict[str, object]] = []
    for line in proc.stdout.splitlines():
        match = re.fullmatch(
            r"\s*(?:\[\[|\{\[\}\{\[\})REPORTKIT-VISUAL:fig:"
            r"([a-z0-9]+(?:-[a-z0-9]+)*)"
            r"(?:\]\]|\{\]\}\{\]\})\s*",
            line,
        )
        if match:
            fragment = root / "fragments" / f"fig-{match.group(1)}.tex"
            if not fragment.is_file():
                raise RuntimeError(f"missing fragment: {fragment}")
            generated_start = len(lines) + 1
            fragment_lines = fragment.read_text(encoding="utf-8").splitlines()
            lines.extend(fragment_lines)
            generated_end = generated_start + max(0, len(fragment_lines) - 1)
            fragments.append({
                "start": generated_start,
                "end": generated_end,
                "generated_start": generated_start,
                "generated_end": generated_end,
                "source_start": source_locations.get(match.group(1)),
                "source_end": source_locations.get(match.group(1)),
                "slug": match.group(1),
                "path": str(fragment.relative_to(root)),
            })
        else:
            lines.append(line)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sidecar = map_path or output.with_name(f"{output.stem}.map.json")
    sidecar.write_text(json.dumps({"source": str(manuscript.relative_to(root)), "fragments": fragments}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_metadata(path: Path, *, identity: dict[str, str], combined: bool, license_values: dict[str, str], cover_name: str | None, uses_tables: bool, uses_code: bool) -> None:
    """Emit the publication's identity as LaTeX macros.

    Every value here comes from the consumer project's publication.yaml or the
    CLI. Nothing about a specific publication is hard-coded in this engine.
    """
    lines = [
        "% Generated by publication_build.py; do not edit.",
        "\\newif\\ifRKPubUsesTables",
        "\\RKPubUsesTablestrue" if uses_tables else "\\RKPubUsesTablesfalse",
        "\\newif\\ifRKPubUsesCode",
        "\\RKPubUsesCodetrue" if uses_code else "\\RKPubUsesCodefalse",
        "\\newif\\ifRKPubIsCombined",
        "\\newif\\ifRKPubHasCover",
        "\\RKPubIsCombinedtrue" if combined else "\\RKPubIsCombinedfalse",
        "\\RKPubHasCovertrue" if cover_name else "\\RKPubHasCoverfalse",
        f"\\newcommand{{\\RKPubTitle}}{{{tex_escape(identity['title'])}}}",
        f"\\newcommand{{\\RKPubSubtitle}}{{{tex_escape(identity['subtitle'])}}}",
        f"\\newcommand{{\\RKPubAuthor}}{{{tex_escape(identity['author'])}}}",
        f"\\newcommand{{\\RKPubVersion}}{{{tex_escape(identity['version'])}}}",
        "\\newcommand{\\RKPubDate}{" + datetime.now().strftime("%-d %B %Y") + "}",
        f"\\newcommand{{\\RKPubLeftHeader}}{{{tex_escape(identity['left_header'])}}}",
        f"\\newcommand{{\\RKPubFooter}}{{{tex_escape(identity['footer'])}}}",
        f"\\newcommand{{\\RKPubSubject}}{{{tex_escape(identity['subject'])}}}",
        f"\\newcommand{{\\RKPubKeywords}}{{{tex_escape(identity['keywords'])}}}",
        f"\\newcommand{{\\RKPubProjectURL}}{{{identity['project_url']}}}",
        f"\\newcommand{{\\RKPubContentLicense}}{{{tex_escape(license_values['content_license'])}}}",
        f"\\newcommand{{\\RKPubContentLicenseURL}}{{{license_values['content_license_url']}}}",
        f"\\newcommand{{\\RKPubCoverPath}}{{{cover_name or ''}}}",
        f"\\newcommand{{\\RKPubDisclaimer}}{{{tex_escape(identity['disclaimer'])}}}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def git_value(args: list[str]) -> str:
    """Describe the engine checkout, degrading to 'unknown' outside git."""
    try:
        proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "unknown"


def write_lock(path: Path, *, engine: str, tool_versions: dict[str, str]) -> None:
    """Pin the engine and toolchain the publication was built against."""
    lock = {
        "reportkit_ref": git_value(["describe", "--tags", "--always"]),
        "reportkit_commit": git_value(["rev-parse", "HEAD"]),
        "tex_engine": engine,
        "pandoc": tool_versions.get("pandoc", "unknown"),
        "python": tool_versions.get("python", "unknown"),
    }
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(command: list[str], cwd: Path, log: Path) -> int:
    with log.open("a", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(command) + "\n")
        proc = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, text=True)
    return proc.returncode


def resolve_roots(args: argparse.Namespace) -> tuple[Path, Path]:
    """Locate the publication and where its artefacts go.

    Both default into the consumer project, never into this repository, so a
    build cannot silently write publication output back into the engine.
    """
    source_root = Path(args.source_root).resolve() if args.source_root else DEFAULT_SOURCE_ROOT
    output_root = Path(args.output_root).resolve() if args.output_root else source_root / "build"
    return source_root, output_root


def build(args: argparse.Namespace) -> int:
    source_root, output_root = resolve_roots(args)
    profile = getattr(args, "profile", None)
    validation = validate_publication(source_root)
    if not validation.ok:
        for error in validation.errors:
            print(f"publication validation: {error}", file=sys.stderr)
        return 1
    authoring = validate_authoring(source_root)
    if not authoring.ok:
        for error in authoring.errors:
            print(f"authoring validation: {error}", file=sys.stderr)
        return 1
    try:
        license_values = load_license_metadata(LICENSE_FILE)
    except (OSError, ValueError) as exc:
        print(f"licensing: {exc}", file=sys.stderr)
        return 1
    try:
        config = load_publication_config(source_root / CONFIG_NAME)
        identity = resolve_identity(
            config,
            {"title": getattr(args, "title", None), "author": getattr(args, "author", None), "version": getattr(args, "version", None)},
            source_root,
            profile=profile,
        )
    except (OSError, ValueError) as exc:
        print(f"publication config: {exc}", file=sys.stderr)
        return 2
    entries = order_entries(source_root)
    if args.mode == "section":
        chosen = getattr(args, "section", None)
        if not chosen:
            print("--section is required in section mode", file=sys.stderr)
            return 2
        manuscripts = [Path(chosen)]
    else:
        manuscripts = [Path(entry) for entry in entries]
    for manuscript in manuscripts:
        if not (source_root / "manuscript" / manuscript).is_file():
            print(f"missing manuscript: {manuscript}", file=sys.stderr)
            return 1
    stamp = time.strftime("%Y%m%d-%H%M%S")
    history_root = output_root / "history"
    build_id = unique_build_id(args.mode, stamp, history_root)
    output = output_root / ("combined" if args.mode == "combined" else f"section-{Path(manuscripts[0]).stem}-{stamp}")
    if output.exists() and args.mode != "combined":
        output = output_root / build_id
    output.mkdir(parents=True, exist_ok=True)
    for path in list((REPO_ROOT / "latex_templates").glob("*.cls")) + list((REPO_ROOT / "latex_templates").glob("*.sty")):
        shutil.copy2(path, output / path.name)
    shutil.copy2(TEMPLATE, output / TEMPLATE.name)
    cover_name = None
    if args.cover:
        cover = Path(args.cover).resolve()
        if not cover.is_file() or cover.suffix.lower() != ".pdf":
            print(f"cover must be an existing PDF: {cover}", file=sys.stderr)
            return 2
        cover_name = "reportkit-cover.pdf"
        shutil.copy2(cover, output / cover_name)
    body_files = []
    for index, manuscript in enumerate(manuscripts):
        rendered = output / f"body-{index:02d}.tex"
        render_markdown(source_root, source_root / "manuscript" / manuscript, rendered)
        body_files.append(rendered)
    body = output / "body.tex"
    body.write_text("\n".join(f"\\input{{{path.stem}}}" for path in body_files) + "\n", encoding="utf-8")
    manuscript_text = "\n".join((source_root / "manuscript" / path).read_text(encoding="utf-8") for path in manuscripts)
    uses_tables = any("|" in line and "---" in line for line in manuscript_text.splitlines())
    uses_code = "```" in manuscript_text or "~~~" in manuscript_text
    write_metadata(output / "metadata.tex", identity=identity, combined=args.mode == "combined", license_values=license_values, cover_name=cover_name, uses_tables=uses_tables, uses_code=uses_code)
    links_file = source_root / "links.yaml"
    if links_file.is_file():
        try:
            render_links_tex(links_file, output / "links.tex")
        except (OSError, ValueError) as exc:
            print(f"link registry: {exc}", file=sys.stderr)
            return 2
    tex = output / TEMPLATE.name
    log = output / "publication.log"
    document = resolve_document(config, profile)
    validation_config = resolve_validation(config, profile)
    engine = str(getattr(args, "engine", None) or os.environ.get("REPORTKIT_TEX_ENGINE") or document.get("engine", "pdflatex"))
    figure_count = sum(len(re.findall(r"REPORTKIT-VISUAL:fig:[a-z0-9]+(?:-[a-z0-9]+)*", text)) for text in ((source_root / "manuscript" / path).read_text(encoding="utf-8") for path in manuscripts))
    table_count = len(re.findall(r"(?m)^\s*\|.*\n\s*\|?\s*:?-{3,}", manuscript_text))
    report = {
        "schema_version": 2,
        "build_id": build_id,
        "mode": args.mode,
        "profile": profile or "draft",
        "version": identity["version"],
        "commit": git_value(["rev-parse", "HEAD"]),
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": [{"path": str(path), "sha256": sha256(source_root / "manuscript" / path)} for path in manuscripts],
        "templates": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256(path)} for path in (list((REPO_ROOT / "latex_templates").glob("*.cls")) + list((REPO_ROOT / "latex_templates").glob("*.sty")) + [TEMPLATE, LICENSE_FILE])],
        "tool_versions": {"python": sys.version.split()[0], "pandoc": version_line("pandoc"), "tex": version_line(engine)},
        "commands": [], "exit_codes": [], "diagnostics": {}, "figures": figure_count, "tables": table_count, "pdf_sha256": None,
    }
    texinputs = f"{output}:{REPO_ROOT / 'latex_templates'}:"
    for pass_number in range(1, 3):
        command = [engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name]
        report["commands"].append(" ".join(command))
        env = dict(os.environ, TEXINPUTS=texinputs)
        pass_log = output / f"publication-pass-{pass_number}.log"
        with pass_log.open("w", encoding="utf-8") as stream:
            stream.write("$ " + " ".join(command) + "\n")
            proc = subprocess.run(command, cwd=output, env=env, stdout=stream, stderr=subprocess.STDOUT, text=True)
        report["exit_codes"].append({"command": " ".join(command), "code": proc.returncode})
        if proc.returncode:
            report["status"] = "failed"
            report["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_report(report, output / "build-report.json", history_root)
            return proc.returncode
        if pass_number == 2:
            shutil.copy2(pass_log, log)
    gate = SCRIPT_DIR / "check_build_log.py"
    gate_command = [sys.executable, str(gate), str(log), "--json", str(output / "diagnostics.json"), "--map-dir", str(output), "--source-root", str(source_root)]
    threshold = validation_config.get("underfull_badness_threshold")
    if threshold is not None:
        gate_command += ["--underfull-badness", str(int(threshold))]
    # Which diagnostics a publication has reviewed and accepted is that
    # publication's call, not this engine's -- so prefer an allowlist that
    # lives with the project. Falls back to the engine's own (empty) default
    # when the project has not defined one.
    project_allowlist = source_root / "build-log-allowlist.json"
    if project_allowlist.is_file():
        gate_command += ["--allowlist", str(project_allowlist)]
    gate_result = subprocess.run(gate_command, text=True)
    report["exit_codes"].append({"command": f"{sys.executable} {gate} {log}", "code": gate_result.returncode})
    report["diagnostics"] = json.loads((output / "diagnostics.json").read_text(encoding="utf-8"))
    report["gate"] = "passed" if gate_result.returncode == 0 else "failed"
    compiled_pdf = output / f"{TEMPLATE.stem}.pdf"
    pdf = output / (f"{identity['slug']}.pdf" if args.mode == "combined" else "section.pdf")
    if compiled_pdf.is_file() and compiled_pdf != pdf:
        shutil.copy2(compiled_pdf, pdf)
    if gate_result.returncode or not pdf.is_file():
        report["status"] = "failed"
        report["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write_report(report, output / "build-report.json", history_root)
        return 1
    report["pdf"] = pdf.name
    report["pdf_sha256"] = sha256(pdf)
    renderer = Path(os.environ["REPORTKIT_PDF_PYTHON"]).expanduser() if os.environ.get("REPORTKIT_PDF_PYTHON") else output_root / ".venv" / "bin" / "python"
    if not renderer.is_absolute():
        renderer = (Path.cwd() / renderer).absolute()
    if not renderer.is_file():
        renderer = Path(sys.executable)
    pages = output / "pages"
    render = subprocess.run([str(renderer), str(SCRIPT_DIR / "render_pdf_pages.py"), str(pdf), str(pages), "--manifest", str(output / "page-manifest.json")], cwd=output, text=True)
    report["exit_codes"].append({"command": f"{renderer} {SCRIPT_DIR / 'render_pdf_pages.py'} {pdf}", "code": render.returncode})
    report["page_count"] = json.loads((output / "page-manifest.json").read_text(encoding="utf-8")).get("page_count") if render.returncode == 0 else None
    inspection = subprocess.run([str(renderer), str(SCRIPT_DIR / "inspect_pdf.py"), str(pdf), "--json", str(output / "pdf-inspection.json")], cwd=output, text=True)
    report["exit_codes"].append({"command": f"{renderer} {SCRIPT_DIR / 'inspect_pdf.py'} {pdf}", "code": inspection.returncode})
    if (output / "pdf-inspection.json").is_file():
        report["pdf_inspection"] = json.loads((output / "pdf-inspection.json").read_text(encoding="utf-8"))
    report["commands"].append(f"{renderer} {SCRIPT_DIR / 'inspect_pdf.py'} {pdf}")
    report["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report["status"] = "passed" if render.returncode == 0 and inspection.returncode == 0 else "failed"
    write_report(report, output / "build-report.json", history_root)
    if report["status"] == "passed":
        write_lock(source_root / "reportkit.lock", engine=engine, tool_versions=report["tool_versions"])
    return render.returncode or inspection.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("section", "combined", "sections"), required=True)
    parser.add_argument("--section")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--source-root", help=f"consumer publication project (default: {DEFAULT_SOURCE_ROOT})")
    parser.add_argument("--output-root", help="where build artefacts go (default: <source-root>/build)")
    parser.add_argument("--profile", default=os.environ.get("REPORTKIT_PROFILE"), help="publication config profile")
    parser.add_argument("--engine", default=os.environ.get("REPORTKIT_TEX_ENGINE"), help="TeX engine (default: publication config or pdflatex)")
    parser.add_argument("--version", default=os.environ.get("REPORTKIT_VERSION"), help=f"overrides version in {CONFIG_NAME}")
    parser.add_argument("--title", default=os.environ.get("REPORTKIT_TITLE"), help=f"overrides title in {CONFIG_NAME}")
    parser.add_argument("--author", default=os.environ.get("REPORTKIT_AUTHOR"), help=f"overrides author in {CONFIG_NAME}")
    parser.add_argument("--cover", help="reserved for a future cover-PDF prepend")
    args = parser.parse_args()
    if args.mode == "sections":
        root, _ = resolve_roots(args)
        result = validate_publication(root)
        if not result.ok:
            for error in result.errors:
                print(error, file=sys.stderr)
            return 1
        failures = 0
        for entry in order_entries(root):
            if entry.startswith("00-"):
                continue
            section_args = argparse.Namespace(**vars(args))
            section_args.mode, section_args.section = "section", entry
            failures |= build(section_args)
        return failures
    return build(args)


if __name__ == "__main__":
    raise SystemExit(main())
