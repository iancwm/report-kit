"""Build manifest and history helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_report(report: dict[str, Any], path: Path, history_root: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")
    if history_root is not None:
        history_root.mkdir(parents=True, exist_ok=True)
        history_path = history_root / f"{report['build_id']}.json"
        history_path.write_text(payload, encoding="utf-8")


def unique_build_id(mode: str, stamp: str, history_root: Path) -> str:
    candidate = f"{mode}-{stamp}"
    index = 1
    while (history_root / f"{candidate}.json").exists():
        candidate = f"{mode}-{stamp}-{index}"
        index += 1
    return candidate
