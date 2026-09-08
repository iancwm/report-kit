"""Dependency-free parsing and resolution for consumer ``publication.yaml`` files."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import os
import re
from typing import Any

CONFIG_NAME = "publication.yaml"
REQUIRED = ("title",)

PUBLICATION_KEYS = (
    "title", "subtitle", "author", "language", "version", "left_header",
    "footer", "subject", "keywords", "disclaimer", "project_url",
)
DOCUMENT_KEYS = ("main", "class", "engine")
VALIDATION_KEYS = (
    "fail_on_undefined_refs", "fail_on_missing_assets", "overfull_hbox_threshold",
    "underfull_badness_threshold",
)
OUTPUT_KEYS = ("directory",)
ROOT_KEYS = ("publication", "document", "profiles", "validation", "output")
FLAT_KNOWN = PUBLICATION_KEYS

_BOOLS = {"true": True, "false": False}
_INT_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")


def _strip_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in "'\"":
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        elif char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _scalar(value: str, path: Path, line_number: int) -> Any:
    value = _strip_comment(value.strip())
    if not value:
        return None
    if value.startswith(("[", "{")) or value.endswith(("]", "}")):
        raise ValueError(f"{path}:{line_number}: flow-style values are not supported")
    if value[0:1] in ("'", '"'):
        quote = value[0]
        if len(value) < 2 or value[-1] != quote:
            raise ValueError(f"{path}:{line_number}: unterminated quoted value")
        if quote == "'":
            return value[1:-1].replace("''", "'")
        escaped = value[1:-1]
        return re.sub(r"\\([\\\"nrt])", lambda match: {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}[match.group(1)], escaped)
    if value.lower() in _BOOLS:
        return _BOOLS[value.lower()]
    if _INT_RE.fullmatch(value):
        return int(value)
    if value.startswith(("&", "*", "!")):
        raise ValueError(f"{path}:{line_number}: anchors, aliases, and tags are not supported")
    return value


def _parse_subset(path: Path) -> dict[str, Any]:
    lines: list[tuple[int, int, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ValueError(f"{path}:{line_number}: tabs are not allowed for indentation")
        content = _strip_comment(raw.strip())
        if not content:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((line_number, indent, content))

    def block(position: int, indent: int) -> tuple[Any, int]:
        if position >= len(lines) or lines[position][1] != indent:
            raise ValueError(f"{path}:{lines[position][0] if position < len(lines) else 1}: invalid indentation")
        is_list = lines[position][2].startswith("- ") or lines[position][2] == "-"
        result: Any = [] if is_list else {}
        while position < len(lines) and lines[position][1] == indent:
            line_number, _, content = lines[position]
            if is_list:
                if not (content == "-" or content.startswith("- ")):
                    raise ValueError(f"{path}:{line_number}: cannot mix list and mapping entries")
                item = content[1:].strip()
                if not item:
                    if position + 1 < len(lines) and lines[position + 1][1] > indent:
                        child, position = block(position + 1, lines[position + 1][1])
                        result.append(child)
                    else:
                        result.append(None)
                else:
                    if ":" not in item or item.startswith(("'", '"')):
                        result.append(_scalar(item, path, line_number))
                        position += 1
                    else:
                        key, raw_value = item.split(":", 1)
                        key = key.strip()
                        if not key or any(char.isspace() for char in key):
                            raise ValueError(f"{path}:{line_number}: invalid list mapping key {key!r}")
                        mapping: dict[str, Any] = {key: _scalar(raw_value, path, line_number) if raw_value.strip() else None}
                        position += 1
                        if position < len(lines) and lines[position][1] > indent:
                            child, position = block(position, lines[position][1])
                            if not isinstance(child, dict):
                                raise ValueError(f"{path}:{line_number}: list mapping continuation must be a mapping")
                            if mapping[key] is None and key in child:
                                mapping[key] = child.pop(key)
                            overlap = set(mapping) & set(child)
                            if overlap:
                                raise ValueError(f"{path}:{line_number}: duplicate list mapping key {sorted(overlap)[0]!r}")
                            mapping.update(child)
                        result.append(mapping)
                continue
            if content.startswith("- ") or ":" not in content:
                raise ValueError(f"{path}:{line_number}: expected key: value")
            key, raw_value = content.split(":", 1)
            key = key.strip()
            if not key or any(char.isspace() for char in key):
                raise ValueError(f"{path}:{line_number}: invalid key {key!r}")
            if key in result:
                raise ValueError(f"{path}:{line_number}: duplicate key {key!r}")
            if raw_value.strip():
                result[key] = _scalar(raw_value, path, line_number)
                position += 1
            elif position + 1 < len(lines) and lines[position + 1][1] > indent:
                child, position = block(position + 1, lines[position + 1][1])
                result[key] = child
            else:
                result[key] = None
                position += 1
        return result, position

    if not lines:
        return {}
    parsed, position = block(0, lines[0][1])
    if position != len(lines) or not isinstance(parsed, dict):
        line_number = lines[position][0] if position < len(lines) else lines[-1][0]
        raise ValueError(f"{path}:{line_number}: invalid top-level mapping")
    if lines[0][1] != 0:
        raise ValueError(f"{path}:{lines[0][0]}: top-level keys must not be indented")
    return parsed


def _check_keys(values: dict[str, Any], allowed: tuple[str, ...], path: str) -> None:
    for key in values:
        if key not in allowed:
            known = ", ".join(allowed)
            raise ValueError(f"unknown key {path}.{key}; known keys: {known}")


def _validate_schema(values: dict[str, Any], path: Path) -> dict[str, Any]:
    nested = any(key in values for key in ROOT_KEYS)
    if not nested:
        _check_keys(values, FLAT_KNOWN, "publication")
        return values
    _check_keys(values, ROOT_KEYS, "root")
    if "publication" in values:
        if not isinstance(values["publication"], dict):
            raise ValueError(f"{path}: publication must be a mapping")
        _check_keys(values["publication"], PUBLICATION_KEYS, "publication")
    for section, allowed in (("document", DOCUMENT_KEYS), ("validation", VALIDATION_KEYS), ("output", OUTPUT_KEYS)):
        if section in values:
            if not isinstance(values[section], dict):
                raise ValueError(f"{path}: {section} must be a mapping")
            _check_keys(values[section], allowed, section)
    profiles = values.get("profiles", {})
    if profiles is not None:
        if not isinstance(profiles, dict):
            raise ValueError(f"{path}: profiles must be a mapping")
        for name, profile in profiles.items():
            if not isinstance(profile, dict):
                raise ValueError(f"unknown profile {name!r}: expected a mapping")
            if any(key in profile for key in ROOT_KEYS):
                _check_keys(profile, ROOT_KEYS, f"profiles.{name}")
                for section, allowed in (("publication", PUBLICATION_KEYS), ("document", DOCUMENT_KEYS), ("validation", VALIDATION_KEYS), ("output", OUTPUT_KEYS)):
                    if section in profile:
                        if not isinstance(profile[section], dict):
                            raise ValueError(f"profiles.{name}.{section} must be a mapping")
                        _check_keys(profile[section], allowed, f"profiles.{name}.{section}")
            else:
                _check_keys(profile, tuple(ROOT_KEYS) + FLAT_KNOWN + DOCUMENT_KEYS + VALIDATION_KEYS + OUTPUT_KEYS, f"profiles.{name}")
    return values


def load_publication_config(path: Path) -> dict[str, Any]:
    """Load the supported YAML subset; absent config remains an empty mapping."""
    if not path.is_file():
        return {}
    return _validate_schema(_parse_subset(path), path)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "publication"


def resolve_settings(config: dict[str, Any], profile: str | None = None) -> dict[str, dict[str, Any]]:
    """Return normalized publication/document/validation/output sections."""
    if any(key in config for key in ROOT_KEYS):
        settings: dict[str, dict[str, Any]] = {
            section: deepcopy(config.get(section, {}) or {})
            for section in ("publication", "document", "validation", "output")
        }
        settings["profiles"] = deepcopy(config.get("profiles", {}) or {})
    else:
        settings = {"publication": deepcopy(config), "document": {}, "validation": {}, "output": {}, "profiles": {}}
    if profile:
        profiles = settings.get("profiles", {})
        if profile not in profiles:
            raise ValueError(f"unknown publication profile {profile!r}; known profiles: {', '.join(sorted(profiles)) or 'none'}")
        selected = profiles[profile] or {}
        if any(key in selected for key in ROOT_KEYS):
            for section in ("publication", "document", "validation", "output"):
                if isinstance(selected.get(section), dict):
                    settings[section].update(deepcopy(selected[section]))
        else:
            for key, value in selected.items():
                if key in PUBLICATION_KEYS:
                    settings["publication"][key] = deepcopy(value)
                elif key in DOCUMENT_KEYS:
                    settings["document"][key] = deepcopy(value)
                elif key in VALIDATION_KEYS:
                    settings["validation"][key] = deepcopy(value)
                elif key in OUTPUT_KEYS:
                    settings["output"][key] = deepcopy(value)
    return settings


def resolve_identity(config: dict[str, Any], overrides: dict[str, str | None], source_root: Path, profile: str | None = None) -> dict[str, str]:
    settings = resolve_settings(config, profile)
    values = {key: str(value) for key, value in settings["publication"].items() if value is not None}
    for key in PUBLICATION_KEYS:
        env_name = f"REPORTKIT_{key.upper()}"
        if os.environ.get(env_name):
            values[key] = os.environ[env_name]
    for key, value in overrides.items():
        if value:
            values[key] = value
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise ValueError(f"missing publication identity: {', '.join(missing)}. Set it in {source_root / CONFIG_NAME} or pass --{missing[0]}." )
    title = values["title"]
    values.setdefault("subtitle", title)
    values.setdefault("author", "")
    values.setdefault("version", "draft")
    values.setdefault("left_header", f"REPORTKIT / {title.upper()}")
    values.setdefault("footer", title)
    values.setdefault("subject", "")
    values.setdefault("keywords", "")
    values.setdefault("disclaimer", "")
    values.setdefault("project_url", "")
    values["slug"] = slugify(title)
    return values


def resolve_document(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    document = resolve_settings(config, profile)["document"]
    return {"main": document.get("main", "publication-template.tex"), "class": document.get("class", "reportkit"), "engine": document.get("engine") or os.environ.get("REPORTKIT_TEX_ENGINE", "pdflatex")}


KNOWN = FLAT_KNOWN
