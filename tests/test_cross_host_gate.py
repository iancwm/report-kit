from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import cross_host_gate as gate  # noqa: E402


def summary(**overrides):
    base = {
        "schema": "reportkit-cross-host-gate/1", "image": {"digest": "sha256:" + "a" * 64},
        "fixtures": {"markdown": {"input_manifest_sha256": "m", "selection": {"theme": "default"}, "page_count": 3, "inspect_passed": True, "pdf_sha256": "p1"}},
        "checks": [{"name": name, "status": "passed", "detail": ""} for name in gate.REQUIRED_CHECKS], "passed": True,
    }
    base.update(overrides)
    return base


def test_equivalent_summaries_ignore_pdf_bytes() -> None:
    other = summary()
    other["fixtures"]["markdown"] = {**other["fixtures"]["markdown"], "pdf_sha256": "p2"}
    assert gate.compare_summaries(summary(), other) == []


def test_differences_are_reported() -> None:
    other = summary(image={"digest": "sha256:" + "b" * 64})
    other["fixtures"]["markdown"] = {**other["fixtures"]["markdown"], "page_count": 4}
    diffs = gate.compare_summaries(summary(), other)
    assert any("image digest" in d for d in diffs) and any("page_count" in d for d in diffs)


def test_failed_or_missing_required_check_fails_comparison() -> None:
    other = summary()
    other["checks"] = [c for c in other["checks"] if c["name"] != "path-safety-symlink"]
    assert any("path-safety-symlink" in d for d in gate.compare_summaries(summary(), other))
    other = summary()
    other["checks"][0]["status"] = "failed"
    assert gate.compare_summaries(summary(), other)


def test_materialize_uses_raw_blob_bytes(tmp_path: Path) -> None:
    if not (REPO / ".git").exists():
        pytest.skip("needs a Git checkout")
    gate.materialize("HEAD", "publication_pipeline/example_publication", tmp_path / "Publication Tëst ü")
    raw = subprocess.run(["git", "show", "HEAD:publication_pipeline/example_publication/manuscript/01-fixture.md"],
                         cwd=REPO, capture_output=True, check=True).stdout
    assert (tmp_path / "Publication Tëst ü" / "manuscript" / "01-fixture.md").read_bytes() == raw
    assert b"\r\n" not in raw


def test_dotdot_result_member_check_is_host_side(tmp_path: Path) -> None:
    status, _ = gate.check_result_dotdot(tmp_path)
    assert status == "passed"
