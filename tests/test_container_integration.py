"""Runs the cross-host gate against a real image. CI sets
REPORTKIT_CONTAINER_TEST_IMAGE and REPORTKIT_REQUIRE_DOCKER=1 so a missing
daemon fails instead of skipping."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import cross_host_gate as gate  # noqa: E402

IMAGE = os.environ.get("REPORTKIT_CONTAINER_TEST_IMAGE")
if not IMAGE:
    if os.environ.get("REPORTKIT_REQUIRE_DOCKER") == "1":
        raise RuntimeError("REPORTKIT_REQUIRE_DOCKER=1 but REPORTKIT_CONTAINER_TEST_IMAGE is unset")
    pytest.skip("set REPORTKIT_CONTAINER_TEST_IMAGE to run container integration tests", allow_module_level=True)


def test_gate_passes_on_this_host(tmp_path: Path) -> None:
    summary = gate.run(argparse.Namespace(image=IMAGE, allow_unpinned_image="@sha256:" not in IMAGE, work_dir=str(tmp_path),
                                          summary=str(tmp_path / "s.json"), fresh=False, commit="HEAD"))
    failed = [c for c in summary["checks"] if c["status"] == "failed" and c["name"] != "host-has-no-lualatex"]
    assert not failed, failed
    assert summary["fixtures"]["editorial"]["selection"]["theme"] == "editorial"
    assert 6 <= summary["fixtures"]["editorial"]["page_count"] <= 8
    assert summary["fixtures"]["markdown"]["inspect_passed"] is True
