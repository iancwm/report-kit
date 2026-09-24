"""Declaration and path helpers for replaceable publication image slots.

The accepted manifest is deliberately small YAML: one ``images`` mapping,
slot mappings keyed by slug, and scalar fields inside each slot. Keeping the
parser here avoids adding a runtime YAML dependency to ReportKit.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .config import _scalar, _yaml_tokens


IMAGE_SLOTS_FILENAME = "image-slots.yaml"
IMAGE_DIRECTORY = "assets/images"
SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".pdf")
ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "wide": (16, 9),
    "landscape": (4, 3),
    "square": (1, 1),
    "portrait": (3, 4),
}
IMAGE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE_SENTINEL_RE = re.compile(r"^\[\[REPORTKIT-IMAGE:img:(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\]\]$")
IMAGE_SENTINEL_MARKER = "REPORTKIT-IMAGE"
IMAGE_FIELDS = (
    "purpose", "caption", "alt", "aspect_ratio", "path", "source", "creator",
    "license", "attribution", "restrictions",
)
RIGHTS_FIELDS = ("source", "creator", "license", "attribution", "restrictions")
PENDING_RIGHTS_VALUES = {
    "pending", "unknown", "tbd", "todo", "unspecified", "to be determined",
    "not yet determined", "not yet known",
}


@dataclass
class ImageSlot:
    """A normalized declared image slot and its first manuscript use."""

    slug: str
    purpose: str
    caption: str
    alt: str
    aspect_ratio: str
    path: str
    source: str
    creator: str
    license: str
    attribution: str
    restrictions: str
    state: str
    manuscript_file: str | None = None
    manuscript_line: int | None = None
    unresolved_reason: str | None = None


@dataclass(frozen=True)
class ImageManifestIssue:
    """A manifest syntax or shape problem with a source location."""

    message: str
    line: int | None = None


def _key_value(content: str, path: Path, line: int) -> tuple[str, str]:
    if ":" not in content:
        raise ValueError(f"{path}:{line}: expected key: value")
    key, raw = content.split(":", 1)
    key = key.strip()
    if not key or any(char.isspace() for char in key):
        raise ValueError(f"{path}:{line}: invalid mapping key {key!r}")
    return key, raw.strip()


def is_pending_rights_value(value: str, field_name: str) -> bool:
    """Return whether a rights field explicitly marks its value unresolved."""
    folded = value.strip().casefold()
    if field_name == "restrictions" and folded in {"none", "no restrictions", "unrestricted"}:
        return False
    return (
        folded in PENDING_RIGHTS_VALUES
        or re.match(r"^(?:pending|unknown|tbd|todo|unspecified)(?:\b|[.:;])", folded) is not None
        or folded.startswith("to be determined")
        or folded.startswith("not yet determined")
        or folded.startswith("not yet known")
        or (value.startswith("[") and value.endswith("]"))
    )


def parse_image_slots(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, int], list[ImageManifestIssue]]:
    """Parse ``image-slots.yaml`` and return raw records, slug lines, and issues.

    Parsing is intentionally limited to the manifest shape used by consumers;
    unsupported YAML constructs become actionable validation issues.
    """
    records: dict[str, dict[str, Any]] = {}
    slug_lines: dict[str, int] = {}
    issues: list[ImageManifestIssue] = []
    try:
        tokens = _yaml_tokens(path)
    except (OSError, UnicodeError, ValueError) as exc:
        return records, slug_lines, [ImageManifestIssue(str(exc))]
    if not tokens:
        return records, slug_lines, [ImageManifestIssue(f"{path}: manifest is empty")]

    first_line, first_indent, first_content = tokens[0]
    try:
        top_key, top_raw = _key_value(first_content, path, first_line)
    except ValueError as exc:
        return records, slug_lines, [ImageManifestIssue(str(exc), first_line)]
    if first_indent != 0 or top_key != "images" or top_raw:
        issues.append(ImageManifestIssue(f"{path}:{first_line}: expected top-level 'images:' mapping", first_line))
        return records, slug_lines, issues

    top_seen = {top_key}
    active_slug: str | None = None
    active_record: dict[str, Any] | None = None
    field_lines: dict[str, int] = {}
    for line_number, indent, content in tokens[1:]:
        try:
            key, raw_value = _key_value(content, path, line_number)
        except ValueError as exc:
            issues.append(ImageManifestIssue(str(exc), line_number))
            continue
        if indent == 0:
            if key in top_seen:
                issues.append(ImageManifestIssue(f"{path}:{line_number}: duplicate top-level key {key!r}", line_number))
            else:
                issues.append(ImageManifestIssue(f"{path}:{line_number}: unexpected top-level key {key!r}; only 'images' is allowed", line_number))
            top_seen.add(key)
            active_slug = None
            active_record = None
            continue
        if indent == 2:
            if raw_value:
                issues.append(ImageManifestIssue(f"{path}:{line_number}: image slot {key!r} must be a mapping", line_number))
                active_slug = None
                active_record = None
                continue
            if not IMAGE_SLUG_RE.fullmatch(key):
                issues.append(ImageManifestIssue(f"{path}:{line_number}: invalid image slot slug {key!r}; use lowercase letters, digits, and single hyphens", line_number))
            if key in records:
                issues.append(ImageManifestIssue(f"{path}:{line_number}: duplicate image slot slug {key!r}", line_number))
                active_slug = None
                active_record = None
                continue
            records[key] = {}
            slug_lines[key] = line_number
            active_slug = key
            active_record = records[key]
            active_record["_slug_line"] = line_number
            field_lines = {}
            continue
        if indent != 4 or active_record is None or active_slug is None:
            issues.append(ImageManifestIssue(f"{path}:{line_number}: expected a slot at two spaces and its fields at four spaces", line_number))
            continue
        if key in field_lines:
            issues.append(ImageManifestIssue(f"{path}:{line_number}: duplicate field {key!r} for image slot {active_slug!r}", line_number))
            continue
        field_lines[key] = line_number
        if key not in IMAGE_FIELDS:
            issues.append(ImageManifestIssue(f"{path}:{line_number}: unknown field {key!r} for image slot {active_slug!r}", line_number))
            continue
        if raw_value and (raw_value[0] in "'\"" or raw_value[-1] in "'\""):
            quote = raw_value[0]
            if quote not in "'\"" or raw_value[-1] != quote:
                issues.append(ImageManifestIssue(f"{path}:{line_number}: unterminated quoted value for {key!r}", line_number))
                continue
        if raw_value.startswith(("'", '"')) and len(raw_value) < 2:
            issues.append(ImageManifestIssue(f"{path}:{line_number}: unterminated quoted value for {key!r}", line_number))
            continue
        try:
            value = _scalar(raw_value, path, line_number)
        except ValueError as exc:
            issues.append(ImageManifestIssue(str(exc), line_number))
            continue
        active_record[key] = value
        active_record[f"_{key}_line"] = line_number

    return records, slug_lines, issues


def resolve_image_path(root: Path, slug: str, raw_path: str) -> tuple[Path | None, str | None]:
    """Validate the declared asset path and resolve it without following escapes."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "path must be a non-empty relative path under assets/images/"
    value = raw_path.strip()
    if "\\" in value:
        return None, "path must use forward slashes and stay under assets/images/"
    candidate = Path(value)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:", value) or ".." in candidate.parts:
        return None, "path must be relative and may not contain '..' or an absolute prefix"
    path_parts = value.split("/")
    if len(path_parts) != 3 or path_parts[:2] != list(Path(IMAGE_DIRECTORY).parts):
        return None, f"path must have the form assets/images/{slug}.<extension>"
    if path_parts[2].rsplit(".", 1)[0] != slug:
        return None, f"filename must match slot slug {slug!r}"
    if candidate.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        extensions = ", ".join(SUPPORTED_IMAGE_EXTENSIONS)
        return None, f"unsupported image extension {candidate.suffix or '(none)'}; supported formats: {extensions}"

    root_resolved = root.resolve()
    image_dir = root / IMAGE_DIRECTORY
    declared = root / candidate
    try:
        if image_dir.exists() and not image_dir.is_dir():
            return None, "assets/images exists but is not a directory"
        resolved_image_dir = image_dir.resolve(strict=False)
        resolved = declared.resolve(strict=False)
        resolved.relative_to(root_resolved)
        resolved.relative_to(resolved_image_dir)
    except (OSError, RuntimeError):
        return None, "could not resolve image path safely (check symlinks)"
    except ValueError:
        return None, "resolved image path escapes the publication's assets/images directory (check symlinks)"
    return declared, None


def normalize_image_slot(
    slug: str,
    values: dict[str, Any],
    *,
    path: Path,
    root: Path,
    manuscript_file: str | None = None,
    manuscript_line: int | None = None,
) -> tuple[ImageSlot, list[ImageManifestIssue]]:
    """Build a typed slot record and report field/path errors."""
    issues: list[ImageManifestIssue] = []
    normalized: dict[str, str] = {}
    slug_line = values.get("_slug_line")
    for field_name in IMAGE_FIELDS:
        value = values.get(field_name)
        if not isinstance(value, str) or not value.strip():
            issues.append(ImageManifestIssue(
                f"{path}:{slug}: required field {field_name!r} must have a non-empty text value",
                values.get(f"_{field_name}_line") or slug_line,
            ))
            normalized[field_name] = ""
        else:
            normalized[field_name] = value.strip()

    ratio = normalized["aspect_ratio"]
    if ratio not in ASPECT_RATIOS:
        issues.append(ImageManifestIssue(
            f"{path}:{slug}: unknown aspect_ratio {ratio!r}; choose one of {', '.join(ASPECT_RATIOS)}",
            values.get("_aspect_ratio_line") or slug_line,
        ))

    declared_path, path_error = resolve_image_path(root, slug, normalized["path"])
    if path_error:
        issues.append(ImageManifestIssue(
            f"{path}:{slug}: unsafe or unsupported image path {normalized['path']!r}: {path_error}",
            values.get("_path_line") or slug_line,
        ))

    state = "invalid" if path_error else ("supplied" if declared_path and declared_path.is_file() else "placeholder")
    unresolved_reasons: list[str] = []
    if state == "placeholder":
        unresolved_reasons.append(f"missing image file {normalized['path']}")

    for field_name in RIGHTS_FIELDS:
        value = normalized[field_name]
        folded = value.casefold()
        if field_name == "restrictions" and folded in {"none", "no restrictions", "unrestricted"}:
            continue
        if folded in {"", "none", "n/a", "na", "not applicable"}:
            issues.append(ImageManifestIssue(
                f"{path}:{slug}: {field_name!r} must identify concrete rights or credit information; use 'restrictions: none' only when there are no restrictions",
                values.get(f"_{field_name}_line") or slug_line,
            ))
        elif is_pending_rights_value(value, field_name):
            unresolved_reasons.append(f"pending {field_name}")

    slot = ImageSlot(
        slug=slug,
        purpose=normalized["purpose"],
        caption=normalized["caption"],
        alt=normalized["alt"],
        aspect_ratio=ratio,
        path=normalized["path"],
        source=normalized["source"],
        creator=normalized["creator"],
        license=normalized["license"],
        attribution=normalized["attribution"],
        restrictions=normalized["restrictions"],
        state=state,
        manuscript_file=manuscript_file,
        manuscript_line=manuscript_line,
        unresolved_reason="; ".join(unresolved_reasons) if unresolved_reasons else None,
    )
    return slot, issues
