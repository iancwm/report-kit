from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "python_scripts"))

from image_release_manifest import build_manifest  # noqa: E402
from reportkit.version import REPORTKIT_VERSION  # noqa: E402

DIGEST, COMMIT, TAG = "sha256:" + "a" * 64, "b" * 40, f"v{REPORTKIT_VERSION}"
GATE = {"passed": True, "image": {"digest": DIGEST}}


def test_manifest_shape() -> None:
    data = build_manifest("ghcr.io/iancwm/report-kit", DIGEST, COMMIT, TAG, 1_700_000_000, GATE)
    assert data["image"] == f"ghcr.io/iancwm/report-kit@{DIGEST}"
    assert data["tags"] == [f"sha-{COMMIT}", TAG] and data["platform"] == "linux/amd64"
    assert data["reportkit"]["commit"] == COMMIT and data["gates"]["linux"] == GATE


@pytest.mark.parametrize("digest,commit,tag,gate", [
    ("sha256:short", COMMIT, TAG, GATE), (DIGEST, "abc", TAG, GATE), (DIGEST, COMMIT, "v0.0.0", GATE),
    (DIGEST, COMMIT, TAG, {"passed": False, "image": {"digest": DIGEST}}),
    (DIGEST, COMMIT, TAG, {"passed": True, "image": {"digest": "sha256:" + "c" * 64}}),
])
def test_manifest_rejects_inconsistent_inputs(digest, commit, tag, gate) -> None:
    with pytest.raises(ValueError):
        build_manifest("ghcr.io/iancwm/report-kit", digest, commit, tag, 1, gate)
