#!/usr/bin/env python3
"""Static validation for a publication project's manuscript/fragment contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from reportkit.diagnostics import make_diagnostic  # noqa: E402
from reportkit.image_slots import (
    IMAGE_SENTINEL_MARKER,
    IMAGE_SENTINEL_RE,
    IMAGE_SLOTS_FILENAME,
    ImageSlot,
    is_pending_rights_value,
    normalize_image_slot,
    parse_image_slots,
)

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
TRUSTED_FRAGMENT_RE = re.compile(r"^\s*fragment\s*:\s*(?P<value>\S+)\s*$")


def _safe_trusted_fragment_name(value: str) -> str | None:
    """Return a contained composition-fragment filename, if it is safe."""
    normalized = value.strip().replace("\\", "/")
    if normalized.startswith("fragments/"):
        normalized = normalized.removeprefix("fragments/")
    if not normalized.endswith(".tex"):
        normalized += ".tex"
    candidate = Path(normalized)
    if (
        candidate.parent != Path(".")
        or candidate.suffix != ".tex"
        or not FRAGMENT_RE.fullmatch(candidate.name)
    ):
        return None
    return candidate.name


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
    image_slots: dict[str, ImageSlot] = field(default_factory=dict)
    unresolved_image_slots: list[ImageSlot] = field(default_factory=list)
    profile: str = "draft"

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
        severity: str = "error",
    ) -> None:
        source = {"file": file} if file else None
        if source is not None and line is not None:
            source["line"] = line
        self.diagnostics.append(make_diagnostic(
            kind, message, code=f"RK_VALIDATION_{rule.upper()}", severity=severity, source=source,
            docs="#/commands/check",
        ))


def _validate_fragment_safety(result: ValidationResult, root: Path, path: Path) -> str:
    """Scan a fragment for forbidden execution or escaping file paths."""
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
    return text


def validate_publication(root: Path, profile: str = "draft") -> ValidationResult:
    root = root.resolve()
    selected_profile = profile or "draft"
    result = ValidationResult(profile=selected_profile)
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
    used_images: dict[str, tuple[str, int]] = {}
    trusted_fragments: set[str] = set()
    for entry in entries:
        manuscript = manuscript_dir / entry
        if not manuscript.is_file():
            continue
        result.manuscript_files.append(entry)
        for number, raw in enumerate(manuscript.read_text(encoding="utf-8").splitlines(), 1):
            trusted_match = TRUSTED_FRAGMENT_RE.fullmatch(raw)
            if trusted_match:
                trusted_name = _safe_trusted_fragment_name(trusted_match.group("value"))
                if trusted_name is not None:
                    trusted_fragments.add(trusted_name)
            for asset_match in MARKDOWN_ASSET_RE.finditer(raw):
                value = asset_match.group("path").strip().replace("\\", "/")
                parsed = Path(value)
                if parsed.is_absolute() or ".." in parsed.parts or re.match(r"^[A-Za-z]:/", value):
                    result.add(
                        f"{manuscript.relative_to(root)}:{number}: Markdown asset path escapes the publication root: {value!r}",
                        rule="asset_path_escape", file=str(manuscript.relative_to(root)), line=number,
                        kind="security_violation",
                    )
            if "REPORTKIT-VISUAL" in raw:
                visual_match = SENTINEL_RE.fullmatch(raw.strip())
                if not visual_match:
                    result.add(f"{manuscript.relative_to(root)}:{number}: invalid visual sentinel", rule="invalid_visual_sentinel", file=str(manuscript.relative_to(root)), line=number)
                else:
                    slug = visual_match.group("slug")
                    if slug in used:
                        result.add(f"{manuscript.relative_to(root)}:{number}: duplicate visual slug: {slug}", rule="duplicate_visual_slug", file=str(manuscript.relative_to(root)), line=number)
                    else:
                        used[slug] = f"{manuscript.relative_to(root)}:{number}"
                        result.slugs.append(slug)

            if IMAGE_SENTINEL_MARKER not in raw.upper():
                continue
            image_match = IMAGE_SENTINEL_RE.fullmatch(raw.strip())
            if not image_match:
                result.add(
                    f"{manuscript.relative_to(root)}:{number}: invalid image sentinel; put exactly [[REPORTKIT-IMAGE:img:<slug>]] on its own line",
                    rule="invalid_image_sentinel", file=str(manuscript.relative_to(root)), line=number,
                )
                continue
            image_slug = image_match.group("slug")
            location = (str(manuscript.relative_to(root)), number)
            if image_slug in used_images:
                result.add(
                    f"{manuscript.relative_to(root)}:{number}: duplicate image slot use: {image_slug}",
                    rule="duplicate_image_slot_use", file=str(manuscript.relative_to(root)), line=number,
                )
            else:
                used_images[image_slug] = location

    if not fragment_dir.is_dir():
        result.add(f"missing fragment directory: {fragment_dir}", rule="missing_fragment_directory", file="fragments")
    fragments: dict[str, Path] = {}
    for path in (sorted(fragment_dir.iterdir()) if fragment_dir.is_dir() else ()):
        if not path.is_file():
            continue
        match = FRAGMENT_RE.fullmatch(path.name)
        if not match:
            if path.suffix == ".tex" or path.name.startswith("fig-"):
                result.add(f"fragment has an unsupported filename: {path.name}", rule="fragment_filename", file=f"fragments/{path.name}")
            continue
        fragments[match.group("slug")] = path

    for trusted_name in sorted(trusted_fragments):
        trusted_path = fragment_dir / trusted_name
        if not trusted_path.is_file():
            result.add(
                f"missing trusted composition fragment: fragments/{trusted_name}",
                rule="missing_trusted_fragment",
                file=f"fragments/{trusted_name}",
            )
        else:
            _validate_fragment_safety(result, root, trusted_path)

    for slug, location in used.items():
        path = fragments.get(slug)
        if path is None:
            location_file, _, location_line = location.partition(":")
            result.add(f"{location}: missing fragment: fragments/fig-{slug}.tex", rule="missing_fragment", file=location_file, line=int(location_line) if location_line.isdigit() else None)
            continue
        text = _validate_fragment_safety(result, root, path)
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
        if slug not in used and path.name not in trusted_fragments:
            result.add(f"orphan fragment has no manuscript sentinel: {path.relative_to(root)}", rule="orphan_fragment", file=str(path.relative_to(root)))
    for label in sorted({label for label in result.labels if result.labels.count(label) > 1}):
        result.add(f"duplicate diagram label: {label}", rule="duplicate_diagram_label")

    manifest = root / IMAGE_SLOTS_FILENAME
    declared: dict[str, dict] = {}
    declaration_lines: dict[str, int] = {}
    if manifest.is_file():
        declared, declaration_lines, manifest_issues = parse_image_slots(manifest)
        for issue in manifest_issues:
            result.add(
                issue.message,
                rule="image_manifest_syntax",
                file=IMAGE_SLOTS_FILENAME,
                line=issue.line,
            )

    for slug, (manuscript_file, manuscript_line) in used_images.items():
        if slug not in declared:
            result.add(
                f"{manuscript_file}:{manuscript_line}: image slot {slug!r} has no declaration in {IMAGE_SLOTS_FILENAME}",
                rule="missing_image_declaration",
                file=manuscript_file,
                line=manuscript_line,
            )
    for slug, values in declared.items():
        use = used_images.get(slug)
        manuscript_file, manuscript_line = use if use else (None, None)
        slot, slot_issues = normalize_image_slot(
            slug,
            values,
            path=manifest,
            root=root,
            manuscript_file=manuscript_file,
            manuscript_line=manuscript_line,
        )
        result.image_slots[slug] = slot
        if use is None:
            result.add(
                f"{IMAGE_SLOTS_FILENAME}:{declaration_lines.get(slug, 1)}: orphan image slot declaration {slug!r} has no manuscript sentinel",
                rule="orphan_image_declaration",
                file=IMAGE_SLOTS_FILENAME,
                line=declaration_lines.get(slug),
            )
        for issue in slot_issues:
            result.add(
                issue.message,
                rule="image_slot_metadata_or_path",
                file=IMAGE_SLOTS_FILENAME,
                line=issue.line,
            )
        if slot.unresolved_reason:
            result.unresolved_image_slots.append(slot)
            strict_profile = selected_profile.casefold() in {"final", "release"}
            if slot.state == "placeholder":
                result.add(
                    f"image slot {slug!r} is missing {slot.path!r}; add the file inside assets/images/ or correct the declaration",
                    rule="image_slot_missing_file",
                    file=manuscript_file or IMAGE_SLOTS_FILENAME,
                    line=manuscript_line if use else declaration_lines.get(slug),
                    severity="error" if strict_profile else "warning",
                )
            pending_fields = [
                field_name for field_name in ("source", "creator", "license", "attribution", "restrictions")
                if is_pending_rights_value(getattr(slot, field_name), field_name)
            ]
            if pending_fields:
                result.add(
                    f"image slot {slug!r} has pending rights or credit fields ({', '.join(pending_fields)}); record concrete source, creator, license, attribution, and restrictions before final/release",
                    rule="image_slot_pending_rights",
                    file=IMAGE_SLOTS_FILENAME,
                    line=declaration_lines.get(slug),
                    severity="error" if strict_profile else "warning",
                )
    return result
