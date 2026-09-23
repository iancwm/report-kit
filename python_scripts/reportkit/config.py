"""Dependency-free publication configuration loading and resolution."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .publications import PUBLICATION_TYPES, RENDERERS, THEMES, engine_conflict

CONFIG_NAME = "publication.yaml"
REQUIRED = ("title",)
IDENTITY_KEYS = (
    "title", "subtitle", "author", "language", "version", "date", "left_header",
    "footer", "subject", "keywords", "disclaimer", "project_url",
)
DOCUMENT_KEYS = ("main", "class", "engine", "theme", "publication_type", "paper")
LICENSE_KEYS = ("content_license", "content_license_url", "classification")
# Compatibility view retained for callers that imported this constant before
# the publication registry became canonical. Values are derived from the
# registry; there is no second hand-maintained engine table.
THEME_ENGINE_REQUIREMENTS: dict[str, str] = {
    name: str(record["required_engine"])
    for name, record in THEMES.items()
    if record.get("required_engine")
}
# Optional theme-level knobs (spec §3). These are validated and resolved
# here so `reportkit check`/`reportkit context` know about them, but nothing
# yet writes them out as LaTeX macros the way document identity fields are
# written by publication_build.py's write_metadata(): every existing
# latex_templates/examples/*/report.tex sets \setreportkitfontfamily etc.
# directly in the .tex source (the same way it sets \setreportkitleftheader),
# not through the publication_pipeline's markdown pipeline. Wiring
# theme.font_* into that pipeline's generated metadata.tex, if ever needed,
# is unstarted follow-up, not a Step 2 requirement -- see the
# institutional-theme implementation plan.
THEME_KEYS = ("font_family", "font_path", "font_policy")
BRAND_KEYS = ("primary", "secondary", "logo", "display_font")
VALIDATION_KEYS = (
    "fail_on_undefined_refs", "fail_on_missing_assets",
    "overfull_hbox_threshold", "underfull_badness_threshold",
)
OUTPUT_KEYS = ("directory",)
KNOWN = IDENTITY_KEYS + DOCUMENT_KEYS + LICENSE_KEYS + VALIDATION_KEYS + OUTPUT_KEYS + THEME_KEYS
SECTIONS = ("publication", "document", "license", "theme", "brand", "profiles", "validation", "output")


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


def _yaml_tokens(path: Path) -> list[tuple[int, int, str]]:
    """Tokenize the supported YAML subset for both config grammars."""
    tokens: list[tuple[int, int, str]] = []
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
        tokens.append((line_number, indent, content))
    return tokens


def _parse_yaml(path: Path) -> dict[str, Any]:
    """Parse the deliberately small YAML subset supported by ReportKit."""
    lines = _yaml_tokens(path)
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    for index, (line_number, indent, content) in enumerate(lines):
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
            next_content = lines[index + 1] if index + 1 < len(lines) else None
            child: dict[str, Any] | list[Any] = [] if next_content and next_content[1] > indent and next_content[2].startswith("- ") else {}
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
    lines = _yaml_tokens(path)

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
        "license": LICENSE_KEYS,
        "theme": THEME_KEYS,
        "brand": BRAND_KEYS,
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
    if "publication" not in raw and unknown_top:
        # Keep the historical flat identity form composable with new nested
        # sections, so a project can add `license:` without first moving its
        # existing title/author fields under `publication:`.
        _validate_mapping({key: raw[key] for key in unknown_top}, "", KNOWN, source)
        unknown_top = set()
    if unknown_top:
        key = sorted(unknown_top)[0]
        raise ValueError(f"{source}: unknown key {key}; known keys: {', '.join(SECTIONS)}")
    for section in ("publication", "document", "license", "theme", "brand", "validation", "output"):
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
        values = {key: value for key, value in config.items() if key not in SECTIONS}
        selected = profile or "draft"
        profile_values = (config.get("profiles") or {}).get(selected, {})
        if isinstance(profile_values, dict):
            values.update({key: value for key, value in profile_values.items() if key not in SECTIONS})
            values.update(profile_values.get("publication") or {})
        return values
    values = dict(config.get("publication") or {})
    selected = profile or "draft"
    profile_values = (config.get("profiles") or {}).get(selected, {})
    if isinstance(profile_values, dict):
        values.update({key: value for key, value in profile_values.items() if key not in SECTIONS})
        values.update(profile_values.get("publication") or {})
    return values


def resolve_declared_language(config: dict[str, Any], profile: str | None = None) -> str | None:
    """Return the publication's declared ``language`` (profile-aware), if any.

    ``None`` means the publication declares no language and the historical
    en-US catalog default applies without any locale package.
    """
    value = _profile_values(config, profile).get("language")
    return None if value in (None, "") else str(value)


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
        "subtitle": title, "author": "", "version": "draft", "date": "",
        "left_header": f"REPORTKIT / {title.upper()}", "footer": title,
        "subject": "", "keywords": "", "disclaimer": "", "project_url": "",
    }
    for key, default in defaults.items():
        values.setdefault(key, default)
    values["slug"] = slugify(title)
    return {key: str(value) for key, value in values.items()}


def resolve_license(config: dict[str, Any], defaults: dict[str, str], profile: str | None = None) -> dict[str, str]:
    """Merge optional project license metadata over engine defaults."""
    values = {key: str(value) for key, value in defaults.items()}
    overrides = _profile_section(config, "license", profile)
    for key in LICENSE_KEYS:
        value = overrides.get(key)
        if value not in (None, ""):
            values[key] = str(value)
    values.setdefault("classification", "")
    return values


def _profile_section(config: dict[str, Any], name: str, profile: str | None) -> dict[str, Any]:
    values = dict(config.get(name) or {}) if isinstance(config.get(name), dict) else {}
    selected = profile or "draft"
    profile_values = (config.get("profiles") or {}).get(selected, {})
    if isinstance(profile_values, dict):
        values.update(profile_values.get(name) or {})
        allowed = {
            "document": DOCUMENT_KEYS,
            "license": LICENSE_KEYS,
            "theme": THEME_KEYS,
            "brand": BRAND_KEYS,
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
    # decision D5 (multi-format publication architecture spec): a canvas-based
    # renderer (slides) never gets a fake "paper" value -- an omitted paper
    # key must stay omitted so context/build-report honestly report a canvas
    # instead of pretending A4/Letter applies. Only default to "a4" when the
    # resolved publication type actually uses a paper-based renderer (every
    # publication type today, until "presentation" lands); an unrecognized
    # publication_type also defaults to "a4" here so resolve_build_target's
    # own validation -- not this defaulting step -- produces the "unknown
    # publication type" diagnostic.
    publication = PUBLICATION_TYPES.get(str(document["publication_type"]))
    renderer_name = str(publication["renderer"]) if publication else "paged"
    geometry_kind = RENDERERS.get(renderer_name, {}).get("geometry", {}).get("kind", "paper")
    if geometry_kind == "paper":
        # Default to the publication type's own registered paper (Letter for
        # equity-research and executive-brief) so the recorded selection
        # matches the page size the theme adapter actually sets.
        document.setdefault("paper", str((publication or {}).get("paper") or "a4"))
    return document


def theme_engine_conflict(document: dict[str, Any]) -> str | None:
    """Return an error message if the resolved theme needs an engine the
    resolved configuration doesn't provide, or None if there's no conflict.

    Call this against the fully resolved document (i.e. after any CLI
    ``--engine``/``REPORTKIT_TEX_ENGINE`` override has already been folded
    into ``document["engine"]``) so an explicit override is honoured the
    same way a config-file value would be.
    """
    engine = str(document.get("engine") or "pdflatex")
    return engine_conflict(str(document.get("theme") or "default"), engine)


def resolve_theme(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    """Resolve the optional `theme:` section (spec §3): font_family/font_path/
    font_policy. Distinct from `document.theme` (the theme *name*, resolved
    by resolve_document) -- this is that theme's own optional configuration.
    """
    theme = _profile_section(config, "theme", profile)
    theme.setdefault("font_family", "Google Sans")
    theme.setdefault("font_path", "")
    theme.setdefault("font_policy", "fallback")
    return theme


def theme_font_policy_conflict(theme: dict[str, Any]) -> str | None:
    """Return an error message if the resolved theme.font_policy (spec §3)
    isn't one of the two values ReportKit's LaTeX theme files understand
    (strict/fallback), or None if it's fine. Mirrors theme_engine_conflict's
    "validate and fail rather than silently degrade" approach, since an
    unrecognized policy would otherwise reach \\ifdefstring in the .sty file
    and silently take the fallback branch regardless of what was requested.
    """
    configured = theme.get("font_policy")
    policy = configured if configured is not None else "fallback"
    if not isinstance(policy, str) or policy not in ("strict", "fallback"):
        return f"theme.font_policy {policy!r} is not recognized; use 'strict' or 'fallback'."
    return None


def resolve_brand(
    config: dict[str, Any],
    theme: str | None = None,
    source_root: Path | None = None,
    profile: str | None = None,
    *,
    publication_root: Path | None = None,
    registry: dict[str, dict[str, Any]] | None = None,
) -> Any:
    """Resolve and strictly normalize the optional top-level ``brand`` section.

    Brand values are intentionally separate from ``theme:``: the selected
    theme name comes from ``document.theme``, while the registry decides if
    that theme is allowed to consume the four controlled brand keys.  An
    absent or empty section returns an empty immutable ``BrandOverrides``
    record and preserves all legacy behavior.
    """
    if source_root is not None and publication_root is not None and Path(source_root) != Path(publication_root):
        raise ValueError("source_root and publication_root refer to different paths")
    root = publication_root if publication_root is not None else source_root
    values = _profile_section(config, "brand", profile)
    if not values:
        from .theme_overrides import BrandOverrides

        return BrandOverrides()
    selected_theme = theme or str(resolve_document(config, profile).get("theme", "default"))
    theme_config = resolve_theme(config, profile)
    policy_error = theme_font_policy_conflict(theme_config)
    if policy_error:
        raise ValueError(policy_error)
    from .theme_overrides import normalize_brand_overrides

    return normalize_brand_overrides(
        values,
        theme=selected_theme,
        publication_root=root,
        font_policy=theme_config.get("font_policy", "fallback"),
        registry=registry,
    )


def resolve_effective_theme(
    config: dict[str, Any],
    source_root: Path | None = None,
    profile: str | None = None,
    *,
    theme: str | None = None,
    publication_root: Path | None = None,
    registry: dict[str, dict[str, Any]] | None = None,
) -> Any:
    """Resolve config and return the shared immutable effective-theme record."""
    if source_root is not None and publication_root is not None and Path(source_root) != Path(publication_root):
        raise ValueError("source_root and publication_root refer to different paths")
    root = publication_root if publication_root is not None else source_root
    document = resolve_document(config, profile)
    selected_theme = theme or str(document.get("theme", "default"))
    theme_config = resolve_theme(config, profile)
    policy_error = theme_font_policy_conflict(theme_config)
    if policy_error:
        raise ValueError(policy_error)
    from .theme_overrides import build_effective_theme

    brand = resolve_brand(
        config,
        theme=selected_theme,
        source_root=root,
        profile=profile,
        registry=registry,
    )
    return build_effective_theme(
        selected_theme,
        brand,
        publication_root=root,
        font_policy=theme_config.get("font_policy", "fallback"),
        font_family=theme_config.get("font_family"),
        font_path=theme_config.get("font_path", ""),
        font_configured=bool(_profile_section(config, "theme", profile)),
        registry=registry,
    )


# The longer name mirrors the low-level materializer and is convenient for
# callers that want to make the distinction from ``resolve_theme`` explicit.
resolve_brand_overrides = resolve_brand


def resolve_validation(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    return _profile_section(config, "validation", profile)


def resolve_output(config: dict[str, Any], source_root: Path, profile: str | None = None) -> Path | None:
    """Resolve the optional output directory relative to the consumer root."""
    directory = _profile_section(config, "output", profile).get("directory")
    return (source_root / str(directory)).resolve() if directory else None
