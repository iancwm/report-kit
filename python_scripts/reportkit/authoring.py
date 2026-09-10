"""Optional source/manuscript and link-registry validation for publications."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from .config import _parse_subset
from .diagnostics import make_diagnostic, suggest

LINK_TYPES = {"citation", "documentation", "repository", "dataset", "further_reading", "interactive_resource"}


@dataclass
class AuthoringResult:
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    chapters: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(item["severity"] == "error" for item in self.diagnostics)

    @property
    def errors(self) -> list[str]:
        """v1.x compatibility view derived from structured diagnostics."""
        return [item["message"] for item in self.diagnostics if item["severity"] == "error"]

    def add(
        self,
        message: str,
        *,
        rule: str,
        file: str | None = None,
        candidates: list[str] | None = None,
    ) -> None:
        self.diagnostics.append(make_diagnostic(
            "publication_validation", message, code=f"RK_AUTHORING_{rule.upper()}",
            source={"file": file} if file else None, candidates=candidates or (), docs="#/commands/check",
        ))


def _read(path: Path) -> Any:
    if not path.is_file():
        return None
    return _parse_subset(path)


def _require_mapping(value: Any, location: str, result: AuthoringResult) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        result.add(f"{location}: expected a mapping", rule="expected_mapping", file=location.split(":", 1)[0])
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
        model_map = _require_mapping(model, model_path.name, result)
        if model_map is not None:
            sources = model_map.get("sources", {})
            source_map = _require_mapping(sources, f"{model_path.name}:sources", result)
            if source_map is not None:
                for source_id, source in source_map.items():
                    location = f"{model_path.name}:sources.{source_id}"
                    source_value = _require_mapping(source, location, result)
                    if source_value is None:
                        continue
                    source_ids.add(source_id)
                    result.sources.append(source_id)
                    for key in ("type", "title", "file"):
                        if not source_value.get(key):
                            result.add(f"{location}: missing {key}", rule="missing_source_field", file=model_path.name)
                    source_links = source_value.get("links", []) or []
                    if not isinstance(source_links, list) or not all(isinstance(item, str) for item in source_links):
                        result.add(f"{location}.links: expected a list of link keys", rule="source_links_type", file=model_path.name)
            chapters = model_map.get("chapters", []) or []
            if not isinstance(chapters, list):
                result.add(f"{model_path.name}:chapters: expected a list", rule="chapters_type", file=model_path.name)
            else:
                for index, chapter in enumerate(chapters, 1):
                    location = f"{model_path.name}:chapters[{index}]"
                    chapter_value = _require_mapping(chapter, location, result)
                    if chapter_value is None:
                        continue
                    chapter_id = chapter_value.get("id")
                    if not chapter_id:
                        result.add(f"{location}: missing id", rule="missing_chapter_id", file=model_path.name)
                    else:
                        result.chapters.append(str(chapter_id))
                    for key in ("title", "purpose"):
                        if not chapter_value.get(key):
                            result.add(f"{location}: missing {key}", rule="missing_chapter_field", file=model_path.name)
                    chapter_sources = chapter_value.get("sources", []) or []
                    if not isinstance(chapter_sources, list):
                        result.add(f"{location}.sources: expected a list", rule="chapter_sources_type", file=model_path.name)
                    else:
                        for source_id in chapter_sources:
                            if source_id not in source_ids:
                                result.add(
                                    f"{location}.sources: unknown source {source_id!r}", rule="unknown_source",
                                    file=model_path.name, candidates=suggest(str(source_id), source_ids),
                                )
    if links is not None:
        link_map = _require_mapping(links, links_path.name, result)
        if link_map is not None:
            values = link_map.get("links", link_map)
            link_map = _require_mapping(values, f"{links_path.name}:links", result)
            if link_map is not None:
                for key, link in link_map.items():
                    location = f"{links_path.name}:links.{key}"
                    link_value = _require_mapping(link, location, result)
                    if link_value is None:
                        continue
                    link_ids.add(key)
                    result.links.append(key)
                    if not link_value.get("url"):
                        result.add(f"{location}: missing url", rule="missing_link_url", file=links_path.name)
                    if not link_value.get("label"):
                        result.add(f"{location}: missing label", rule="missing_link_label", file=links_path.name)
                    if link_value.get("type") not in LINK_TYPES:
                        unknown = str(link_value.get("type"))
                        result.add(
                            f"{location}: type must be one of {', '.join(sorted(LINK_TYPES))}", rule="link_type",
                            file=links_path.name, candidates=suggest(unknown, LINK_TYPES),
                        )
    if model is not None:
        model_map = model if isinstance(model, dict) else {}
        source_map = model_map.get("sources", {}) if isinstance(model_map, dict) else {}
        for source_id, source in source_map.items() if isinstance(source_map, dict) else []:
            for link_id in (source.get("links", []) if isinstance(source, dict) else []):
                if link_id not in link_ids:
                    result.add(
                        f"sources.{source_id}.links: unknown link {link_id!r}", rule="unknown_link",
                        file=model_path.name, candidates=suggest(str(link_id), link_ids),
                    )
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
