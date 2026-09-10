"""Deterministic contract-derived Markdown reference generation."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

START = "<!-- REPORTKIT-CONTRACT:START -->"
END = "<!-- REPORTKIT-CONTRACT:END -->"


def _cell(value: Any) -> str:
    text = str(value).replace("\n", "<br>").replace("|", "&#124;")
    return html.escape(text, quote=False).replace("&amp;#124;", "&#124;")


def _arguments(record: dict[str, Any]) -> str:
    values = []
    for argument in record["arguments"]:
        required = "required" if argument["required"] else "optional"
        default = "" if argument.get("default") is None else f"={argument['default']}"
        values.append(f"`{argument['name']}` ({_cell(argument['type'])}, {required}{_cell(default)}) — {_cell(argument['description'])}")
    return "<br>".join(values) if values else "—"


def _constraints(record: dict[str, Any]) -> str:
    return "<br>".join(_cell(item.get("description", item.get("code", "constraint"))) for item in record["constraints"]) or "—"


def render_reference(registry: dict[str, Any], *, publication_type: str | None = None) -> str:
    lines = [
        START,
        "## Generated primitive contract",
        "",
        "This section is generated from source-adjacent contract metadata. Do not edit it by hand.",
        "",
    ]
    for kind, records in registry["primitives"].items():
        selected = [record for record in records.values() if not publication_type or publication_type in record["available_in"]["publication_types"]]
        if not selected:
            continue
        lines.extend([
            f"### {kind.title()} primitives",
            "",
            "| Name | Signature | Arguments | Constraints | Stability | Canonical example |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for record in sorted(selected, key=lambda item: item["name"]):
            stability = f"{record['stability']} since {record['since']}"
            lines.append(
                f"| `{record['name']}` | `{_cell(record['signature'])}` | {_arguments(record)} | "
                f"{_constraints(record)} | {_cell(stability)} | <code>{_cell(record['example'])}</code> |"
            )
        lines.append("")
    lines.extend([END, ""])
    return "\n".join(lines)


def _replace_generated(text: str, generated: str) -> str:
    if START not in text and END not in text:
        return text.rstrip() + "\n\n" + generated
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise ValueError("generated contract markers are missing, duplicated, or out of order")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    return before.rstrip() + "\n\n" + generated.rstrip() + "\n" + after.lstrip("\n")


def generated_documents(repo_root: Path, registry: dict[str, Any]) -> dict[Path, str]:
    targets = {
        repo_root / "SKILL.md": render_reference(registry),
        repo_root / "references" / "institutional-research-theme.md": render_reference(registry, publication_type="equity-research"),
    }
    return {
        path: _replace_generated(path.read_text(encoding="utf-8"), generated)
        for path, generated in targets.items()
    }


def check_documentation(repo_root: Path, *, registry: dict[str, Any]) -> list[str]:
    errors = []
    for path, expected in generated_documents(repo_root, registry).items():
        if path.read_text(encoding="utf-8") != expected:
            errors.append(f"generated contract documentation drift: {path.relative_to(repo_root)}")
    return errors


def write_documentation(repo_root: Path, *, registry: dict[str, Any]) -> list[str]:
    changed = []
    for path, expected in generated_documents(repo_root, registry).items():
        if path.read_text(encoding="utf-8") != expected:
            path.write_text(expected, encoding="utf-8")
            changed.append(str(path.relative_to(repo_root)))
    return changed
