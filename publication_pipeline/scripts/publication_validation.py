#!/usr/bin/env python3
"""Static validation for a publication project's manuscript/fragment contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

SENTINEL_RE = re.compile(r"\[\[REPORTKIT-VISUAL:fig:(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\]\]")
FRAGMENT_RE = re.compile(r"^fig-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.tex$")
LABEL_RE = re.compile(r"\\label\s*\{\s*([^{}]+?)\s*\}")
OPTION_LABEL_RE = re.compile(r"(?<![\\A-Za-z])label\s*=\s*\{\s*([^{}]+?)\s*\}")


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    manuscript_files: list[str] = field(default_factory=list)
    slugs: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_publication(root: Path) -> ValidationResult:
    root = root.resolve()
    result = ValidationResult()
    manuscript_dir, fragment_dir = root / "manuscript", root / "fragments"
    order = manuscript_dir / "order.txt"
    if not order.is_file():
        result.errors.append(f"missing manuscript order file: {order}")
        return result
    entries: list[str] = []
    seen_entries: set[str] = set()
    for number, raw in enumerate(order.read_text(encoding="utf-8").splitlines(), 1):
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        path = Path(entry)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
            result.errors.append(f"order.txt:{number}: invalid manuscript path: {entry!r}")
            continue
        if entry in seen_entries:
            result.errors.append(f"order.txt:{number}: duplicate manuscript entry: {entry}")
            continue
        seen_entries.add(entry)
        entries.append(entry)
        if not (manuscript_dir / entry).is_file():
            result.errors.append(f"order.txt:{number}: missing manuscript: {entry}")
    actual = {path.name for path in manuscript_dir.glob("*.md")}
    for name in sorted(actual - set(entries)):
        result.errors.append(f"manuscript is not listed in order.txt: {name}")

    used: dict[str, str] = {}
    for entry in entries:
        manuscript = manuscript_dir / entry
        if not manuscript.is_file():
            continue
        result.manuscript_files.append(entry)
        for number, raw in enumerate(manuscript.read_text(encoding="utf-8").splitlines(), 1):
            if "REPORTKIT-VISUAL" not in raw:
                continue
            match = SENTINEL_RE.fullmatch(raw.strip())
            if not match:
                result.errors.append(f"{manuscript.relative_to(root)}:{number}: invalid visual sentinel")
                continue
            slug = match.group("slug")
            if slug in used:
                result.errors.append(f"{manuscript.relative_to(root)}:{number}: duplicate visual slug: {slug}")
            else:
                used[slug] = f"{manuscript.relative_to(root)}:{number}"
                result.slugs.append(slug)

    if not fragment_dir.is_dir():
        result.errors.append(f"missing fragment directory: {fragment_dir}")
        return result
    fragments: dict[str, Path] = {}
    for path in sorted(fragment_dir.iterdir()):
        if not path.is_file():
            continue
        match = FRAGMENT_RE.fullmatch(path.name)
        if not match:
            if path.suffix == ".tex" or path.name.startswith("fig-"):
                result.errors.append(f"fragment has an unsupported filename: {path.name}")
            continue
        fragments[match.group("slug")] = path

    for slug, location in used.items():
        path = fragments.get(slug)
        if path is None:
            result.errors.append(f"{location}: missing fragment: fragments/fig-{slug}.tex")
            continue
        text = path.read_text(encoding="utf-8")
        if len(re.findall(r"\\begin\s*\{diagram\}", text)) != 1 or len(re.findall(r"\\end\s*\{diagram\}", text)) != 1:
            result.errors.append(f"{path.relative_to(root)}: expected exactly one diagram environment")
        labels = [value.strip() for value in LABEL_RE.findall(text)]
        labels.extend(value.strip() for value in OPTION_LABEL_RE.findall(text))
        if len(labels) != 1:
            result.errors.append(f"{path.relative_to(root)}: expected exactly one diagram label")
            continue
        label = labels[0]
        result.labels.append(label)
        if label != f"fig:{slug}":
            result.errors.append(f"{path.relative_to(root)}: label {label!r} does not match fig:{slug}")

    for slug, path in fragments.items():
        if slug not in used:
            result.errors.append(f"orphan fragment has no manuscript sentinel: {path.relative_to(root)}")
    for label in sorted({label for label in result.labels if result.labels.count(label) > 1}):
        result.errors.append(f"duplicate diagram label: {label}")
    return result
