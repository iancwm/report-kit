"""Consumer-project scaffolding and optional local font installation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tarfile


DIRECTORIES = ("manuscript", "fragments", "assets", "figures", "build", "output")
ORDER_CONTENT = """# One manuscript filename per line, in reading order.
# Example:
# 01-introduction.md
# 02-background.md
"""
PUBLICATION_CONTENT = """# Publication identity. title is required; everything else is optional.
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


@dataclass(frozen=True)
class InitResult:
    """Describe the files and directories created by :func:`initialize`."""

    target: Path
    created: tuple[str, ...]


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def initialize(target: Path, repo_root: Path) -> InitResult:
    """Scaffold a consumer project after enforcing the engine boundary."""
    target = target.expanduser().resolve()
    repo_root = repo_root.expanduser().resolve()
    if _inside(target, repo_root):
        raise ValueError(
            f"refusing to initialize {target}: it is inside the ReportKit clone {repo_root}. "
            "Publications must live in a separate consumer project; see references/repository-boundary.md."
        )

    created: list[str] = []
    if not target.exists():
        target.mkdir(parents=True)
        created.append(".")
    elif not target.is_dir():
        raise ValueError(f"init target is not a directory: {target}")
    for name in DIRECTORIES:
        path = target / name
        if not path.exists():
            path.mkdir()
            created.append(name + "/")
        elif not path.is_dir():
            raise ValueError(f"init target contains a non-directory path: {path}")

    files = {
        target / "manuscript" / "order.txt": ORDER_CONTENT,
        target / "publication.yaml": PUBLICATION_CONTENT,
    }
    for path, content in files.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(str(path.relative_to(target)))
        elif not path.is_file():
            raise ValueError(f"init target contains a non-file path: {path}")
    return InitResult(target=target, created=tuple(created))


def _texmf_local() -> Path:
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich:
        try:
            result = subprocess.run(
                [kpsewhich, "-var-value", "TEXMFLOCAL"], capture_output=True, text=True, timeout=8,
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    return Path("/usr/local/share/texmf")


def _tex_files_available() -> bool:
    kpsewhich = shutil.which("kpsewhich")
    if not kpsewhich:
        return False
    try:
        return all(
            subprocess.run([kpsewhich, name], capture_output=True, text=True, timeout=8).stdout.strip()
            for name in ("libertinus.sty", "libertinust1math.sty")
        )
    except (OSError, subprocess.SubprocessError):
        return False


def install_fonts(repo_root: Path) -> tuple[bool, str]:
    """Install the bundled Libertinus subset into ``TEXMFLOCAL`` if needed."""
    if _tex_files_available():
        return True, "Libertinus is already resolvable"
    bundle = repo_root / "font_data" / "reportkit-libertinus-fonts.tar.gz"
    if not bundle.is_file():
        return False, (
            f"font bundle is missing: {bundle}; install it with "
            "apt-get install -y --no-install-recommends texlive-fonts-extra"
        )
    texmf = _texmf_local()
    try:
        texmf.mkdir(parents=True, exist_ok=True)
        with tarfile.open(bundle, "r:gz") as archive:
            archive.extractall(texmf, filter="data")
        mktexlsr = shutil.which("mktexlsr")
        if mktexlsr:
            subprocess.run([mktexlsr, str(texmf)], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, tarfile.TarError) as exc:
        return False, f"could not install fonts into {texmf}: {exc}"
    if not _tex_files_available():
        return False, f"font bundle extracted into {texmf}, but kpsewhich cannot resolve Libertinus"
    return True, f"Libertinus installed in {texmf}"
