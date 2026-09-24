"""Shared image-slot sentinel rendering for publication pipeline paths."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

from reportkit.latex import tex_escape


IMAGE_SENTINEL_RE = re.compile(
    r"^\s*(?:\[\[|\{\[\}\{\[\})REPORTKIT-IMAGE:img:"
    r"(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)"
    r"(?:\]\]|\{\]\}\{\]\})\s*$"
)
SAFE_IMAGE_PATH_RE = re.compile(
    r"^assets/images/[a-z0-9]+(?:-[a-z0-9]+)*(?:\.(?i:png|jpe?g|pdf))$"
)


def image_field(slot: Any, name: str, default: Any = "") -> Any:
    """Read a typed slot field while also accepting mapping-shaped records."""
    if isinstance(slot, Mapping):
        return slot.get(name, default)
    return getattr(slot, name, default)


def image_state(slot: Any, source_root: Path) -> str:
    """Return the render state using the validated local replacement path."""
    path = str(image_field(slot, "path", ""))
    if not SAFE_IMAGE_PATH_RE.fullmatch(path):
        raise ValueError(f"image slot has an unsafe or unsupported replacement path: {path!r}")
    return "supplied" if (source_root / path).is_file() else "placeholder"


def image_source_credit(slot: Any) -> str:
    """Combine declared source and credit into the theme's source line."""
    source = str(image_field(slot, "source", "")).strip()
    creator = str(image_field(slot, "creator", "")).strip()
    attribution = str(image_field(slot, "attribution", "")).strip()
    license_name = str(image_field(slot, "license", "")).strip()
    credit = attribution or creator
    parts = [part for part in (source, credit) if part]
    if license_name:
        parts.append(f"license: {license_name}")
    return " — ".join(parts)


def render_image_slot(slot: Any, source_root: Path) -> str:
    """Render one already-validated image record as an escaped TeX unit."""
    slug = str(image_field(slot, "slug", ""))
    purpose = str(image_field(slot, "purpose", ""))
    caption = str(image_field(slot, "caption", ""))
    alt = str(image_field(slot, "alt", ""))
    aspect_ratio = str(image_field(slot, "aspect_ratio", ""))
    path = str(image_field(slot, "path", ""))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError(f"image slot has an invalid slug: {slug!r}")
    if aspect_ratio not in {"wide", "landscape", "square", "portrait"}:
        raise ValueError(f"image slot {slug!r} has an invalid aspect ratio: {aspect_ratio!r}")
    state = image_state(slot, source_root)
    # The path alphabet is deliberately narrower than prose escaping: TeX's
    # graphics parser needs a literal filesystem path, and validation has
    # already constrained it to this safe consumer-owned namespace.
    args = (
        slug,
        purpose,
        caption,
        alt.encode("utf-16-be").hex().upper(),
        aspect_ratio,
        path,
        image_source_credit(slot),
        state,
    )
    escaped = [tex_escape(value) for value in args]
    return r"\csname rk@imageslot\endcsname" + "".join("{" + value + "}" for value in escaped)


def replace_image_sentinel(line: str, slots: Mapping[str, Any], source_root: Path) -> tuple[str, str] | None:
    """Return ``(slug, TeX)`` for a standalone image marker, else ``None``."""
    match = IMAGE_SENTINEL_RE.fullmatch(line)
    if match is None:
        return None
    slug = match.group("slug")
    slot = slots.get(slug)
    if slot is None:
        raise ValueError(f"image sentinel references undeclared slot img:{slug}")
    return slug, render_image_slot(slot, source_root)
