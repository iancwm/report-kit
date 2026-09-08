"""Summaries over ReportKit build history."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


def analyse_history(history_dir: Path) -> dict[str, Any]:
    reports: list[dict[str, Any]] = []
    for path in sorted(history_dir.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            reports.append(value)
    types: Counter[str] = Counter()
    owners: Counter[str] = Counter()
    allowlist: Counter[str] = Counter()
    builds_by_type: defaultdict[str, set[str]] = defaultdict(set)
    for report in reports:
        build_id = str(report.get("build_id", "unknown"))
        diagnostics = report.get("diagnostics", {})
        for issue in diagnostics.get("issues", []) if isinstance(diagnostics, dict) else []:
            if not isinstance(issue, dict):
                continue
            kind = str(issue.get("type", "unknown"))
            types[kind] += 1
            owners[str(issue.get("owner", "UNKNOWN"))] += 1
            builds_by_type[kind].add(build_id)
            if kind == "allowlist":
                allowlist[str(issue.get("message", "unknown"))] += 1
    recurring = [
        {"type": kind, "occurrences": count, "builds": len(builds_by_type[kind])}
        for kind, count in sorted(types.items(), key=lambda item: (-item[1], item[0]))
        if len(builds_by_type[kind]) > 1
    ]
    candidates = [item for item in recurring if item["type"] in {"package_warning", "overfull_hbox", "underfull_hbox", "ignored_error"}]
    return {
        "history_dir": str(history_dir),
        "build_count": len(reports),
        "diagnostic_counts": dict(sorted(types.items())),
        "owner_counts": dict(sorted(owners.items())),
        "recurring": recurring,
        "repeated_allowlist_entries": [{"message": message, "occurrences": count} for message, count in allowlist.most_common() if count > 1],
        "primitive_candidates": candidates,
    }
