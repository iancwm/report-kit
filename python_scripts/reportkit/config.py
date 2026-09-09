"""Dependency-free publication configuration loading and resolution."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

CONFIG_NAME = "publication.yaml"
REQUIRED = ("title",)
IDENTITY_KEYS = (
    "title", "subtitle", "author", "language", "version", "left_header",
    "footer", "subject", "keywords", "disclaimer", "project_url",
)
DOCUMENT_KEYS = ("main", "class", "engine", "theme", "publication_type", "paper")
# Themes that require a specific engine. Selecting the theme without
# configuring that engine must fail validation rather than silently degrade
# the PDF (for example, falling back off Google Sans under pdfTeX). See
# docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md,
# open question 1.
THEME_ENGINE_REQUIREMENTS: dict[str, str] = {
    "institutional-research": "lualatex",
}
VALIDATION_KEYS = (
    "fail_on_undefined_refs", "fail_on_missing_assets",
    "overfull_hbox_threshold", "underfull_badness_threshold",
)
OUTPUT_KEYS = ("directory",)
KNOWN = IDENTITY_KEYS + DOCUMENT_KEYS + VALIDATION_KEYS + OUTPUT_KEYS
SECTIONS = ("publication", "document", "profiles", "validation", "output")


def _strip_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote:
            escaped = True
            continue
        if char in "'\"":
            quote = None if quote == char else (char if quote is None else quote)
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _scalar(raw: str, path: Path, line_number: int) -> Any:
    value = raw.strip()
    if not value:
        return None
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        if len(value) < 2:
            raise ValueError(f"{path}:{line_number}: unterminated quoted value")
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)", value):
        return float(value)
    if value.startswith("[") or value.startswith("{"):
        raise ValueError(f"{path}:{line_number}: flow-style values are not supported")
    return value


def _next_content(lines: list[str], index: int) -> tuple[int, str] | None:
    for next_index in range(index + 1, len(lines)):
        content = _strip_comment(lines[next_index].strip())
        if content:
            indent = len(lines[next_index]) - len(lines[next_index].lstrip(" "))
            return indent, content
    return None


def _parse_yaml(path: Path) -> dict[str, Any]:
    """Parse the deliberately small YAML subset supported by ReportKit."""
    lines = path.read_text(encoding="utf-8").splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    for index, raw in enumerate(lines):
        line_number = index + 1
        leading = raw[: len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in leading:
            raise ValueError(f"{path}:{line_number}: tabs are not supported for indentation")
        content = _strip_comment(raw.strip())
        if not content:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ValueError(f"{path}:{line_number}: indentation must use multiples of two spaces")
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"{path}:{line_number}: list item has no list parent")
            parent.append(_scalar(content[2:], path, line_number))
            continue
        if ":" not in content:
            raise ValueError(f"{path}:{line_number}: expected key: value")
        key, raw_value = content.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"{path}:{line_number}: empty key")
        if not isinstance(parent, dict):
            raise ValueError(f"{path}:{line_number}: mapping entry has no mapping parent")
        if raw_value.strip():
            parent[key] = _scalar(raw_value, path, line_number)
        else:
            next_content = _next_content(lines, index)
            child: dict[str, Any] | list[Any] = [] if next_content and next_content[0] > indent and next_content[1].startswith("- ") else {}
            parent[key] = child
            stack.append((indent, child))
    return root


def _parse_subset(path: Path) -> dict[str, Any]:
    """Parse the same small YAML subset with list-of-mapping support.

    Authoring manifests use lists of structured chapter records, while the
    historical publication config parser above intentionally only handles
    scalar lists. Keep this parser additive so legacy config behaviour stays
    unchanged.
    """
    lines: list[tuple[int, int, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        leading = raw[: len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in leading:
            raise ValueError(f"{path}:{line_number}: tabs are not supported for indentation")
        content = _strip_comment(raw.strip())
        if not content:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ValueError(f"{path}:{line_number}: indentation must use multiples of two spaces")
        lines.append((line_number, indent, content))

    def block(position: int, indent: int) -> tuple[Any, int]:
        if position >= len(lines) or lines[position][1] != indent:
            line_number = lines[position][0] if position < len(lines) else 1
            raise ValueError(f"{path}:{line_number}: invalid indentation")
        is_list = lines[position][2] == "-" or lines[position][2].startswith("- ")
        result: Any = [] if is_list else {}
        while position < len(lines) and lines[position][1] == indent:
            line_number, _, content = lines[position]
            if is_list:
                if content != "-" and not content.startswith("- "):
                    raise ValueError(f"{path}:{line_number}: cannot mix list and mapping entries")
                item = content[1:].strip()
                if not item:
                    if position + 1 < len(lines) and lines[position + 1][1] > indent:
                        child, position = block(position + 1, lines[position + 1][1])
                        result.append(child)
                    else:
                        result.append(None)
                    continue
                if ":" not in item or item.startswith(("'", '"')):
                    result.append(_scalar(item, path, line_number))
                    position += 1
                    continue
                key, raw_value = item.split(":", 1)
                key = key.strip()
                if not key or any(char.isspace() for char in key):
                    raise ValueError(f"{path}:{line_number}: invalid list mapping key {key!r}")
                mapping: dict[str, Any] = {
                    key: _scalar(raw_value, path, line_number) if raw_value.strip() else None
                }
                position += 1
                if position < len(lines) and lines[position][1] > indent:
                    child, position = block(position, lines[position][1])
                    if not isinstance(child, dict):
                        raise ValueError(f"{path}:{line_number}: list mapping continuation must be a mapping")
                    if mapping[key] is None and key in child:
                        mapping[key] = child.pop(key)
                    overlap = set(mapping) & set(child)
                    if overlap:
                        duplicate = sorted(overlap)[0]
                        raise ValueError(f"{path}:{line_number}: duplicate list mapping key {duplicate!r}")
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


def _known_for(section: str) -> tuple[str, ...]:
    return {
        "publication": IDENTITY_KEYS,
        "document": DOCUMENT_KEYS,
        "validation": VALIDATION_KEYS,
        "output": OUTPUT_KEYS,
    }.get(section, KNOWN)


def _validate_mapping(values: dict[str, Any], path: str, allowed: tuple[str, ...], source: Path) -> None:
    for key in values:
        if key not in allowed:
            dotted = f"{path}.{key}" if path else key
            raise ValueError(f"{source}: unknown key {dotted}; known keys: {', '.join(allowed)}")


def _validate_and_normalize(raw: dict[str, Any], source: Path) -> dict[str, Any]:
    if not set(raw) & set(SECTIONS):
        _validate_mapping(raw, "", KNOWN, source)
        return raw
    unknown_top = set(raw) - set(SECTIONS)
    if unknown_top:
        key = sorted(unknown_top)[0]
        raise ValueError(f"{source}: unknown key {key}; known keys: {', '.join(SECTIONS)}")
    for section in ("publication", "document", "validation", "output"):
        value = raw.get(section)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{source}: {section} must be a mapping")
        if isinstance(value, dict):
            _validate_mapping(value, section, _known_for(section), source)
    profiles = raw.get("profiles")
    if profiles is not None and not isinstance(profiles, dict):
        raise ValueError(f"{source}: profiles must be a mapping")
    if isinstance(profiles, dict):
        for profile, values in profiles.items():
            if not isinstance(values, dict):
                raise ValueError(f"{source}: profiles.{profile} must be a mapping")
            for key, value in values.items():
                if key in SECTIONS:
                    if not isinstance(value, dict):
                        raise ValueError(f"{source}: profiles.{profile}.{key} must be a mapping")
                    _validate_mapping(value, f"profiles.{profile}.{key}", _known_for(key), source)
                elif key not in KNOWN:
                    raise ValueError(f"{source}: unknown key profiles.{profile}.{key}; known keys: {', '.join(KNOWN)}")
    return raw


def load_publication_config(path: Path) -> dict[str, Any]:
    """Load a flat legacy or nested publication.yaml file."""
    if not path.is_file():
        return {}
    return _validate_and_normalize(_parse_yaml(path), path)


def slugify(value: str) -> str:
    """Filename-safe slug for the output PDF, derived from the title."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "publication"


def _profile_values(config: dict[str, Any], profile: str | None) -> dict[str, Any]:
    if "publication" not in config:
        return dict(config)
    values = dict(config.get("publication") or {})
    selected = profile or "draft"
    profile_values = (config.get("profiles") or {}).get(selected, {})
    if isinstance(profile_values, dict):
        values.update({key: value for key, value in profile_values.items() if key not in SECTIONS})
        values.update(profile_values.get("publication") or {})
    return values


def resolve_identity(config: dict[str, Any], overrides: dict[str, Any], source_root: Path, profile: str | None = None) -> dict[str, str]:
    """Merge publication config, selected profile, and CLI/environment overrides."""
    values = _profile_values(config, profile)
    for key, value in overrides.items():
        if value not in (None, "") and key in IDENTITY_KEYS:
            values[key] = value
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise ValueError(
            f"missing publication identity: {', '.join(missing)}. "
            f"Set it in {source_root / CONFIG_NAME} or pass --{missing[0]}.")
    title = str(values["title"])
    defaults = {
        "subtitle": title, "author": "", "version": "draft",
        "left_header": f"REPORTKIT / {title.upper()}", "footer": title,
        "subject": "", "keywords": "", "disclaimer": "", "project_url": "",
    }
    for key, default in defaults.items():
        values.setdefault(key, default)
    values["slug"] = slugify(title)
    return {key: str(value) for key, value in values.items()}


def _profile_section(config: dict[str, Any], name: str, profile: str | None) -> dict[str, Any]:
    values = dict(config.get(name) or {}) if "publication" in config else {}
    selected = profile or "draft"
    profile_values = (config.get("profiles") or {}).get(selected, {}) if "publication" in config else {}
    if isinstance(profile_values, dict):
        values.update(profile_values.get(name) or {})
        allowed = {
            "document": DOCUMENT_KEYS,
            "validation": VALIDATION_KEYS,
            "output": OUTPUT_KEYS,
        }.get(name, ())
        values.update({key: value for key, value in profile_values.items() if key in allowed})
    return values


def resolve_document(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    document = _profile_section(config, "document", profile)
    document.setdefault("main", "report.tex")
    document.setdefault("class", "reportkit")
    document.setdefault("engine", "pdflatex")
    document.setdefault("theme", "default")
    document.setdefault("publication_type", "technical-report")
    document.setdefault("paper", "a4")
    return document


def theme_engine_conflict(document: dict[str, Any]) -> str | None:
    """Return an error message if the resolved theme needs an engine the
    resolved configuration doesn't provide, or None if there's no conflict.

    Call this against the fully resolved document (i.e. after any CLI
    ``--engine``/``REPORTKIT_TEX_ENGINE`` override has already been folded
    into ``document["engine"]``) so an explicit override is honoured the
    same way a config-file value would be.
    """
    theme = str(document.get("theme") or "default")
    required = THEME_ENGINE_REQUIREMENTS.get(theme)
    if required is None:
        return None
    engine = str(document.get("engine") or "pdflatex")
    if engine == required:
        return None
    return (
        f"theme {theme!r} requires engine {required!r}, but the resolved engine is "
        f"{engine!r}. Set document.engine: {required} in publication.yaml, or pass "
        f"--engine {required}."
    )


def resolve_validation(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    return _profile_section(config, "validation", profile)


def resolve_output(config: dict[str, Any], source_root: Path, profile: str | None = None) -> Path | None:
    directory = _profile_section(config, "output", profile).get("directory")
    return (source_root / str(directory)).resolve() if directory else None
