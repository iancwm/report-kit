#!/usr/bin/env python3
"""Build one section, or the canonical combined publication, from a project.

The publication being built lives outside this repository: pass --source-root
at the consumer project and --output-root wherever its build artefacts belong.
See references/repository-boundary.md.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
try:
    import resource
except ImportError:  # pragma: no cover - ReportKit's pinned environment is Linux
    resource = None  # type: ignore[assignment]

try:
    from _bootstrap import ensure_reportkit_importable
except ImportError:  # imported as publication_pipeline.scripts.publication_build
    from ._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

from reportkit.publication_validation import validate_publication

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_ROOT.parent
# Phase A5: the entrypoint template is no longer a fixed module constant --
# build() resolves it per build from the publication registry's BuildTarget
# (publications.py's `template` field, selected by publication_type/theme)
# and stages/compiles it under a stable "publication.tex" name regardless of
# which entrypoint filename was selected. See build()'s `entrypoint` local.
LICENSE_FILE = REPO_ROOT / "metadata" / "licenses.yml"
# With no --source-root the pipeline builds its own generic example, so a bare
# invocation exercises the toolchain without assuming any real publication.
DEFAULT_SOURCE_ROOT = PIPELINE_ROOT / "example_publication"


def template_files() -> list[Path]:
    """Every ReportKit TeX input, flattened for TEXINPUTS by filename.

    Themes and publication types live in latex_templates/themes/ and
    latex_templates/publication_types/ respectively (see reportkit.cls's
    theme/publication-type architecture), one directory deeper than the rest
    of latex_templates/, so a plain top-level glob misses them. Flattening
    by filename here -- not preserving the subdirectory -- matches how
    reportkit.cls finds them: `\\RequirePackage{reportkit-theme-<name>}` /
    `\\RequirePackage{reportkit-<publication-type>}` both resolve by
    filename on TEXINPUTS, not by path.
    """
    templates = REPO_ROOT / "latex_templates"
    return (
        sorted(templates.glob("*.cls"))
        + sorted(templates.glob("*.def"))
        + sorted(templates.glob("reportkit-*.tex"))
        + sorted(templates.glob("*.sty"))
        + sorted(templates.glob("themes/*.sty"))
        + sorted(templates.glob("publication_types/*.sty"))
    )


from reportkit.authoring import render_links_tex, validate_authoring  # noqa: E402
from reportkit.authoring_ir import AuthoringValidationError  # noqa: E402
from reportkit.config import (  # noqa: E402
    CONFIG_NAME,
    load_publication_config,
    resolve_license,
    resolve_document,
    resolve_effective_theme,
    resolve_identity,
    resolve_output,
    resolve_theme,
    resolve_validation,
    theme_font_policy_conflict,
)
from reportkit.manifest import unique_build_id, write_report  # noqa: E402
from reportkit.diagnostics import diagnostic_envelope, inspect_log, make_diagnostic  # noqa: E402
from reportkit.latex import tex_escape  # noqa: E402
from reportkit.markdown_directives import parse_markdown, replace_placeholders  # noqa: E402
from reportkit.tex_renderer import render_ir  # noqa: E402
from reportkit.theme_overrides import ThemeOverrideError, materialize_tex_overrides  # noqa: E402
from reportkit.publications import PublicationRegistryError, resolve_build_target  # noqa: E402
from reportkit.toolchain import toolchain_context  # noqa: E402
from reportkit.toolchain import version_line  # noqa: E402
from reportkit.version import BUILD_REPORT_SCHEMA_VERSION  # noqa: E402
from reportkit.license_metadata import load_license_metadata, validate_license_metadata  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage_project_assets(source_root: Path, output: Path) -> list[dict[str, str]]:
    """Copy consumer-owned figures/assets into the isolated TeX build tree."""
    staged: list[dict[str, str]] = []
    for directory_name in ("figures", "assets"):
        directory = source_root / directory_name
        if not directory.is_dir():
            continue
        for source in sorted(path for path in directory.rglob("*") if path.is_file()):
            relative = source.relative_to(source_root)
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            staged.append({"path": str(relative), "sha256": sha256(source)})
    return staged


def stage_entrypoint(entrypoint: Path, destination: Path, *, theme: str, publication_type: str, class_name: str) -> None:
    """Stage a registry-selected entrypoint with its three safe substitutions.

    Pipeline templates are intentionally not general format strings. Only
    these exact placeholders are replaced, and all replacement values have
    already passed ``resolve_build_target()``'s registry validation.
    """
    text = entrypoint.read_text(encoding="utf-8")
    replacements = {
        "%%REPORTKIT_THEME%%": theme,
        "%%REPORTKIT_PUBLICATION_TYPE%%": publication_type,
        "%%REPORTKIT_CLASS%%": class_name,
    }
    for placeholder, value in replacements.items():
        count = text.count(placeholder)
        if count != 1:
            raise ValueError(
                f"{entrypoint}: expected exactly one {placeholder} placeholder, found {count}"
            )
        text = text.replace(placeholder, value)
    destination.write_text(text, encoding="utf-8")


def order_entries(root: Path) -> list[str]:
    return [line.strip() for line in (root / "manuscript" / "order.txt").read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]


def _resource_limiter(memory_limit_mb: int):
    if resource is None or not hasattr(resource, "RLIMIT_AS"):
        raise RuntimeError("this platform cannot enforce the required compile memory limit")
    limit = memory_limit_mb * 1024 * 1024

    def apply_limit() -> None:
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    return apply_limit


def run_limited(command: list[str], *, cwd: Path, timeout: int, memory_limit_mb: int, **kwargs):
    """Run an external build tool with ReportKit's mandatory resource limits."""
    forbidden = {"-shell-escape", "--shell-escape", "-enable-write18", "--enable-write18"}
    if any(part.split("=", 1)[0] in forbidden for part in command):
        raise ValueError("shell escape is forbidden by the ReportKit security contract")
    return subprocess.run(
        command, cwd=cwd, timeout=timeout, preexec_fn=_resource_limiter(memory_limit_mb), **kwargs,
    )


def render_markdown(
    root: Path,
    manuscript: Path,
    output: Path,
    map_path: Path | None = None,
    *,
    writer: str = "latex",
    publication_type: str | None = None,
    theme: str | None = None,
    renderer: str | None = None,
    links: list[str] | None = None,
    timeout: int = 120,
    memory_limit_mb: int = 2048,
) -> None:
    # --slide-level=1 (Beamer writer only): without it, Pandoc's own
    # heuristic ("the highest header level immediately followed by content")
    # can make a level-1 heading a section-navigation slide instead of a
    # frame, depending on whether any level-2 headings exist anywhere in the
    # document -- ambiguous and content-dependent. Forcing level 1 makes
    # every top-level heading an unambiguous \begin{frame}{...}, matching
    # B1's "plain Markdown frames" authoring path (reportkit-presentation.sty
    # compositions are the separate directive/fragment-based path -- see
    # that file's own header). Meaningless for the latex writer, so only
    # added for beamer.
    slide_level = ["--slide-level=1"] if writer == "beamer" else []
    source = manuscript.read_text(encoding="utf-8")
    parsed = parse_markdown(source, source_file=str(manuscript.relative_to(root)))
    if parsed.diagnostics:
        raise AuthoringValidationError(parsed.diagnostics)
    # Directive TeX is generated and inserted after Pandoc.  Consequently it
    # never becomes a raw-TeX extension in the Markdown reader, while ordinary
    # Markdown continues through the existing markdown-raw_tex restriction.
    replacements = render_ir(
        parsed.ir,
        fragment_root=root,
        publication_type=publication_type,
        theme=theme,
        renderer=renderer,
        links=set(links or ()),
    )
    def run_pandoc(input_path: Path):
        # Raw TeX is deliberately disabled in Markdown. Trusted TeX belongs in
        # a validated fragment or a direct .tex document, never a content field.
        # `writer` comes from the resolved BuildTarget's pandoc_writer (Phase
        # A5, decision D3: Python is canonical) -- "latex" for the paged
        # renderer (unchanged), "beamer" for slides.
        return run_limited(
            ["pandoc", "-f", "markdown-raw_tex", "-t", writer, *slide_level, str(input_path)],
            cwd=root.parent, timeout=timeout, memory_limit_mb=memory_limit_mb, capture_output=True, text=True,
        )

    pandoc_output: list[str] = []
    if writer == "beamer" and parsed.directives:
        # Beamer's frame environment scans the literal Pandoc output.  A
        # directive marker inside one Pandoc invocation would therefore land
        # inside the preceding Markdown frame.  Separate ordinary Markdown
        # segments ensure every generated composition is inserted between
        # complete frame batches.  This also permits a directive-only deck to
        # render without an unnecessary Pandoc call.
        markers = sorted(parsed.placeholders, key=len, reverse=True)
        marker_pattern = re.compile(rf"(?m)^({'|'.join(re.escape(marker) for marker in markers)})[ \t]*\n?")
        cursor = 0
        for match in marker_pattern.finditer(parsed.markdown):
            segment = parsed.markdown[cursor:match.start()]
            if segment.strip():
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", suffix=".md", prefix=".reportkit-", dir=output.parent, delete=False,
                ) as stream:
                    stream.write(segment)
                    segment_path = Path(stream.name)
                try:
                    proc = run_pandoc(segment_path)
                finally:
                    segment_path.unlink(missing_ok=True)
                if proc.returncode:
                    raise RuntimeError(proc.stderr or f"Pandoc failed for {manuscript}")
                pandoc_output.append(proc.stdout)
            pandoc_output.append(match.group(1) + "\n")
            cursor = match.end()
        tail = parsed.markdown[cursor:]
        if tail.strip():
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".md", prefix=".reportkit-", dir=output.parent, delete=False,
            ) as stream:
                stream.write(tail)
                tail_path = Path(stream.name)
            try:
                proc = run_pandoc(tail_path)
            finally:
                tail_path.unlink(missing_ok=True)
            if proc.returncode:
                raise RuntimeError(proc.stderr or f"Pandoc failed for {manuscript}")
            pandoc_output.append(proc.stdout)
        pandoc_text = "\n".join(pandoc_output)
    else:
        pandoc_input = manuscript
        temporary_input: Path | None = None
        if parsed.directives:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".md", prefix=".reportkit-", dir=output.parent, delete=False,
            ) as stream:
                stream.write(parsed.markdown)
                temporary_input = Path(stream.name)
            pandoc_input = temporary_input
        try:
            proc = run_pandoc(pandoc_input)
        finally:
            if temporary_input is not None:
                temporary_input.unlink(missing_ok=True)
        if proc.returncode:
            raise RuntimeError(proc.stderr or f"Pandoc failed for {manuscript}")
        pandoc_text = proc.stdout
    source_lines = source.splitlines()
    source_locations = {
        match.group(1): line_number
        for line_number, raw in enumerate(source_lines, 1)
        if (match := re.search(r"REPORTKIT-VISUAL:fig:([a-z0-9]+(?:-[a-z0-9]+)*)", raw))
    }
    lines: list[str] = []
    fragments: list[dict[str, object]] = []
    directives: list[dict[str, object]] = []
    for line in pandoc_text.splitlines():
        directive_marker = next((marker for marker in replacements if marker in line), None)
        if directive_marker is not None:
            generated_start = len(lines) + 1
            replacement = replacements[directive_marker]
            if line.strip() == directive_marker:
                lines.extend(replacement.splitlines())
            else:
                lines.extend(replace_placeholders(line, replacements).splitlines())
            generated_end = generated_start + max(0, len(replacement.splitlines()) - 1)
            node = parsed.placeholders[directive_marker]
            directives.append({
                "start": generated_start,
                "end": generated_end,
                "generated_start": generated_start,
                "generated_end": generated_end,
                "source_start": node.source.line,
                "source_end": node.source.line_end,
                "primitive": node.primitive,
                "path": node.fragment,
                "trusted_fragment": bool(node.fragment),
            })
            continue
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
    sidecar.write_text(json.dumps({"source": str(manuscript.relative_to(root)), "fragments": fragments, "directives": directives}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_publication_date(value: str, *, now: datetime | None = None) -> str:
    """Resolve a configured publication date, including the dynamic build date."""
    if value != "build":
        return value
    current = now if now is not None else datetime.now().astimezone()
    return f"{current.day} {current.strftime('%B %Y')}"


def write_metadata(path: Path, *, identity: dict[str, str], combined: bool, license_values: dict[str, str], cover_name: str | None, uses_tables: bool, uses_code: bool) -> None:
    """Emit the publication's identity as LaTeX macros.

    Every value here comes from the consumer project's publication.yaml or the
    CLI. Nothing about a specific publication is hard-coded in this engine.
    """
    publication_date = _resolve_publication_date(identity.get("date", ""))
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
        f"\\newcommand{{\\RKPubDate}}{{{tex_escape(publication_date)}}}",
        f"\\newcommand{{\\RKPubLeftHeader}}{{{tex_escape(identity['left_header'])}}}",
        f"\\newcommand{{\\RKPubFooter}}{{{tex_escape(identity['footer'])}}}",
        f"\\newcommand{{\\RKPubSubject}}{{{tex_escape(identity['subject'])}}}",
        f"\\newcommand{{\\RKPubKeywords}}{{{tex_escape(identity['keywords'])}}}",
        # These macros are consumed by \RKPath/\href after expansion, so
        # escape configured URLs at definition time just like other metadata.
        f"\\newcommand{{\\RKPubProjectURL}}{{{tex_escape(identity['project_url'])}}}",
        f"\\newcommand{{\\RKPubContentLicense}}{{{tex_escape(license_values['content_license'])}}}",
        f"\\newcommand{{\\RKPubContentLicenseURL}}{{{tex_escape(license_values['content_license_url'])}}}",
        f"\\newcommand{{\\RKPubClassification}}{{{tex_escape(license_values.get('classification', ''))}}}",
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


def write_lock(path: Path, *, engine: str, tool_versions: dict[str, str], toolchain: dict) -> None:
    """Pin the engine and toolchain the publication was built against."""
    lock = {
        "schema_version": 2,
        "reportkit_ref": git_value(["describe", "--tags", "--always"]),
        "reportkit_commit": git_value(["rev-parse", "HEAD"]),
        "tex_engine": engine,
        "pandoc": tool_versions.get("pandoc", "unknown"),
        "python": tool_versions.get("python", "unknown"),
        "toolchain_fingerprint": toolchain["fingerprint"],
        "toolchain": toolchain,
    }
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fail(
    report: dict[str, object], diagnostics: dict[str, object], code: int,
    *, report_path: Path | None = None, history_root: Path | None = None,
) -> int:
    """Finalize a failed build and optionally persist its report.

    Keeping this transition in one place makes every compile, gate, render,
    and inspection failure produce the same terminal report shape. The path
    arguments stay optional so stage-level callers and unit tests can use the
    state transition without touching the filesystem.
    """
    report["status"] = "failed"
    report["diagnostics"] = diagnostics
    report["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if report_path is not None:
        write_report(report, report_path, history_root)
    return code


def run(command: list[str], cwd: Path, log: Path, *, timeout: int = 120, memory_limit_mb: int = 2048) -> int:
    with log.open("a", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(command) + "\n")
        proc = run_limited(command, cwd=cwd, timeout=timeout, memory_limit_mb=memory_limit_mb, stdout=stream, stderr=subprocess.STDOUT, text=True)
    return proc.returncode


def resolve_roots(args: argparse.Namespace) -> tuple[Path, Path]:
    """Locate the publication and where its artefacts go.

    Both default into the consumer project, never into this repository, so a
    build cannot silently write publication output back into the engine.
    """
    source_root = Path(args.source_root).resolve() if args.source_root else DEFAULT_SOURCE_ROOT
    if args.output_root:
        output_root = Path(args.output_root).resolve()
    else:
        config = load_publication_config(source_root / CONFIG_NAME)
        output_root = resolve_output(config, source_root, getattr(args, "profile", None)) or source_root / "build"
    return source_root, output_root


def build(args: argparse.Namespace) -> int:
    source_root, output_root = resolve_roots(args)
    profile = getattr(args, "profile", None)
    timeout = int(getattr(args, "compile_timeout_seconds", 120))
    memory_limit_mb = int(getattr(args, "memory_limit_mb", 2048))
    if timeout <= 0 or memory_limit_mb <= 0:
        print("compile timeout and memory limit must be positive", file=sys.stderr)
        return 2
    if resource is None or not hasattr(resource, "RLIMIT_AS"):
        print("environment: this platform cannot enforce the required compile memory limit", file=sys.stderr)
        return 5
    validation = validate_publication(source_root)
    if not validation.ok:
        for error in validation.errors:
            print(f"publication validation: {error}", file=sys.stderr)
        return 3
    authoring = validate_authoring(source_root)
    if not authoring.ok:
        for error in authoring.errors:
            print(f"authoring validation: {error}", file=sys.stderr)
        return 3
    try:
        license_defaults = load_license_metadata(LICENSE_FILE)
    except (OSError, ValueError) as exc:
        print(f"licensing: {exc}", file=sys.stderr)
        return 2
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
    try:
        license_values = resolve_license(config, license_defaults, profile=profile)
        validate_license_metadata(license_values, source_root / CONFIG_NAME)
    except (OSError, ValueError) as exc:
        print(f"licensing: {exc}", file=sys.stderr)
        return 2
    document = resolve_document(config, profile)
    engine = str(getattr(args, "engine", None) or os.environ.get("REPORTKIT_TEX_ENGINE") or document.get("engine", "pdflatex"))
    try:
        target = resolve_build_target(
            str(document.get("publication_type")),
            str(document.get("theme")),
            explicit_paper=document.get("paper"),
            engine=engine,
            repo_root=REPO_ROOT,
        )
    except PublicationRegistryError as exc:
        print(f"publication config: {exc}", file=sys.stderr)
        return 2
    # Phase A5: the resolved BuildTarget is canonical (decision D3) --
    # `engine` above is the same value once resolve_build_target accepts it
    # (it never falls back to the theme's required engine here, since
    # `engine` is never empty), but target.engine is used from this point on
    # so the compiled command and the reported selection can never diverge.
    engine = target.engine
    entrypoint = PIPELINE_ROOT / "templates" / target.template
    if not entrypoint.is_file():
        print(f"publication config: resolved template does not exist: {entrypoint}", file=sys.stderr)
        return 2
    # Machine-readable and log-visible resolved-selection marker (A5): PDF
    # inspection / a human reviewing the compile log can use this line to
    # catch default-theme leakage -- a build that silently fell back to
    # "default"/"technical-report" when something else was requested.
    selection_marker = (
        f"REPORTKIT-SELECTED publication_type={target.publication_type} "
        f"requested_theme={target.requested_theme} theme={target.theme} "
        f"renderer={target.renderer} class={target.class_name} "
        f"template={target.template} writer={target.pandoc_writer} "
        f"engine={target.engine} "
        f"paper={target.paper if target.paper else '-'} "
        f"canvas={target.canvas if target.canvas else '-'}"
    )
    print(selection_marker)
    font_policy_conflict = theme_font_policy_conflict(resolve_theme(config, profile))
    if font_policy_conflict:
        print(f"publication config: {font_policy_conflict}", file=sys.stderr)
        return 2
    try:
        effective_theme = resolve_effective_theme(
            config,
            source_root=source_root,
            profile=profile,
            theme=target.requested_theme,
        )
    except (OSError, ThemeOverrideError, ValueError) as exc:
        print(f"publication config: theme/brand overrides: {exc}", file=sys.stderr)
        return 2
    entries = order_entries(source_root)
    if args.mode == "section":
        chosen = getattr(args, "section", None)
        if not chosen:
            print("--section is required in section mode", file=sys.stderr)
            return 2
        chosen_path = Path(chosen)
        if chosen_path.is_absolute() or ".." in chosen_path.parts or chosen_path.suffix != ".md":
            print(f"--section must name a Markdown file inside manuscript/: {chosen!r}", file=sys.stderr)
            return 2
        manuscripts = [chosen_path]
    else:
        manuscripts = [Path(entry) for entry in entries]
    for manuscript in manuscripts:
        if not (source_root / "manuscript" / manuscript).is_file():
            print(f"missing manuscript: {manuscript}", file=sys.stderr)
            return 3
    stamp = time.strftime("%Y%m%d-%H%M%S")
    history_root = output_root / "history"
    # F2 bounded parallelism: two sections built concurrently can resolve the
    # same mode+stamp before either has written its history file, so a
    # build-id keyed on mode alone ("section-<stamp>") is a check-then-act
    # race under --workers > 1. Keying on the manuscript stem too makes
    # concurrent sections' candidates distinct from the start; the
    # pre-existing collision index in unique_build_id still covers the rare
    # case of the same section built twice within one second.
    build_id_mode = f"section-{Path(manuscripts[0]).stem}" if args.mode == "section" else args.mode
    build_id = unique_build_id(build_id_mode, stamp, history_root)
    output = output_root / ("combined" if args.mode == "combined" else f"section-{Path(manuscripts[0]).stem}-{stamp}")
    if output.exists() and args.mode != "combined":
        output = output_root / build_id
    output.mkdir(parents=True, exist_ok=True)
    for path in template_files():
        shutil.copy2(path, output / path.name)
    # Stable staged/compiled filename (A5), independent of which entrypoint
    # source template was selected -- downstream packaging/inspection reads
    # "publication.tex"/"publication.pdf" regardless of publication_type.
    try:
        stage_entrypoint(
            entrypoint,
            output / "publication.tex",
            theme=target.requested_theme,
            publication_type=target.publication_type,
            class_name=target.class_name,
        )
    except (OSError, ValueError) as exc:
        print(f"publication config: could not stage resolved entrypoint: {exc}", file=sys.stderr)
        return 2
    # Per-renderer shared base files an entrypoint may \input{} (D7) -- e.g.
    # slides-base.tex for presentation.tex. publication-template.tex is
    # still self-contained (no *-base.tex dependency), so this is a no-op
    # for the paged renderer today; staged unconditionally (cheap, and every
    # renderer eventually gets one) rather than special-cased per renderer.
    for base_file in (PIPELINE_ROOT / "templates").glob("*-base.tex"):
        shutil.copy2(base_file, output / base_file.name)
    staged_assets = stage_project_assets(source_root, output)
    if effective_theme.brand.logo:
        try:
            logo_relative = effective_theme.brand.logo.relative_to(source_root).as_posix()
        except ValueError as exc:
            print(f"publication config: brand.logo escaped the publication root: {exc}", file=sys.stderr)
            return 2
        if not any(item["path"] == logo_relative for item in staged_assets):
            logo_destination = output / logo_relative
            logo_destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(effective_theme.brand.logo, logo_destination)
            except OSError as exc:
                print(f"publication config: could not stage brand.logo: {exc}", file=sys.stderr)
                return 2
            staged_assets.append({"path": logo_relative, "sha256": sha256(effective_theme.brand.logo)})
    if effective_theme.configured:
        try:
            materialize_tex_overrides(effective_theme, output / "reportkit-theme-overrides.tex")
        except (OSError, ThemeOverrideError, ValueError) as exc:
            print(f"publication config: could not materialize theme overrides: {exc}", file=sys.stderr)
            return 2
    cover_name = None
    if args.cover:
        cover = Path(args.cover).resolve()
        try:
            cover.relative_to(source_root)
        except ValueError:
            print(f"cover must be inside the publication root: {cover}", file=sys.stderr)
            return 2
        if not cover.is_file() or cover.suffix.lower() != ".pdf":
            print(f"cover must be an existing PDF inside the publication root: {cover}", file=sys.stderr)
            return 2
        cover_name = "reportkit-cover.pdf"
        shutil.copy2(cover, output / cover_name)
    body_files = []
    for index, manuscript in enumerate(manuscripts):
        rendered = output / f"body-{index:02d}.tex"
        try:
            render_markdown(
                source_root, source_root / "manuscript" / manuscript, rendered,
                writer=target.pandoc_writer,
                publication_type=target.publication_type,
                theme=target.requested_theme,
                renderer=target.renderer,
                links=authoring.links,
                timeout=timeout,
                memory_limit_mb=memory_limit_mb,
            )
        except subprocess.TimeoutExpired:
            print(f"compile timeout: pandoc exceeded {timeout} seconds", file=sys.stderr)
            return 4
        except FileNotFoundError:
            print("environment: pandoc is not installed", file=sys.stderr)
            return 5
        except AuthoringValidationError as exc:
            for diagnostic in exc.diagnostics:
                print(f"authoring validation: {diagnostic['message']}", file=sys.stderr)
            return 3
        except RuntimeError as exc:
            print(f"compile failure: {exc}", file=sys.stderr)
            return 4
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
    tex = output / "publication.tex"
    log = output / "publication.log"
    validation_config = resolve_validation(config, profile)
    figure_count = sum(len(re.findall(r"REPORTKIT-VISUAL:fig:[a-z0-9]+(?:-[a-z0-9]+)*", text)) for text in ((source_root / "manuscript" / path).read_text(encoding="utf-8") for path in manuscripts))
    table_count = len(re.findall(r"(?m)^\s*\|.*\n\s*\|?\s*:?-{3,}", manuscript_text))
    report = {
        "schema_version": BUILD_REPORT_SCHEMA_VERSION,
        "build_id": build_id,
        "mode": args.mode,
        "profile": profile or "draft",
        "version": identity["version"],
        "commit": git_value(["rev-parse", "HEAD"]),
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": [{"path": str(path), "sha256": sha256(source_root / "manuscript" / path)} for path in manuscripts],
        "templates": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256(path)} for path in (template_files() + [entrypoint, LICENSE_FILE])],
        "assets": staged_assets,
        "tool_versions": {"python": sys.version.split()[0], "pandoc": version_line("pandoc") or "not found", "tex": version_line(engine) or "not found"},
        "toolchain": toolchain_context(REPO_ROOT),
        # Phase A5: the resolved build target, so a build report is self-
        # describing about which renderer/theme/template/writer actually
        # produced it (requested vs. canonical theme distinguishes an alias
        # like "technical" from what actually rendered).
        "selection": target.as_dict(),
        "effective_theme": effective_theme.as_dict(),
        "commands": [], "exit_codes": [], "diagnostics": {}, "figures": figure_count, "tables": table_count, "pdf_sha256": None,
    }
    report_path = output / "build-report.json"
    templates_root = REPO_ROOT / "latex_templates"
    # Keep the TeX search path explicit: the staged output plus the known
    # class/theme/publication roots are the complete ReportKit input surface.
    texinputs = f"{output}:{templates_root}:{templates_root / 'themes'}:{templates_root / 'publication_types'}:"
    for pass_number in range(1, 3):
        command = [engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name]
        report["commands"].append(" ".join(command))
        env = dict(
            os.environ,
            TEXINPUTS=texinputs,
            # luaotfload reads the installed Unicode ScriptExtensions.txt and
            # Scripts.txt through Lua's file API during LuaLaTeX startup. The
            # pinned TeX Live toolchain cannot resolve those absolute
            # kpathsea paths under paranoid input mode; the visual-QA
            # LuaLaTeX runners use the same setting. Markdown and fragment
            # validation still constrain all user-controlled inputs, and
            # output writes remain restricted below.
            openin_any="a" if engine == "lualatex" else "p",
            openout_any="p",
            # The pinned luaotfload build can fail while loading its
            # multiscript module under the runner's C.UTF-8 locale.  Keep
            # every normal-pipeline TeX invocation on the same stable C
            # locale as the renderer and acceptance-test subprocesses.
            LC_ALL="C",
            SOURCE_DATE_EPOCH="1",
            FORCE_SOURCE_DATE="1",
            TZ="UTC",
        )
        pass_log = output / f"publication-pass-{pass_number}.log"
        with pass_log.open("w", encoding="utf-8") as stream:
            stream.write("$ " + " ".join(command) + "\n")
            try:
                proc = run_limited(
                    command, cwd=output, timeout=timeout, memory_limit_mb=memory_limit_mb,
                    env=env, stdout=stream, stderr=subprocess.STDOUT, text=True,
                )
            except subprocess.TimeoutExpired:
                return _fail(report, diagnostic_envelope([
                    make_diagnostic("compile_timeout", f"{engine} pass {pass_number} exceeded {timeout} seconds", code="RK_COMPILE_TIMEOUT")
                ], passed=False), 4, report_path=report_path, history_root=history_root)
            except FileNotFoundError:
                return _fail(report, diagnostic_envelope([
                    make_diagnostic("environment_error", f"TeX engine {engine!r} is not installed", code="RK_TEX_ENGINE_MISSING")
                ], passed=False), 5, report_path=report_path, history_root=history_root)
        report["exit_codes"].append({"command": " ".join(command), "code": proc.returncode})
        if proc.returncode:
            diagnostics = inspect_log(pass_log.read_text(encoding="utf-8", errors="replace"))
            if not diagnostics["diagnostics"]:
                memory_failure = proc.returncode < 0 or proc.returncode in {134, 137}
                diagnostics = diagnostic_envelope([
                    make_diagnostic(
                        "compile_memory" if memory_failure else "compile_failure",
                        f"{engine} exited with status {proc.returncode}",
                        code="RK_COMPILE_MEMORY" if memory_failure else "RK_COMPILE_FAILURE",
                    )
                ], passed=False)
            return _fail(report, diagnostics, 4, report_path=report_path, history_root=history_root)
        if pass_number == 2:
            shutil.copy2(pass_log, log)
            # Log-visible half of the resolved-selection marker (the other
            # half is the stdout print() above, which --json mode's stdout
            # capture does not surface in the payload). Appended after the
            # copy, not written into pass_log, so it cannot affect
            # inspect_log()'s/check_build_log.py's diagnostic parsing.
            with log.open("a", encoding="utf-8") as stream:
                stream.write("\n" + selection_marker + "\n")
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
    try:
        gate_result = run_limited(
            gate_command, cwd=output, timeout=timeout, memory_limit_mb=memory_limit_mb,
            capture_output=True, text=True,
        )
    except subprocess.TimeoutExpired:
        return _fail(report, diagnostic_envelope([
            make_diagnostic("compile_timeout", "diagnostic gate timed out", code="RK_DIAGNOSTIC_TIMEOUT")
        ], passed=False), 4, report_path=report_path, history_root=history_root)
    report["exit_codes"].append({"command": f"{sys.executable} {gate} {log}", "code": gate_result.returncode})
    report["diagnostics"] = json.loads((output / "diagnostics.json").read_text(encoding="utf-8"))
    report["gate"] = "passed" if gate_result.returncode == 0 else "failed"
    compiled_pdf = output / "publication.pdf"
    pdf = output / (f"{identity['slug']}.pdf" if args.mode == "combined" else "section.pdf")
    if compiled_pdf.is_file() and compiled_pdf != pdf:
        shutil.copy2(compiled_pdf, pdf)
    if gate_result.returncode or not pdf.is_file():
        return _fail(report, report["diagnostics"], 3, report_path=report_path, history_root=history_root)  # type: ignore[arg-type]
    report["pdf"] = pdf.name
    report["pdf_sha256"] = sha256(pdf)
    renderer = Path(os.environ["REPORTKIT_PDF_PYTHON"]).expanduser() if os.environ.get("REPORTKIT_PDF_PYTHON") else output_root / ".venv" / "bin" / "python"
    if not renderer.is_absolute():
        renderer = (Path.cwd() / renderer).absolute()
    if not renderer.is_file():
        renderer = Path(sys.executable)
    pages = output / "pages"
    render_command = [str(renderer), str(SCRIPT_DIR / "render_pdf_pages.py"), str(pdf), str(pages), "--manifest", str(output / "page-manifest.json")]
    try:
        render = run_limited(
            render_command, cwd=output, timeout=timeout, memory_limit_mb=memory_limit_mb,
            capture_output=True, text=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        kind = "compile_timeout" if isinstance(exc, subprocess.TimeoutExpired) else "environment_error"
        return _fail(report, diagnostic_envelope([
            make_diagnostic(kind, f"page rendering failed: {exc}", code="RK_RENDER_FAILED")
        ], passed=False), 4 if isinstance(exc, subprocess.TimeoutExpired) else 5, report_path=report_path, history_root=history_root)
    report["exit_codes"].append({"command": f"{renderer} {SCRIPT_DIR / 'render_pdf_pages.py'} {pdf}", "code": render.returncode})
    if render.returncode:
        return _fail(report, diagnostic_envelope([
            make_diagnostic(
                "pdf_geometry", f"page renderer exited with status {render.returncode}",
                code="RK_RENDER_FAILED", details={"stderr": (render.stderr or "")[-4000:]},
            )
        ], passed=False), 3, report_path=report_path, history_root=history_root)
    report["page_count"] = json.loads((output / "page-manifest.json").read_text(encoding="utf-8")).get("page_count")
    inspection_command = [str(renderer), str(SCRIPT_DIR / "inspect_pdf.py"), str(pdf), "--json", str(output / "pdf-inspection.json")]
    try:
        inspection = run_limited(
            inspection_command, cwd=output, timeout=timeout, memory_limit_mb=memory_limit_mb,
            capture_output=True, text=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        kind = "compile_timeout" if isinstance(exc, subprocess.TimeoutExpired) else "environment_error"
        return _fail(report, diagnostic_envelope([
            make_diagnostic(kind, f"PDF inspection failed: {exc}", code="RK_INSPECTION_FAILED")
        ], passed=False), 4 if isinstance(exc, subprocess.TimeoutExpired) else 5, report_path=report_path, history_root=history_root)
    report["exit_codes"].append({"command": f"{renderer} {SCRIPT_DIR / 'inspect_pdf.py'} {pdf}", "code": inspection.returncode})
    if (output / "pdf-inspection.json").is_file():
        report["pdf_inspection"] = json.loads((output / "pdf-inspection.json").read_text(encoding="utf-8"))
    if inspection.returncode:
        nested = report.get("pdf_inspection", {})
        diagnostics = nested if isinstance(nested, dict) and nested.get("diagnostics") else diagnostic_envelope([
            make_diagnostic(
                "pdf_geometry", f"PDF inspector exited with status {inspection.returncode}",
                code="RK_INSPECTION_FAILED", details={"stderr": (inspection.stderr or "")[-4000:]},
            )
        ], passed=False)
        return _fail(report, diagnostics, 5 if inspection.returncode == 5 else 3, report_path=report_path, history_root=history_root)
    report["commands"].append(f"{renderer} {SCRIPT_DIR / 'inspect_pdf.py'} {pdf}")
    report["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report["status"] = "passed" if render.returncode == 0 and inspection.returncode == 0 else "failed"
    write_report(report, output / "build-report.json", history_root)
    if report["status"] == "passed":
        write_lock(source_root / "reportkit.lock", engine=engine, tool_versions=report["tool_versions"], toolchain=report["toolchain"])
    return 0 if report["status"] == "passed" else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("section", "combined", "sections"), required=True)
    parser.add_argument("--section")
    parser.add_argument("--workers", type=int, default=1, help="bounded parallel section builds in --mode sections (F2)")
    parser.add_argument("--source-root", help=f"consumer publication project (default: {DEFAULT_SOURCE_ROOT})")
    parser.add_argument("--output-root", help="where build artefacts go (default: <source-root>/build)")
    parser.add_argument("--profile", default=os.environ.get("REPORTKIT_PROFILE"), help="publication config profile")
    parser.add_argument("--engine", default=os.environ.get("REPORTKIT_TEX_ENGINE"), help="TeX engine (default: publication config or pdflatex)")
    parser.add_argument("--version", default=os.environ.get("REPORTKIT_VERSION"), help=f"overrides version in {CONFIG_NAME}")
    parser.add_argument("--title", default=os.environ.get("REPORTKIT_TITLE"), help=f"overrides title in {CONFIG_NAME}")
    parser.add_argument("--author", default=os.environ.get("REPORTKIT_AUTHOR"), help=f"overrides author in {CONFIG_NAME}")
    parser.add_argument("--cover", help="reserved for a future cover-PDF prepend")
    parser.add_argument("--compile-timeout-seconds", type=int, default=os.environ.get("REPORTKIT_COMPILE_TIMEOUT_SECONDS", "120"))
    parser.add_argument("--memory-limit-mb", type=int, default=os.environ.get("REPORTKIT_MEMORY_LIMIT_MB", "2048"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        print("--workers must be at least 1", file=sys.stderr)
        return 2

    _, initial_output_root = resolve_roots(args)
    prior_reports = {
        path.resolve(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in initial_output_root.glob("**/build-report.json")
        if path.is_file()
    }

    def execute() -> int:
        if args.mode == "sections":
            root, _ = resolve_roots(args)
            result = validate_publication(root)
            if not result.ok:
                for error in result.errors:
                    print(error, file=sys.stderr)
                return 3
            pending = [entry for entry in order_entries(root) if not entry.startswith("00-")]
            section_args_list = []
            for entry in pending:
                section_args = argparse.Namespace(**vars(args))
                section_args.mode, section_args.section = "section", entry
                section_args_list.append(section_args)
            if args.workers == 1 or len(pending) <= 1:
                codes = [build(section_args) for section_args in section_args_list]
            else:
                # F2: each section's build() call is dominated by external
                # subprocess time (pandoc, TeX compiled twice, the PDF
                # renderer, the PDF inspector), which releases the GIL while
                # it waits -- threads, not processes, already parallelise
                # the real bottleneck without paying an extra interpreter
                # import per section. Bounded by --workers, and capped at
                # len(pending) so an oversized --workers never spins up
                # idle threads. ThreadPoolExecutor.map preserves input
                # order in its results regardless of completion order, so
                # the aggregate below stays deterministic under concurrency.
                with ThreadPoolExecutor(max_workers=min(args.workers, len(pending))) as pool:
                    codes = list(pool.map(build, section_args_list))
            # Deterministic aggregate reporting (F2): the summary below
            # lists sections in manuscript order and ORs their exit codes,
            # so both the printed report and the aggregate exit code are the
            # same on every run regardless of which worker finished first.
            failure = 0
            for entry, code in zip(pending, codes):
                failure = failure or code
                print(f"REPORTKIT-SECTION {entry}: exit {code}")
            return failure
        return build(args)

    if not args.json:
        return execute()
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = execute()
        except Exception as exc:  # structured last-resort boundary for the script facade
            code = 70
            print(str(exc), file=sys.stderr)
    _, output_root = resolve_roots(args)
    candidates = [output_root / "combined" / "build-report.json"]
    candidates.extend(sorted(output_root.glob("section-*/build-report.json"), reverse=True))
    report_path = next((
        path for path in candidates
        if path.is_file()
        and prior_reports.get(path.resolve()) != (path.stat().st_mtime_ns, path.stat().st_size)
    ), None)
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path else None
    nested = report.get("diagnostics", {}) if isinstance(report, dict) else {}
    diagnostics = list(nested.get("diagnostics", nested.get("issues", []))) if isinstance(nested, dict) else []
    message = stderr.getvalue().strip() or stdout.getvalue().strip()
    if code and not diagnostics:
        kind = {2: "configuration_error", 3: "publication_validation", 4: "compile_failure", 5: "environment_error"}.get(code, "internal_error")
        diagnostics = [make_diagnostic(kind, message or "publication build failed", code={
            2: "RK_BUILD_CONFIG", 3: "RK_BUILD_VALIDATION", 4: "RK_BUILD_COMPILE", 5: "RK_BUILD_ENVIRONMENT",
        }.get(code, "RK_BUILD_INTERNAL"))]
    payload = diagnostic_envelope(
        diagnostics, passed=code == 0, exit_code=code, report=report,
        report_path=str(report_path) if report_path else None,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
