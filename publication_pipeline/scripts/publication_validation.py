#!/usr/bin/env python3
"""Static validation for a publication project's manuscript/fragment contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python_scripts"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from reportkit.diagnostics import make_diagnostic  # noqa: E402

SENTINEL_RE = re.compile(r"\[\[REPORTKIT-VISUAL:fig:(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\]\]")
FRAGMENT_RE = re.compile(r"^fig-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.tex$")
LABEL_RE = re.compile(r"\\label\s*\{\s*([^{}]+?)\s*\}")
OPTION_LABEL_RE = re.compile(r"(?<![\\A-Za-z])label\s*=\s*\{\s*([^{}]+?)\s*\}")
DIAGRAM_BEGIN_RE = re.compile(r"\\begin\s*\{\s*diagram\s*\}")
TEX_PATH_RE = re.compile(
    r"\\(?:input|include|includegraphics)(?:\[[^]]*\])?\s*(?:\{([^{}]+)\}|([^\s%{}]+))"
)
TEX_OUTPUT_PATH_RE = re.compile(r"\\openout\s*(?:\d+|\\[A-Za-z@]+)\s*=\s*(?:\{([^{}]+)\}|([^\s%]+))")
SHELL_ESCAPE_RE = re.compile(r"\\(?:immediate\s*\\)?write\s*18\b|\\ShellEscape\b")
MARKDOWN_ASSET_RE = re.compile(r"!?\[[^]]*\]\((?P<path>[^ )]+)(?:\s+['\"][^'\"]*['\"])?\)")


def _diagram_options(text: str) -> tuple[str, str | None]:
    """Return the first diagram's option text and a malformed-group error."""
    match = DIAGRAM_BEGIN_RE.search(text)
    if match is None:
        return "", None
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text) or text[cursor] != "[":
        return "", None

    start = cursor + 1
    cursor = start
    brace_depth = 0
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            if brace_depth == 0:
                return "", "malformed diagram options: unexpected '}' before closing ']'"
            brace_depth -= 1
        elif char == "]" and brace_depth == 0:
            return text[start:cursor], None
        cursor += 1
    if brace_depth:
        return "", "malformed diagram options: unterminated '{...}' value"
    return "", "malformed diagram options: unterminated '[...]' group"


@dataclass
class ValidationResult:
    diagnostics: list[dict] = field(default_factory=list)
    manuscript_files: list[str] = field(default_factory=list)
    slugs: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(item["severity"] == "error" for item in self.diagnostics)

    @property
    def errors(self) -> list[str]:
        """v1.x compatibility view derived from structured diagnostics."""
        return [item["message"] for item in self.diagnostics if item["severity"] == "error"]

    def add(
        self, message: str, *, rule: str, file: str | None = None, line: int | None = None,
        kind: str = "publication_validation",
    ) -> None:
        source = {"file": file} if file else None
        if source is not None and line is not None:
            source["line"] = line
        self.diagnostics.append(make_diagnostic(
            kind, message, code=f"RK_VALIDATION_{rule.upper()}", source=source,
            docs="#/commands/check",
        ))


def validate_publication(root: Path) -> ValidationResult:
    root = root.resolve()
    result = ValidationResult()
    manuscript_dir, fragment_dir = root / "manuscript", root / "fragments"
    order = manuscript_dir / "order.txt"
    if not order.is_file():
        result.add(f"missing manuscript order file: {order}", rule="missing_order", file="manuscript/order.txt")
        return result
    entries: list[str] = []
    seen_entries: set[str] = set()
    for number, raw in enumerate(order.read_text(encoding="utf-8").splitlines(), 1):
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        path = Path(entry)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
            result.add(f"order.txt:{number}: invalid manuscript path: {entry!r}", rule="invalid_manuscript_path", file="manuscript/order.txt", line=number)
            continue
        if entry in seen_entries:
            result.add(f"order.txt:{number}: duplicate manuscript entry: {entry}", rule="duplicate_manuscript", file="manuscript/order.txt", line=number)
            continue
        seen_entries.add(entry)
        entries.append(entry)
        if not (manuscript_dir / entry).is_file():
            result.add(f"order.txt:{number}: missing manuscript: {entry}", rule="missing_manuscript", file="manuscript/order.txt", line=number)
    actual = {path.name for path in manuscript_dir.glob("*.md")}
    for name in sorted(actual - set(entries)):
        result.add(f"manuscript is not listed in order.txt: {name}", rule="unlisted_manuscript", file=f"manuscript/{name}")

    used: dict[str, str] = {}
    for entry in entries:
        manuscript = manuscript_dir / entry
        if not manuscript.is_file():
            continue
        result.manuscript_files.append(entry)
        for number, raw in enumerate(manuscript.read_text(encoding="utf-8").splitlines(), 1):
            for asset_match in MARKDOWN_ASSET_RE.finditer(raw):
                value = asset_match.group("path").strip().replace("\\", "/")
                parsed = Path(value)
                if parsed.is_absolute() or ".." in parsed.parts or re.match(r"^[A-Za-z]:/", value):
                    result.add(
                        f"{manuscript.relative_to(root)}:{number}: Markdown asset path escapes the publication root: {value!r}",
                        rule="asset_path_escape", file=str(manuscript.relative_to(root)), line=number,
                        kind="security_violation",
                    )
            if "REPORTKIT-VISUAL" not in raw:
                continue
            match = SENTINEL_RE.fullmatch(raw.strip())
            if not match:
                result.add(f"{manuscript.relative_to(root)}:{number}: invalid visual sentinel", rule="invalid_visual_sentinel", file=str(manuscript.relative_to(root)), line=number)
                continue
            slug = match.group("slug")
            if slug in used:
                result.add(f"{manuscript.relative_to(root)}:{number}: duplicate visual slug: {slug}", rule="duplicate_visual_slug", file=str(manuscript.relative_to(root)), line=number)
            else:
                used[slug] = f"{manuscript.relative_to(root)}:{number}"
                result.slugs.append(slug)

    if not fragment_dir.is_dir():
        result.add(f"missing fragment directory: {fragment_dir}", rule="missing_fragment_directory", file="fragments")
        return result
    fragments: dict[str, Path] = {}
    for path in sorted(fragment_dir.iterdir()):
        if not path.is_file():
            continue
        match = FRAGMENT_RE.fullmatch(path.name)
        if not match:
            if path.suffix == ".tex" or path.name.startswith("fig-"):
                result.add(f"fragment has an unsupported filename: {path.name}", rule="fragment_filename", file=f"fragments/{path.name}")
            continue
        fragments[match.group("slug")] = path

    for slug, location in used.items():
        path = fragments.get(slug)
        if path is None:
            location_file, _, location_line = location.partition(":")
            result.add(f"{location}: missing fragment: fragments/fig-{slug}.tex", rule="missing_fragment", file=location_file, line=int(location_line) if location_line.isdigit() else None)
            continue
        text = path.read_text(encoding="utf-8")
        for number, raw in enumerate(text.splitlines(), 1):
            if SHELL_ESCAPE_RE.search(raw):
                result.add(
                    f"{path.relative_to(root)}:{number}: shell-escape primitives are forbidden",
                    rule="shell_escape", file=str(path.relative_to(root)), line=number, kind="security_violation",
                )
            for match in TEX_PATH_RE.finditer(raw):
                value = (match.group(1) or match.group(2)).strip().replace("\\", "/")
                candidate = Path(value)
                if candidate.is_absolute() or ".." in candidate.parts or re.match(r"^[A-Za-z]:/", value):
                    result.add(
                        f"{path.relative_to(root)}:{number}: TeX input path escapes the publication root: {value!r}",
                        rule="tex_path_escape", file=str(path.relative_to(root)), line=number, kind="security_violation",
                    )
            for match in TEX_OUTPUT_PATH_RE.finditer(raw):
                value = (match.group(1) or match.group(2)).strip().replace("\\", "/")
                candidate = Path(value)
                if candidate.is_absolute() or ".." in candidate.parts or re.match(r"^[A-Za-z]:/", value):
                    result.add(
                        f"{path.relative_to(root)}:{number}: TeX output path escapes the build directory: {value!r}",
                        rule="tex_output_path_escape", file=str(path.relative_to(root)), line=number,
                        kind="security_violation",
                    )
        if len(re.findall(r"\\begin\s*\{diagram\}", text)) != 1 or len(re.findall(r"\\end\s*\{diagram\}", text)) != 1:
            result.add(f"{path.relative_to(root)}: expected exactly one diagram environment", rule="diagram_count", file=str(path.relative_to(root)))
        options, options_error = _diagram_options(text)
        if options_error:
            result.add(f"{path.relative_to(root)}: {options_error}", rule="diagram_options", file=str(path.relative_to(root)))
        labels = [value.strip() for value in LABEL_RE.findall(text)]
        labels.extend(value.strip() for value in OPTION_LABEL_RE.findall(options))
        if len(labels) != 1:
            result.add(f"{path.relative_to(root)}: expected exactly one diagram label", rule="diagram_label_count", file=str(path.relative_to(root)))
            continue
        label = labels[0]
        result.labels.append(label)
        if label != f"fig:{slug}":
            result.add(f"{path.relative_to(root)}: label {label!r} does not match fig:{slug}", rule="diagram_label", file=str(path.relative_to(root)))

    for slug, path in fragments.items():
        if slug not in used:
            result.add(f"orphan fragment has no manuscript sentinel: {path.relative_to(root)}", rule="orphan_fragment", file=str(path.relative_to(root)))
    for label in sorted({label for label in result.labels if result.labels.count(label) > 1}):
        result.add(f"duplicate diagram label: {label}", rule="duplicate_diagram_label")
    return result
