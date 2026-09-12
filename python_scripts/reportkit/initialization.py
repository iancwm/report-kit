"""Initialize a consumer project without copying ReportKit into it."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tarfile


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
