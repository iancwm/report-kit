"""Validate, extract and atomically install container build results (stdlib only)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
from typing import BinaryIO

from .staging import NONPORTABLE_CHARACTERS

RESULT_PREFIX = "result"
RESULT_MANIFEST = "container-build.json"
FAILURE_RECORD = "launcher-failure.json"
MAX_RESULT_BYTES = 4 * 1024 ** 3
MAX_RESULT_FILES = 50_000
MANAGED_DIRECTORIES = ("build", "output")


class ResultError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _absolute(path: Path) -> Path:
    path = Path(path).absolute()
    return path.parent.resolve() / path.name


def _managed(directory: Path, marker: str) -> bool:
    return not directory.exists() or not any(directory.iterdir()) or (directory / marker).is_file()


def validate_output_root(output_root: Path, source_root: Path) -> tuple[Path, Path]:
    """Resolve the output and failure directories and refuse anything unsafe to replace."""
    target = _absolute(output_root)
    source = Path(source_root).resolve()
    if target == source or source.is_relative_to(target):
        raise ResultError("RK_OUTPUT_CONTAINS_SOURCE", f"output root {target} contains the source root; choose a separate directory")
    if target.is_relative_to(source) and target.relative_to(source).parts[0] not in MANAGED_DIRECTORIES:
        raise ResultError("RK_OUTPUT_INSIDE_SOURCE", "an output root inside the source must be under its build/ or output/ directory, which are never staged")
    if not target.parent.is_dir():
        raise ResultError("RK_OUTPUT_PARENT_MISSING", f"parent directory {target.parent} does not exist")
    failure = target.with_name(target.name + ".failed")
    for directory, marker in ((target, RESULT_MANIFEST), (failure, FAILURE_RECORD)):
        if directory.is_symlink():
            raise ResultError("RK_OUTPUT_SYMLINK", f"{directory} is a symbolic link; pass the real directory")
        if directory.exists() and not directory.is_dir():
            raise ResultError("RK_OUTPUT_NOT_DIRECTORY", f"{directory} exists and is not a directory")
        if not _managed(directory, marker):
            raise ResultError("RK_OUTPUT_NOT_MANAGED", f"{directory} already contains files this launcher did not write; choose an empty or new directory")
    return target, failure


def incoming_dir(target: Path) -> Path:
    return Path(tempfile.mkdtemp(prefix=f".{target.name}.incoming-", dir=target.parent))


def _member_path(name: str) -> PurePosixPath:
    unsafe = ResultError("RK_RESULT_UNSAFE_MEMBER", f"{name!r}: result archive entries must stay inside result/")
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        raise unsafe
    parts = PurePosixPath(name).parts
    if not parts or parts[0] != RESULT_PREFIX or ".." in parts:
        raise unsafe
    for part in parts[1:]:
        if set(part) & NONPORTABLE_CHARACTERS or part.endswith((" ", ".")) or any(ord(ch) < 32 for ch in part):
            raise unsafe
    return PurePosixPath(*parts[1:]) if len(parts) > 1 else PurePosixPath()


def extract_result(stream: BinaryIO, destination: Path) -> None:
    """Extract a `docker cp <id>:/work/result -` stream into an empty directory."""
    total = count = 0
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for member in archive:
            relative = _member_path(member.name)
            count += 1
            if count > MAX_RESULT_FILES:
                raise ResultError("RK_RESULT_TOO_LARGE", f"result has more than {MAX_RESULT_FILES} entries")
            if member.isdir():
                destination.joinpath(*relative.parts).mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile() or not relative.parts:
                raise ResultError("RK_RESULT_UNSAFE_MEMBER", f"{member.name!r}: only regular files and directories are accepted")
            total += member.size
            if total > MAX_RESULT_BYTES:
                raise ResultError("RK_RESULT_TOO_LARGE", f"result exceeds {MAX_RESULT_BYTES} bytes")
            path = destination.joinpath(*relative.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                handle = open(path, "xb")
            except FileExistsError:
                raise ResultError("RK_RESULT_DUPLICATE_MEMBER", f"{member.name!r} appears twice in the result archive") from None
            with handle, archive.extractfile(member) as source:
                shutil.copyfileobj(source, handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_result(directory: Path) -> dict:
    manifest_path = directory / RESULT_MANIFEST
    if not manifest_path.is_file():
        raise ResultError("RK_RESULT_MANIFEST_MISSING", f"the container did not return {RESULT_MANIFEST}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = {_member_path(f"{RESULT_PREFIX}/{item['path']}").as_posix(): item for item in manifest.get("outputs", [])}
    present = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()} - {RESULT_MANIFEST}
    if missing := sorted(set(listed) - present):
        raise ResultError("RK_RESULT_MISSING_FILE", f"result is missing {missing[:5]}")
    if extra := sorted(present - set(listed)):
        raise ResultError("RK_RESULT_UNLISTED_FILE", f"result contains files not in {RESULT_MANIFEST}: {extra[:5]}")
    for relative, item in listed.items():
        if _sha256(directory / relative) != item["sha256"]:
            raise ResultError("RK_RESULT_HASH_MISMATCH", f"{relative} does not match its recorded SHA-256")
    return manifest


def install(staged: Path, target: Path) -> None:
    """Swap staged into target. The previous target survives any failure."""
    backup = None
    if target.exists():
        backup = target.with_name(f".{target.name}.previous-{os.getpid()}")
        if backup.exists():
            shutil.rmtree(backup)
        try:
            os.replace(target, backup)
        except PermissionError:
            shutil.rmtree(staged, ignore_errors=True)
            raise ResultError("RK_OUTPUT_LOCKED", f"could not replace {target}; close any program holding files there (for example a PDF viewer) and retry") from None
    try:
        os.replace(staged, target)
    except OSError:
        if backup is not None:
            os.replace(backup, target)
        shutil.rmtree(staged, ignore_errors=True)
        raise
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)


def record_failure(failure_dir: Path, collected: Path | None, launcher_record: dict) -> None:
    staged = incoming_dir(failure_dir)
    if collected is not None and collected.is_dir():
        shutil.copytree(collected, staged, dirs_exist_ok=True)
        shutil.rmtree(collected, ignore_errors=True)
    (staged / FAILURE_RECORD).write_text(json.dumps(launcher_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    install(staged, failure_dir)


def clear_failure(failure_dir: Path) -> None:
    if failure_dir.is_dir() and (failure_dir / FAILURE_RECORD).is_file():
        shutil.rmtree(failure_dir)
