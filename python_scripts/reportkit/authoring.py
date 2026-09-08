"""Optional source/manuscript and link-registry validation for publications."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from .config import _parse_subset

LINK_TYPES = {"citation", "documentation", "repository", "dataset", "further_reading", "interactive_resource"}


@dataclass
class AuthoringResult:
    errors: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    chapters: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _read(path: Path) -> Any:
    if not path.is_file():
        return None
    return _parse_subset(path)


def _require_mapping(value: Any, location: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{location}: expected a mapping")
        return None
    return value


def validate_authoring(root: Path, *, model_name: str = "sources.yaml", links_name: str = "links.yaml") -> AuthoringResult:
    result = AuthoringResult()
    model_path = root / model_name
    links_path = root / links_name
    model = _read(model_path)
    links = _read(links_path)
    source_ids: set[str] = set()
    link_ids: set[str] = set()
    if model is not None:
        model_map = _require_mapping(model, model_path.name, result.errors)
        if model_map is not None:
            sources = model_map.get("sources", {})
            source_map = _require_mapping(sources, f"{model_path.name}:sources", result.errors)
            if source_map is not None:
                for source_id, source in source_map.items():
                    location = f"{model_path.name}:sources.{source_id}"
                    source_value = _require_mapping(source, location, result.errors)
                    if source_value is None:
                        continue
                    source_ids.add(source_id)
                    result.sources.append(source_id)
                    for key in ("type", "title", "file"):
                        if not source_value.get(key):
                            result.errors.append(f"{location}: missing {key}")
                    source_links = source_value.get("links", []) or []
                    if not isinstance(source_links, list) or not all(isinstance(item, str) for item in source_links):
                        result.errors.append(f"{location}.links: expected a list of link keys")
            chapters = model_map.get("chapters", []) or []
            if not isinstance(chapters, list):
                result.errors.append(f"{model_path.name}:chapters: expected a list")
            else:
                for index, chapter in enumerate(chapters, 1):
                    location = f"{model_path.name}:chapters[{index}]"
                    chapter_value = _require_mapping(chapter, location, result.errors)
                    if chapter_value is None:
                        continue
                    chapter_id = chapter_value.get("id")
                    if not chapter_id:
                        result.errors.append(f"{location}: missing id")
                    else:
                        result.chapters.append(str(chapter_id))
                    for key in ("title", "purpose"):
                        if not chapter_value.get(key):
                            result.errors.append(f"{location}: missing {key}")
                    chapter_sources = chapter_value.get("sources", []) or []
                    if not isinstance(chapter_sources, list):
                        result.errors.append(f"{location}.sources: expected a list")
                    else:
                        for source_id in chapter_sources:
                            if source_id not in source_ids:
                                result.errors.append(f"{location}.sources: unknown source {source_id!r}")
    if links is not None:
        link_map = _require_mapping(links, links_path.name, result.errors)
        if link_map is not None:
            values = link_map.get("links", link_map)
            link_map = _require_mapping(values, f"{links_path.name}:links", result.errors)
            if link_map is not None:
                for key, link in link_map.items():
                    location = f"{links_path.name}:links.{key}"
                    link_value = _require_mapping(link, location, result.errors)
                    if link_value is None:
                        continue
                    link_ids.add(key)
                    result.links.append(key)
                    if not link_value.get("url"):
                        result.errors.append(f"{location}: missing url")
                    if not link_value.get("label"):
                        result.errors.append(f"{location}: missing label")
                    if link_value.get("type") not in LINK_TYPES:
                        result.errors.append(f"{location}: type must be one of {', '.join(sorted(LINK_TYPES))}")
    if model is not None:
        model_map = model if isinstance(model, dict) else {}
        source_map = model_map.get("sources", {}) if isinstance(model_map, dict) else {}
        for source_id, source in source_map.items() if isinstance(source_map, dict) else []:
            for link_id in (source.get("links", []) if isinstance(source, dict) else []):
                if link_id not in link_ids:
                    result.errors.append(f"sources.{source_id}.links: unknown link {link_id!r}")
    return result


def _tex_escape(value: str) -> str:
    return "".join({"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}"}.get(char, char) for char in value)


def render_links_tex(path: Path, output: Path) -> None:
    """Generate link macros from a consumer link registry."""
    raw = _read(path) or {}
    values = raw.get("links", raw) if isinstance(raw, dict) else {}
    if not isinstance(values, dict):
        raise ValueError(f"{path}: links must be a mapping")
    lines = ["% Generated by ReportKit; do not edit.", r"\providecommand{\RKLink}[1]{\href{#1}{#1}}"]
    for key, value in values.items():
        if not isinstance(value, dict) or not value.get("url") or not value.get("label"):
            raise ValueError(f"{path}: link {key!r} needs url and label")
        if not re.fullmatch(r"[A-Za-z0-9:_-]+", str(key)):
            raise ValueError(f"{path}: invalid link key {key!r}")
        raw_url = str(value["url"])
        parsed = urlparse(raw_url)
        if parsed.scheme not in {"http", "https", "ftp", "mailto"} or any(char in raw_url for char in "\\{}\r\n"):
            raise ValueError(f"{path}: link {key!r} has an unsafe or unsupported URL")
        url = raw_url.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")
        label = _tex_escape(str(value["label"]))
        lines.append(rf"\expandafter\def\csname rk@link@{key}@url\endcsname{{{url}}}")
        lines.append(rf"\expandafter\def\csname rk@link@{key}@label\endcsname{{{label}}}")
    lines.append(r"\renewcommand{\RKLink}[1]{\ifcsname rk@link@#1@url\endcsname\href{\csname rk@link@#1@url\endcsname}{\csname rk@link@#1@label\endcsname}\else\href{#1}{#1}\fi}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
