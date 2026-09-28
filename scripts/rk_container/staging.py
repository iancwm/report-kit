"""Validate a publication directory and stream it into a build container.

Standard library only: this runs on the author's host (Windows or Linux,
Python 3.11+), never inside the toolchain image. Nothing is renamed or
re-encoded; a path that cannot be staged identically on both hosts is
reported instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
from typing import BinaryIO
import unicodedata

BUILD_UID = 10001
BUILD_GID = 10001
MANIFEST_SCHEMA = "reportkit-input-manifest/1"
EXCLUDED_ANY_DEPTH = frozenset({".git", ".hg", ".svn", ".venv", "venv", "__pycache__",
                                ".pytest_cache", ".ruff_cache", ".mypy_cache", ".cache"})
EXCLUDED_TOP_LEVEL = frozenset({"build", "output", "reportkit.lock"})
NONPORTABLE_CHARACTERS = frozenset('\\:*?"<>|')
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class Limits:
    max_total_bytes: int = 1024 * 1024 * 1024
    max_file_bytes: int = 200 * 1024 * 1024
    max_files: int = 20_000


@dataclass(frozen=True)
class Problem:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class StagingError(Exception):
    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("; ".join(f"{p.path}: {p.message}" for p in problems[:5]))
        self.problems = problems


@dataclass(frozen=True)
class StagedFile:
    relative: str
    absolute: Path
    size: int
    sha256: str


@dataclass
class Staging:
    root: Path
    files: list[StagedFile] = field(default_factory=list)
    directories: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.files)

    def manifest(self) -> dict:
        ordered = sorted(self.files, key=lambda item: item.relative.encode("utf-8"))
        return {
            "schema": MANIFEST_SCHEMA,
            "directories": sorted(self.directories, key=lambda d: d.encode("utf-8")),
            "files": [{"path": f.relative, "size": f.size, "sha256": f.sha256} for f in ordered],
        }

    def manifest_bytes(self) -> bytes:
        return (json.dumps(self.manifest(), ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")

    def manifest_sha256(self) -> str:
        return hashlib.sha256(self.manifest_bytes()).hexdigest()


def _fold(relative: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", relative).casefold())


def _excluded(parts: tuple[str, ...], is_dir: bool, path: str) -> bool:
    name = parts[-1]
    if is_dir and (name in EXCLUDED_ANY_DEPTH or os.path.isfile(os.path.join(path, "pyvenv.cfg"))):
        return True
    return len(parts) == 1 and (name in EXCLUDED_TOP_LEVEL or (not is_dir and name.lower().endswith(".pdf")))


def _name_problem(relative: str, name: str) -> Problem | None:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        return Problem("RK_STAGE_PATH_NONPORTABLE", relative, "name contains a control character")
    bad = "".join(sorted(set(name) & NONPORTABLE_CHARACTERS))
    if bad:
        return Problem("RK_STAGE_PATH_NONPORTABLE", relative, f"name contains {bad!r}, which Windows cannot represent")
    if name.endswith((" ", ".")):
        return Problem("RK_STAGE_PATH_NONPORTABLE", relative, "name ends with a space or dot, which Windows strips")
    return None


def _hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def collect(root: Path, limits: Limits = Limits()) -> Staging:
    """Validate and hash every stageable file under root, or raise with all problems."""
    root = Path(root)
    if not root.is_dir():
        raise StagingError([Problem("RK_STAGE_SOURCE_MISSING", str(root), "source root is not a directory")])
    result = Staging(root.resolve())
    problems: list[Problem] = []
    seen: dict[str, str] = {}
    candidates: list[tuple[str, Path, int]] = []
    pending: list[tuple[str, ...]] = [()]
    while pending:
        parts = pending.pop()
        with os.scandir(result.root.joinpath(*parts)) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            child = (*parts, entry.name)
            relative = "/".join(child)
            info = entry.stat(follow_symlinks=False)
            if entry.is_symlink():
                problems.append(Problem("RK_STAGE_SYMLINK", relative, "symbolic links are not staged; replace it with the real file"))
                continue
            if getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
                problems.append(Problem("RK_STAGE_REPARSE_POINT", relative, "junctions and other reparse points are not staged"))
                continue
            is_dir = stat.S_ISDIR(info.st_mode)
            if _excluded(child, is_dir, entry.path):
                result.excluded.append(relative + ("/" if is_dir else ""))
                continue
            problem = _name_problem(relative, entry.name)
            if problem:
                problems.append(problem)
                continue
            key = _fold(relative)
            if key in seen:
                problems.append(Problem("RK_STAGE_PATH_COLLISION", relative,
                                        f"collides with {seen[key]!r} under case folding or Unicode normalization"))
                continue
            seen[key] = relative
            if is_dir:
                result.directories.append(relative)
                pending.append(child)
            elif not stat.S_ISREG(info.st_mode):
                problems.append(Problem("RK_STAGE_SPECIAL_FILE", relative, "only regular files and directories can be staged"))
            elif info.st_size > limits.max_file_bytes:
                problems.append(Problem("RK_STAGE_FILE_TOO_LARGE", relative,
                                        f"{info.st_size} bytes exceeds the per-file limit of {limits.max_file_bytes}"))
            else:
                candidates.append((relative, Path(entry.path), info.st_size))
    if len(candidates) > limits.max_files:
        problems.append(Problem("RK_STAGE_TOO_MANY_FILES", ".", f"{len(candidates)} files exceeds the limit of {limits.max_files}"))
    total = sum(size for _, _, size in candidates)
    if total > limits.max_total_bytes:
        problems.append(Problem("RK_STAGE_TOO_LARGE", ".", f"{total} bytes exceeds the total limit of {limits.max_total_bytes}"))
    if problems:
        raise StagingError(problems)
    for relative, absolute, size in candidates:
        digest, actual = _hash(absolute)
        if actual != size:
            problems.append(Problem("RK_STAGE_FILE_CHANGED", relative, "file changed while it was being staged"))
        result.files.append(StagedFile(relative, absolute, actual, digest))
    if problems:
        raise StagingError(problems)
    return result


class _VerifyingReader:
    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle
        self._digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        chunk = self._handle.read(size)
        self._digest.update(chunk)
        return chunk

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def _info(name: str, kind: bytes, mode: int, size: int = 0) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type, info.mode, info.size, info.mtime = kind, mode, size, 0
    info.uid, info.gid, info.uname, info.gname = BUILD_UID, BUILD_GID, "reportkit", "reportkit"
    return info


def write_archive(staging: Staging, stream: BinaryIO) -> None:
    """Write source/ and input-manifest.json for `docker cp --archive - <id>:/work`."""
    manifest = staging.manifest()
    with tarfile.open(fileobj=stream, mode="w|", format=tarfile.PAX_FORMAT) as archive:
        archive.addfile(_info("source", tarfile.DIRTYPE, 0o755))
        for directory in manifest["directories"]:
            archive.addfile(_info(f"source/{directory}", tarfile.DIRTYPE, 0o755))
        for item in sorted(staging.files, key=lambda f: f.relative.encode("utf-8")):
            with open(item.absolute, "rb") as handle:
                reader = _VerifyingReader(handle)
                try:
                    archive.addfile(_info(f"source/{item.relative}", tarfile.REGTYPE, 0o644, item.size), reader)
                except OSError as exc:  # file shrank after hashing
                    raise StagingError([Problem("RK_STAGE_FILE_CHANGED", item.relative, f"file changed after it was hashed ({exc})")]) from None
            if reader.hexdigest() != item.sha256:
                raise StagingError([Problem("RK_STAGE_FILE_CHANGED", item.relative, "file changed after it was hashed")])
        data = staging.manifest_bytes()
        archive.addfile(_info("input-manifest.json", tarfile.REGTYPE, 0o644, len(data)), io.BytesIO(data))
