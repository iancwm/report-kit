"""Pinned toolchain identity and drift reporting."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from .version import TOOLCHAIN_SCHEMA_VERSION

DEFAULT_RENDER_DPI = 150


def lock_path(repo_root: Path) -> Path:
    """Return the canonical machine-readable toolchain lock path."""
    return repo_root / "toolchain" / "toolchain.lock.json"


def load_toolchain_lock(repo_root: Path) -> dict[str, Any]:
    """Load and validate the toolchain lock object for ``repo_root``."""
    path = lock_path(repo_root)
    if not path.is_file():
        return {"schema_version": TOOLCHAIN_SCHEMA_VERSION, "missing": True}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def toolchain_fingerprint(lock: dict[str, Any]) -> str:
    """Calculate the stable SHA-256 fingerprint of a lock object."""
    value = {key: item for key, item in lock.items() if key != "fingerprint"}
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def version_line(command: str) -> str | None:
    """Return the first version-output line for an executable, if present."""
    executable = shutil.which(command)
    if not executable:
        return None
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = (result.stdout or result.stderr).splitlines()
    return lines[0].strip() if lines else executable


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _apt_package_version(name: str) -> str | None:
    executable = shutil.which("dpkg-query")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "-W", "-f=${Version}", name],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _font_family(name: str) -> str | None:
    executable = shutil.which("fc-match")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "--format=%{family}", name], capture_output=True, text=True, timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    family = result.stdout.strip()
    return family if result.returncode == 0 and name.lower() in family.lower() else None


def _tex_file(name: str) -> str | None:
    executable = shutil.which("kpsewhich")
    if not executable:
        return None
    try:
        result = subprocess.run([executable, name], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def resolved_toolchain(repo_root: Path) -> dict[str, Any]:
    """Resolve installed tools against the lock and classify their status.

    ``pinned`` means the declared fingerprint, required runtime dependencies,
    and versions all match. ``unverified`` means the environment is available
    and version-compatible but no fingerprint was declared. ``mismatch`` means
    an integrity, fingerprint, or version check failed. ``unavailable`` means
    one or more required tools, packages, or fonts cannot be resolved.
    """
    lock = load_toolchain_lock(repo_root)
    expected_fingerprint = toolchain_fingerprint(lock)
    declared_fingerprint = os.environ.get("REPORTKIT_TOOLCHAIN_FINGERPRINT")
    commands = {name: version_line(name) for name in ("pdflatex", "lualatex", "pandoc", "bibtex", "git")}
    packages = {name: _package_version(name) for name in lock.get("python_packages", {})}
    expected_packages = lock.get("python_packages", {})
    expected_apt_packages = lock.get("apt_package_versions", {})
    apt_packages = {name: _apt_package_version(name) for name in expected_apt_packages}
    runtime_fonts = {
        "Google Sans": _font_family("Google Sans"),
        "libertinus.sty": _tex_file("libertinus.sty"),
        "libertinust1math.sty": _tex_file("libertinust1math.sty"),
    }
    version_matches = {
        "python": sys.version.split()[0] == lock.get("python_version"),
        **{f"apt:{name}": apt_packages[name] == expected for name, expected in expected_apt_packages.items()},
        **{f"python:{name}": packages[name] == expected for name, expected in expected_packages.items()},
    }
    integrity: dict[str, bool] = {}
    files = {**lock.get("fonts", {}), "toolchain/requirements.lock": lock.get("python_lock_sha256")}
    for relative, expected in files.items():
        path = repo_root / relative
        if not path.is_file() or not expected:
            integrity[relative] = False
            continue
        integrity[relative] = hashlib.sha256(path.read_bytes()).hexdigest() == expected
    required_available = all(commands.values()) and all(packages.values()) and all(runtime_fonts.values())
    versions_match = all(version_matches.values())
    if not all(integrity.values()):
        status = "mismatch"
    elif declared_fingerprint:
        status = "pinned" if declared_fingerprint == expected_fingerprint and required_available and versions_match else "mismatch"
    elif required_available:
        status = "unverified" if versions_match else "mismatch"
    else:
        status = "unavailable"
    return {
        "status": status,
        "fingerprint": declared_fingerprint,
        "expected_fingerprint": expected_fingerprint,
        "python": sys.version.split()[0],
        "commands": commands,
        "apt_packages": apt_packages,
        "runtime_fonts": runtime_fonts,
        "python_packages": packages,
        "version_matches": version_matches,
        "integrity": integrity,
        "renderer_dpi": int(lock.get("renderer", {}).get("dpi", DEFAULT_RENDER_DPI)),
    }


def toolchain_context(repo_root: Path) -> dict[str, Any]:
    """Return expected lock data, resolved status, and its fingerprint."""
    lock = load_toolchain_lock(repo_root)
    return {
        "expected": lock,
        "resolved": resolved_toolchain(repo_root),
        "fingerprint": toolchain_fingerprint(lock),
    }
