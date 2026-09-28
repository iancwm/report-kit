from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from rk_container import staging  # noqa: E402
from rk_container.staging import Limits, StagingError, collect, write_archive  # noqa: E402


def _tree(root: Path, files: dict[str, bytes]) -> Path:
    for relative, data in files.items():
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return root


def _codes(exc: pytest.ExceptionInfo[StagingError]) -> set[str]:
    return {p.code for p in exc.value.problems}


def test_manifest_records_bytes_and_posix_spelling(tmp_path: Path) -> None:
    body = b"# Title\r\n\r\nCRLF stays CRLF.\r\n"
    src = _tree(tmp_path / "Publication Tëst ü", {"manuscript/01 intro.md": body, "publication.yaml": b"title: x\n"})
    result = collect(src)
    entry = {f["path"]: f for f in result.manifest()["files"]}["manuscript/01 intro.md"]
    assert entry == {"path": "manuscript/01 intro.md", "size": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    assert result.manifest_sha256() == hashlib.sha256(result.manifest_bytes()).hexdigest()


def test_manifest_is_order_independent(tmp_path: Path) -> None:
    a = collect(_tree(tmp_path / "a", {"b.md": b"1", "a.md": b"2", "z/y.md": b"3"}))
    b = collect(_tree(tmp_path / "b", {"z/y.md": b"3", "a.md": b"2", "b.md": b"1"}))
    assert a.manifest_bytes() == b.manifest_bytes()


def test_excludes_host_state(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {
        "publication.yaml": b"t", ".git/HEAD": b"x", "build/combined/x.pdf": b"%PDF", "output/y.pdf": b"%PDF",
        "manuscript/__pycache__/m.pyc": b"x", ".venv/bin/python": b"x", "env2/pyvenv.cfg": b"home=/",
        "env2/lib/x.py": b"x", ".ruff_cache/x": b"x", "reportkit.lock": b"{}", "report.pdf": b"%PDF",
    })
    result = collect(src)
    assert [f.relative for f in result.files] == ["publication.yaml"]
    assert {".git/", "build/", "output/", "manuscript/__pycache__/", ".venv/", "env2/", ".ruff_cache/", "reportkit.lock", "report.pdf"} <= set(result.excluded)


def test_nested_pdfs_are_inputs_but_root_pdfs_are_not(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"report.tex": b"x", "report.pdf": b"%PDF-old", "figures/chart.pdf": b"%PDF-fig"})
    assert sorted(f.relative for f in collect(src).files) == ["figures/chart.pdf", "report.tex"]


def test_empty_directories_are_kept(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"publication.yaml": b"t"})
    (src / "fragments").mkdir()
    assert "fragments" in collect(src).directories


@pytest.mark.skipif(os.name == "nt", reason="needs a case-sensitive filesystem")
def test_case_collision_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"Chapter.md": b"1", "chapter.md": b"2"})
    if len(list(src.iterdir())) < 2:
        pytest.skip("filesystem is case-insensitive")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_PATH_COLLISION"}


def test_unicode_normalization_collision_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"café.md": b"1"})
    try:
        (src / "café.md").write_bytes(b"2")
    except OSError:
        pytest.skip("filesystem normalizes names")
    if len(list(src.iterdir())) < 2:
        pytest.skip("filesystem normalizes names")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_PATH_COLLISION"}


def test_symlink_is_rejected_without_reading_target(tmp_path: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_bytes(b"do not stage")
    src = _tree(tmp_path / "p", {"a.md": b"1"})
    try:
        (src / "link.md").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable (enable Developer Mode on Windows)")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_SYMLINK"}


@pytest.mark.skipif(os.name != "nt", reason="junctions are Windows-only")
def test_junction_is_rejected(tmp_path: Path) -> None:
    import _winapi
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.md").write_bytes(b"secret")
    src = _tree(tmp_path / "p", {"a.md": b"1"})
    _winapi.CreateJunction(str(outside), str(src / "junction"))
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_REPARSE_POINT"}


@pytest.mark.skipif(os.name == "nt" or not hasattr(os, "mkfifo"), reason="needs mkfifo")
def test_special_file_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"a.md": b"1"})
    os.mkfifo(src / "pipe")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_SPECIAL_FILE"}


@pytest.mark.skipif(os.name == "nt", reason="Windows cannot create these names")
@pytest.mark.parametrize("name", ["a\\b.md", "a:b.md", "trailing.md ", "ctrl\x01.md"])
def test_names_windows_cannot_represent_are_reported_not_renamed(tmp_path: Path, name: str) -> None:
    src = _tree(tmp_path / "p", {name: b"1"})
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_PATH_NONPORTABLE"}
    assert exc.value.problems[0].path == name


def test_limits_are_enforced_before_hashing(tmp_path: Path, monkeypatch) -> None:
    src = _tree(tmp_path / "p", {"a.bin": b"x" * 10, "b.bin": b"y" * 10})
    monkeypatch.setattr(staging, "_hash", lambda path: pytest.fail("hashed despite limit failure"))
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_file_bytes=5))
    assert _codes(exc) == {"RK_STAGE_FILE_TOO_LARGE"}
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_total_bytes=15))
    assert _codes(exc) == {"RK_STAGE_TOO_LARGE"}
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_files=1))
    assert _codes(exc) == {"RK_STAGE_TOO_MANY_FILES"}


def test_all_problems_are_reported_together(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"big.bin": b"x" * 10, "ok.md": b"1"})
    try:
        (src / "link").symlink_to(src / "ok.md")
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_file_bytes=5))
    assert _codes(exc) == {"RK_STAGE_SYMLINK", "RK_STAGE_FILE_TOO_LARGE"}


def test_archive_layout_ownership_and_bytes(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"manuscript/ä b.md": b"x\r\n", "publication.yaml": b"t"})
    (src / "fragments").mkdir()
    result = collect(src)
    buffer = io.BytesIO()
    write_archive(result, buffer)
    buffer.seek(0)
    with tarfile.open(fileobj=buffer) as archive:
        members = {m.name: m for m in archive.getmembers()}
        assert {"source", "source/manuscript", "source/fragments", "source/manuscript/ä b.md",
                "source/publication.yaml", "input-manifest.json"} == set(members)
        assert all((m.uid, m.gid) == (10001, 10001) for m in members.values())
        assert archive.extractfile("source/manuscript/ä b.md").read() == b"x\r\n"
        assert archive.extractfile("input-manifest.json").read() == result.manifest_bytes()
    assert json.loads(result.manifest_bytes())["directories"] == ["fragments", "manuscript"]


def test_file_changed_during_archive_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"a.md": b"original"})
    result = collect(src)
    (src / "a.md").write_bytes(b"editeddd")  # same size, different bytes
    with pytest.raises(StagingError) as exc:
        write_archive(result, io.BytesIO())
    assert _codes(exc) == {"RK_STAGE_FILE_CHANGED"}


def test_missing_source_root(tmp_path: Path) -> None:
    with pytest.raises(StagingError) as exc:
        collect(tmp_path / "nope")
    assert _codes(exc) == {"RK_STAGE_SOURCE_MISSING"}


def test_excludes_launcher_byproducts_from_a_prior_retry(tmp_path: Path) -> None:
    """scripts/rk_container/results.py creates these siblings of a
    user-chosen output-root directory: <output>.failed (validate_output_root),
    .<output>.incoming-* (incoming_dir), .<output>.previous-<pid> (install's
    backup). None of them are publication content -- a retry after a failed
    build (using the documented `--output-root <publication>/output` layout)
    must not silently restage them as if they were real source files."""
    src = _tree(tmp_path / "p", {"publication.yaml": b"t"})
    _tree(src / "output.failed", {
        "launcher-failure.json": b'{"code": "RK_CONTAINER_FAILED"}',
        "logs/build.log": b"! Undefined control sequence.",
    })
    _tree(src / ".output.previous-12345", {"report.pdf": b"%PDF-stale"})
    (src / ".output.incoming-abc123").mkdir()
    result = collect(src)
    assert [f.relative for f in result.files] == ["publication.yaml"]
    assert {"output.failed/", ".output.previous-12345/", ".output.incoming-abc123/"} <= set(result.excluded)
