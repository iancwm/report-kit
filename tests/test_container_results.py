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

from rk_container import results  # noqa: E402
from rk_container.results import ResultError, extract_result, install, validate_output_root, verify_result  # noqa: E402


def _tar(entries: list[tuple[str, bytes | None, bytes]]) -> io.BytesIO:
    """entries: (name, data or None for dir, tar type)"""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind == tarfile.SYMTYPE:
                info.linkname = "/etc/passwd"
            if data is not None:
                info.size = len(data)
            archive.addfile(info, io.BytesIO(data) if data is not None else None)
    buffer.seek(0)
    return buffer


def _good_result() -> io.BytesIO:
    pdf = b"%PDF-1.7 ok"
    manifest = {"status": "passed", "outputs": [{"path": "doc.pdf", "sha256": hashlib.sha256(pdf).hexdigest(), "bytes": len(pdf)}]}
    return _tar([("result", None, tarfile.DIRTYPE), ("result/doc.pdf", pdf, tarfile.REGTYPE),
                 ("result/container-build.json", json.dumps(manifest).encode(), tarfile.REGTYPE)])


def test_good_result_round_trip(tmp_path: Path) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    extract_result(_good_result(), dest)
    assert verify_result(dest)["status"] == "passed"


@pytest.mark.parametrize("name,kind", [
    ("result/../escape.txt", tarfile.REGTYPE), ("/result/abs.txt", tarfile.REGTYPE), ("other/x", tarfile.REGTYPE),
    ("result/a\\b", tarfile.REGTYPE), ("result/a:stream", tarfile.REGTYPE), ("result/link", tarfile.SYMTYPE),
    ("result/hard", tarfile.LNKTYPE), ("result/dev", tarfile.CHRTYPE),
])
def test_unsafe_members_are_rejected_before_writing(tmp_path: Path, name: str, kind: bytes) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    data = None if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE) else b"x"
    with pytest.raises(ResultError) as exc:
        extract_result(_tar([(name, data, kind)]), dest)
    assert exc.value.code == "RK_RESULT_UNSAFE_MEMBER"
    assert not (tmp_path / "escape.txt").exists()
    assert list(dest.rglob("*")) == []


def test_duplicate_member_is_rejected(tmp_path: Path) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    with pytest.raises(ResultError) as exc:
        extract_result(_tar([("result/a", b"1", tarfile.REGTYPE), ("result/a", b"2", tarfile.REGTYPE)]), dest)
    assert exc.value.code == "RK_RESULT_DUPLICATE_MEMBER"


def test_result_size_limit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(results, "MAX_RESULT_BYTES", 3)
    dest = tmp_path / "in"
    dest.mkdir()
    with pytest.raises(ResultError) as exc:
        extract_result(_tar([("result/a", b"1234", tarfile.REGTYPE)]), dest)
    assert exc.value.code == "RK_RESULT_TOO_LARGE"


def test_hash_mismatch_and_unlisted_files(tmp_path: Path) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    extract_result(_good_result(), dest)
    (dest / "extra.txt").write_bytes(b"x")
    with pytest.raises(ResultError) as exc:
        verify_result(dest)
    assert exc.value.code == "RK_RESULT_UNLISTED_FILE"
    (dest / "extra.txt").unlink()
    (dest / "doc.pdf").write_bytes(b"%PDF tampered")
    with pytest.raises(ResultError) as exc:
        verify_result(dest)
    assert exc.value.code == "RK_RESULT_HASH_MISMATCH"


def test_output_root_rules(tmp_path: Path) -> None:
    source = tmp_path / "project"
    (source / "manuscript").mkdir(parents=True)
    target, failure = validate_output_root(tmp_path / "out", source)
    assert target == (tmp_path / "out").resolve() and failure.name == "out.failed"
    assert validate_output_root(source / "output", source)[0] == (source / "output").resolve()
    with pytest.raises(ResultError) as exc:
        validate_output_root(source / "manuscript" / "pdf", source)
    assert exc.value.code == "RK_OUTPUT_INSIDE_SOURCE"
    with pytest.raises(ResultError) as exc:
        validate_output_root(tmp_path / "missing" / "out", source)
    assert exc.value.code == "RK_OUTPUT_PARENT_MISSING"


def test_refuses_output_root_containing_source(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    for candidate in (source, tmp_path):
        with pytest.raises(ResultError) as exc:
            validate_output_root(candidate, source)
        assert exc.value.code == "RK_OUTPUT_CONTAINS_SOURCE"


def test_refuses_unmanaged_output_root(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    documents = tmp_path / "Documents"
    documents.mkdir()
    (documents / "taxes.xlsx").write_bytes(b"precious")
    with pytest.raises(ResultError) as exc:
        validate_output_root(documents, source)
    assert exc.value.code == "RK_OUTPUT_NOT_MANAGED"
    assert (documents / "taxes.xlsx").read_bytes() == b"precious"
    (documents / "taxes.xlsx").unlink()
    validate_output_root(documents, source)  # empty is fine


def test_refuses_unmanaged_failure_dir(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    (tmp_path / "out.failed").mkdir()
    (tmp_path / "out.failed" / "notes.txt").write_bytes(b"mine")
    with pytest.raises(ResultError) as exc:
        validate_output_root(tmp_path / "out", source)
    assert exc.value.code == "RK_OUTPUT_NOT_MANAGED"


def test_install_replaces_previous_output(tmp_path: Path) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "old.pdf").write_bytes(b"old")
    staged = results.incoming_dir(target)
    (staged / "new.pdf").write_bytes(b"new")
    install(staged, target)
    assert [p.name for p in target.iterdir()] == ["new.pdf"]
    assert not staged.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["out"]


def test_install_keeps_previous_output_when_rename_is_locked(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "old.pdf").write_bytes(b"old")
    staged = results.incoming_dir(target)
    (staged / "new.pdf").write_bytes(b"new")
    real_replace = os.replace

    def locked(src, dst):
        if Path(src) == target:
            raise PermissionError(32, "The process cannot access the file because it is being used by another process")
        return real_replace(src, dst)

    monkeypatch.setattr(results.os, "replace", locked)
    with pytest.raises(ResultError) as exc:
        install(staged, target)
    assert exc.value.code == "RK_OUTPUT_LOCKED"
    assert "close" in exc.value.message
    assert (target / "old.pdf").read_bytes() == b"old"


def test_install_rolls_back_if_second_rename_fails(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "old.pdf").write_bytes(b"old")
    staged = results.incoming_dir(target)
    real_replace = os.replace

    def fail_second(src, dst):
        if Path(src) == staged:
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr(results.os, "replace", fail_second)
    with pytest.raises(OSError):
        install(staged, target)
    assert (target / "old.pdf").read_bytes() == b"old"


def test_record_and_clear_failure(tmp_path: Path) -> None:
    failure = tmp_path / "out.failed"
    collected = tmp_path / "collected"
    (collected / "logs").mkdir(parents=True)
    (collected / "logs" / "build.log").write_text("! Undefined control sequence.")
    results.record_failure(failure, collected, {"code": "RK_CONTAINER_FAILED", "exit_code": 4})
    assert json.loads((failure / "launcher-failure.json").read_text())["exit_code"] == 4
    assert (failure / "logs" / "build.log").is_file()
    results.clear_failure(failure)
    assert not failure.exists()
