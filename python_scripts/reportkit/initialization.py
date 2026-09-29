"""Initialize a consumer project without copying ReportKit into it."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import subprocess
import tarfile

from .authoring_templates import document_template
from .publications import PUBLICATION_TYPES


PROJECT_DIRECTORIES = ("manuscript", "fragments", "assets", "figures", "build", "output")
DIRECTORIES = PROJECT_DIRECTORIES
ORDER_FILE = """# One manuscript filename per line, in reading order.
# Example:
# 01-introduction.md
# 02-background.md
"""
ORDER_CONTENT = ORDER_FILE
PUBLICATION_CONFIG = """# Publication identity -- read by ReportKit's publication pipeline.
# title is required; everything else is optional and falls back sensibly.
title:
# subtitle:
# author:
# version:
# left_header:
# footer:
# subject:
# keywords:
# disclaimer:
# project_url:
document:
  publication_type:   # REQUIRED: run `reportkit target set` (see SKILL.md selection table)
  theme:
validation:
  require_declared_target: true
"""
PUBLICATION_CONTENT = PUBLICATION_CONFIG


@dataclass(frozen=True)
class InitResult:
    """Describe the files and directories created by :func:`initialize`."""

    target: Path
    created: tuple[str, ...]


def ensure_outside_repository(target: Path, repo_root: Path) -> Path:
    """Resolve *target* and reject paths inside the ReportKit checkout."""
    target = target.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()
    if target == repo_root or repo_root in target.parents:
        raise ValueError(
            f"REFUSING: work dir ({target}) is inside the ReportKit clone ({repo_root}).\n"
            "ReportKit is a reusable engine; publications live in a separate "
            "consumer project, never inside this repository. Pick a work dir "
            "outside the clone. See references/repository-boundary.md."
        )
    return target


def initialize_project(target: Path, repo_root: Path) -> tuple[Path, list[str]]:
    """Create standard consumer directories and starter files without overwriting content."""
    target = ensure_outside_repository(target, repo_root)
    target.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for name in PROJECT_DIRECTORIES:
        directory = target / name
        if not directory.exists():
            directory.mkdir()
            created.append(f"{name}/")
        elif not directory.is_dir():
            raise ValueError(f"cannot initialize {target}: {directory} exists and is not a directory")

    for name, contents in (("manuscript/order.txt", ORDER_FILE), ("publication.yaml", PUBLICATION_CONFIG)):
        path = target / name
        if not path.exists():
            path.write_text(contents, encoding="utf-8")
            created.append(name)
        elif not path.is_file():
            raise ValueError(f"cannot initialize {target}: {path} exists and is not a file")
    return target, created


def initialize(target: Path, repo_root: Path) -> InitResult:
    """Scaffold a consumer project and return a structured result for callers."""
    resolved, created = initialize_project(target, repo_root)
    return InitResult(target=resolved, created=tuple(created))


def scaffold_target(
    target: Path, publication_type: str, theme: str, source_mode: str, *, main: str = "report.tex",
) -> tuple[str, ...]:
    """Create a target-specific starter and composition brief without overwriting.

    This is called only when ``reportkit init`` receives target flags. The
    template is derived from the target's canonical opening grammar; the
    brief is copied from its canonical example with the reference left blank
    for the consumer to fill in.
    """
    root = Path(target).resolve()
    if publication_type not in PUBLICATION_TYPES:
        raise ValueError(f"unknown publication type {publication_type!r}")
    record = PUBLICATION_TYPES[publication_type]
    repository = Path(__file__).resolve().parents[2]
    created: list[str] = []

    if source_mode == "tex":
        destination = (root / main).resolve()
        if destination != root and root not in destination.parents:
            raise ValueError("document.main must stay inside the consumer project")
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            starter = document_template(publication_type, theme)
            starter = starter.replace("{{body}}", "% TODO: author the target-specific composition here.\n")
            destination.write_text(starter, encoding="utf-8")
            created.append(str(destination.relative_to(root)))
    elif source_mode == "markdown":
        manuscript = root / "manuscript"
        manuscript.mkdir(parents=True, exist_ok=True)
        source = manuscript / "01-introduction.md"
        if not source.exists():
            source.write_text(
                "# Start with the reader's question\n\n"
                "State the main point, then support it with evidence and sources.\n",
                encoding="utf-8",
            )
            created.append("manuscript/01-introduction.md")
        order = root / "manuscript" / "order.txt"
        if order.is_file() and order.read_text(encoding="utf-8").strip() == ORDER_FILE.strip():
            order.write_text("01-introduction.md\n", encoding="utf-8")
            created.append("manuscript/order.txt")

    brief_path = root / "composition-brief.json"
    if not brief_path.exists():
        example_name = str(record.get("composition_brief_example") or "")
        example = repository / example_name if example_name else Path()
        if not example.is_file():
            example_dir = repository / str(record.get("canonical_example", ""))
            alternatives = (example_dir / "editorial-brief.json", example_dir / "composition-brief.json")
            example = next((candidate for candidate in alternatives if candidate.is_file()), Path())
        if example.is_file():
            brief = json.loads(example.read_text(encoding="utf-8"))
            if not isinstance(brief, dict):
                raise ValueError(f"canonical composition brief must be a JSON object: {example}")
            brief["publication_type"] = publication_type
            brief["visual_reference"] = ""
        else:
            brief = {
                "schema_version": "1.0.0",
                "publication_type": publication_type,
                "visual_reference": "",
                "required": [],
            }
        try:
            intent = json.loads((root / ".reportkit" / "intent.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            intent = {}
        if isinstance(intent, dict) and isinstance(intent.get("visual_reference"), str):
            if intent["visual_reference"].strip():
                brief["visual_reference"] = intent["visual_reference"]
        brief_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append("composition-brief.json")

    return tuple(created)


def _texmf_local() -> Path:
    kpsewhich = shutil.which("kpsewhich")
    if not kpsewhich:
        return Path("/usr/local/share/texmf")
    try:
        result = subprocess.run(
            [kpsewhich, "-var-value", "TEXMFLOCAL"], capture_output=True, text=True, check=False, timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return Path("/usr/local/share/texmf")
    value = result.stdout.strip()
    return Path(value) if result.returncode == 0 and value else Path("/usr/local/share/texmf")


def _font_files_resolvable() -> bool:
    kpsewhich = shutil.which("kpsewhich")
    if not kpsewhich:
        return False
    try:
        return all(
            subprocess.run([kpsewhich, name], capture_output=True, text=True, check=False, timeout=8).stdout.strip()
            for name in ("libertinus.sty", "libertinust1math.sty")
        )
    except (OSError, subprocess.SubprocessError):
        return False


def _extract_font_bundle(bundle: Path, destination: Path) -> None:
    """Extract regular files and directories without following archive links."""
    root = destination.resolve()
    with tarfile.open(bundle, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"font bundle contains an unsupported member: {member.name}")
            member_destination = (destination / member.name).resolve()
            if member_destination != root and root not in member_destination.parents:
                raise ValueError(f"font bundle contains an unsafe path: {member.name}")

        for member in members:
            member_destination = destination / member.name
            if member.isdir():
                member_destination.mkdir(parents=True, exist_ok=True)
                continue
            member_destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"font bundle member cannot be read: {member.name}")
            with source, member_destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            member_destination.chmod(member.mode & 0o777)


def install_fonts(repo_root: Path) -> str:
    """Install the bundled Libertinus subset into the local TeX tree if needed."""
    if _font_files_resolvable():
        return "Libertinus fonts already resolvable"

    bundle = repo_root / "font_data" / "reportkit-libertinus-fonts.tar.gz"
    if not bundle.is_file():
        raise ValueError(
            f"font bundle is missing: {bundle}. Install it manually with "
            "apt-get install -y --no-install-recommends texlive-fonts-extra"
        )

    texmf_local = _texmf_local()
    try:
        texmf_local.mkdir(parents=True, exist_ok=True)
        _extract_font_bundle(bundle, texmf_local)
    except (OSError, tarfile.TarError, ValueError) as exc:
        raise ValueError(
            f"could not install Libertinus fonts into {texmf_local}: {exc}. "
            "Try the manual instructions in references/font-setup.md."
        ) from exc

    mktexlsr = shutil.which("mktexlsr")
    if mktexlsr:
        result = subprocess.run([mktexlsr, str(texmf_local)], capture_output=True, text=True, check=False, timeout=30)
        if result.returncode:
            raise ValueError(
                f"mktexlsr could not update {texmf_local}: {result.stderr.strip() or result.stdout.strip()}"
            )
    if not _font_files_resolvable():
        raise ValueError(
            f"fonts were extracted into {texmf_local}, but kpsewhich cannot resolve them; "
            "see references/font-setup.md"
        )
    return f"Libertinus fonts installed in {texmf_local}"
