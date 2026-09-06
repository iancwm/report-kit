#!/usr/bin/env python3
"""Static validation for the Data Engineering Guide source tree."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


SENTINEL_RE = re.compile(
    r"\[\[REPORTKIT-VISUAL:fig:(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\]\]"
)
SENTINEL_MARKER = "REPORTKIT-VISUAL"
FRAGMENT_RE = re.compile(r"^fig-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.tex$")
LABEL_RE = re.compile(r"\\label\s*\{\s*([^{}]+?)\s*\}")
OPTION_LABEL_RE = re.compile(r"(?<![\\A-Za-z])label\s*=\s*\{\s*([^{}]+?)\s*\}")
DIAGRAM_BEGIN_RE = re.compile(r"\\begin\s*\{diagram\}")
DIAGRAM_END_RE = re.compile(r"\\end\s*\{diagram\}")


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    manuscript_files: list[str] = field(default_factory=list)
    slugs: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _error(result: ValidationResult, message: str) -> None:
    result.errors.append(message)


def _read_order(root: Path, result: ValidationResult) -> list[str]:
    order_path = root / "manuscript" / "order.txt"
    if not order_path.is_file():
        _error(result, f"missing manuscript order file: {order_path}")
        return []

    entries: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(order_path.read_text(encoding="utf-8").splitlines(), 1):
        entry = raw_line.strip()
        if not entry or entry.startswith("#"):
            continue
        path = Path(entry)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
            _error(result, f"order.txt:{line_number}: invalid manuscript path: {entry!r}")
            continue
        if entry in seen:
            _error(result, f"order.txt:{line_number}: duplicate manuscript entry: {entry}")
            continue
        seen.add(entry)
        entries.append(entry)
        manuscript = root / "manuscript" / entry
        if not manuscript.is_file():
            _error(result, f"order.txt:{line_number}: missing manuscript: {entry}")
    return entries


def _validate_manuscripts(root: Path, entries: list[str], result: ValidationResult) -> dict[str, str]:
    manuscript_dir = root / "manuscript"
    actual = {path.name for path in manuscript_dir.glob("*.md")}
    ordered = {Path(entry).name for entry in entries}
    for missing in sorted(actual - ordered):
        _error(result, f"manuscript is not listed in order.txt: {missing}")
    for unknown in sorted(ordered - actual):
        _error(result, f"order.txt references a manuscript that is not present: {unknown}")

    used: dict[str, str] = {}
    for entry in entries:
        manuscript = manuscript_dir / entry
        if not manuscript.is_file():
            continue
        result.manuscript_files.append(entry)
        for line_number, raw_line in enumerate(manuscript.read_text(encoding="utf-8").splitlines(), 1):
            stripped = raw_line.strip()
            if SENTINEL_MARKER not in raw_line:
                continue
            match = SENTINEL_RE.fullmatch(stripped)
            if not match:
                _error(
                    result,
                    f"{manuscript.relative_to(root)}:{line_number}: invalid visual sentinel; "
                    "use [[REPORTKIT-VISUAL:fig:lowercase-kebab-slug]] on its own line",
                )
                continue
            slug = match.group("slug")
            if slug in used:
                _error(
                    result,
                    f"{manuscript.relative_to(root)}:{line_number}: duplicate visual slug "
                    f"{slug!r}; already used in {used[slug]}",
                )
            else:
                used[slug] = f"{manuscript.relative_to(root)}:{line_number}"
                result.slugs.append(slug)
    return used


def _validate_fragments(root: Path, used: dict[str, str], result: ValidationResult) -> None:
    fragment_dir = root / "fragments"
    if not fragment_dir.is_dir():
        _error(result, f"missing fragment directory: {fragment_dir}")
        return

    fragments: dict[str, Path] = {}
    for path in sorted(fragment_dir.iterdir()):
        if not path.is_file():
            continue
        match = FRAGMENT_RE.fullmatch(path.name)
        if not match:
            if path.suffix == ".tex" or path.name.startswith("fig-"):
                _error(result, f"fragment has an unsupported filename: {path.name}")
            continue
        slug = match.group("slug")
        fragments[slug] = path

    for slug, location in sorted(used.items()):
        path = fragments.get(slug)
        if path is None:
            _error(result, f"{location}: missing fragment: fragments/fig-{slug}.tex")
            continue
        text = path.read_text(encoding="utf-8")
        begins = len(DIAGRAM_BEGIN_RE.findall(text))
        ends = len(DIAGRAM_END_RE.findall(text))
        if begins != 1 or ends != 1:
            _error(
                result,
                f"{path.relative_to(root)}: expected exactly one diagram block, found "
                f"{begins} begin and {ends} end markers",
            )
        labels = [label.strip() for label in LABEL_RE.findall(text)]
        labels.extend(label.strip() for label in OPTION_LABEL_RE.findall(text))
        if len(labels) != 1:
            _error(
                result,
                f"{path.relative_to(root)}: expected exactly one diagram label, found {len(labels)}",
            )
            continue
        label = labels[0]
        result.labels.append(label)
        expected = f"fig:{slug}"
        if label != expected:
            _error(
                result,
                f"{path.relative_to(root)}: label {label!r} does not match sentinel slug {expected!r}",
            )

    for slug, path in sorted(fragments.items()):
        if slug not in used:
            _error(result, f"orphan fragment has no manuscript sentinel: {path.relative_to(root)}")

    duplicates = sorted({label for label in result.labels if result.labels.count(label) > 1})
    for label in duplicates:
        _error(result, f"duplicate diagram label: {label}")


def validate_guide(root: Path) -> ValidationResult:
    """Validate manuscript order, sentinels, fragments, and labels."""
    root = root.resolve()
    result = ValidationResult()
    entries = _read_order(root, result)
    used = _validate_manuscripts(root, entries, result)
    _validate_fragments(root, used, result)
    return result
