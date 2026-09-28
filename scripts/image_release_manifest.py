#!/usr/bin/env python3
"""Emit the machine-readable release manifest for a gated toolchain image."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_scripts"))

from reportkit.version import CONTRACT_VERSION, REPORTKIT_VERSION  # noqa: E402

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def build_manifest(repository: str, digest: str, commit: str, tag: str, source_date_epoch: int, gate_summary: dict) -> dict:
    if not DIGEST.match(digest):
        raise ValueError(f"not a sha256 digest: {digest}")
    if not COMMIT.match(commit):
        raise ValueError(f"not a full commit SHA: {commit}")
    if tag != f"v{REPORTKIT_VERSION}":
        raise ValueError(f"tag {tag} does not match REPORTKIT_VERSION {REPORTKIT_VERSION}")
    if not gate_summary.get("passed") or gate_summary.get("image", {}).get("digest") != digest:
        raise ValueError("the Linux gate summary did not pass for this digest")
    return {
        "schema": "reportkit-image-release/1", "image": f"{repository}@{digest}", "repository": repository,
        "digest": digest, "platform": "linux/amd64", "tags": [f"sha-{commit}", tag],
        "reportkit": {"version": REPORTKIT_VERSION, "contract_version": CONTRACT_VERSION, "commit": commit, "ref": tag},
        "source_date_epoch": source_date_epoch, "gates": {"linux": gate_summary},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "digest", "commit", "tag", "gate-summary"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--source-date-epoch", type=int, required=True)
    args = parser.parse_args()
    gate = json.loads(Path(args.gate_summary).read_text(encoding="utf-8"))
    print(json.dumps(build_manifest(args.repository, args.digest, args.commit, args.tag, args.source_date_epoch, gate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
