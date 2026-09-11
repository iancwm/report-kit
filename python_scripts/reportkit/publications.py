"""Canonical publication, renderer, and theme capability catalog.

The publication catalog is the hand-maintained source of truth for the
renderer matrix. LaTeX receives a generated backstop from this data in the
later registry phase; Python consumers should resolve a :class:`BuildTarget`
instead of reconstructing class, engine, and geometry choices independently.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .diagnostics import make_diagnostic


def _freeze(value: Any) -> Any:
    """Recursively freeze catalog data used by an immutable build target."""
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_thaw(item) for item in value)
    return value


@dataclass(frozen=True)
class BuildTarget:
    """One fully resolved publication build target.

    ``requested_theme`` preserves what the author asked for, while ``theme``
    is the canonical theme implementation. This distinction makes the
    ``technical`` alias observable without duplicating a visual theme.
    Mapping fields are recursively immutable so a resolved target can safely
    be passed between validation, context, and build stages.
    """

    publication_type: str
    requested_theme: str
    theme: str
    alias_of: str | None
    renderer: str
    class_name: str
    template: str
    pandoc_writer: str
    engine: str
    paper: str | None
    canvas: Mapping[str, Any] | None
    geometry: Mapping[str, Any]
    accessibility: Mapping[str, Any]
    common_package: str
    renderer_adapter: str | None
    publication_package: str | None
    brand_overrides: bool
    language_support: Mapping[str, Any]

    @property
    def class_adapter(self) -> str:
        """Compatibility name for the renderer's LaTeX class adapter."""
        return self.class_name

    @property
    def requested_name(self) -> str:
        """Plan terminology for the requested theme/alias name."""
        return self.requested_theme

    @property
    def canonical_theme(self) -> str:
        """Explicit name for the implementation theme."""
        return self.theme

    @property
    def writer(self) -> str:
        """Short compatibility view for callers that use ``writer``."""
        return self.pandoc_writer

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly selection record."""
        return {
            "publication_type": self.publication_type,
            "requested_theme": self.requested_theme,
            "requested_name": self.requested_name,
            "theme": self.theme,
            "alias_of": self.alias_of,
            "renderer": self.renderer,
            "class": self.class_name,
            "template": self.template,
            "writer": self.pandoc_writer,
            "engine": self.engine,
            "paper": self.paper,
            "canvas": _thaw(self.canvas),
            "geometry": _thaw(self.geometry),
            "accessibility": _thaw(self.accessibility),
            "common_package": self.common_package,
            "renderer_adapter": self.renderer_adapter,
            "publication_package": self.publication_package,
            "brand_overrides": self.brand_overrides,
            "language_support": _thaw(self.language_support),
        }


RENDERERS: dict[str, dict[str, Any]] = {
    "paged": {
        "name": "paged",
        "stability": "stable",
        "since": "1.0.0",
        "class_adapter": "reportkit",
        "class_file": "latex_templates/reportkit.cls",
        # This is the legacy template until the target-aware pipeline slice
        # adds paged-base.tex and per-publication entrypoints.
        "template_base": "publication-template.tex",
        "pandoc_writer": "latex",
        "geometry": {"kind": "paper", "papers": ["a4", "letter"]},
        "accessibility": {
            "pdf_metadata": "supported",
            "catalog_language": "supported",
            "bookmarks": "supported",
            "meaningful_links": "supported",
            "diagram_actual_text": "supported",
            "tagged_pdf": "unsupported",
            "tagged_pdf_reason": "The pinned LaTeX format has not yet passed the documented tagging spike.",
        },
    },
}


_LANGUAGE_SUPPORT = {
    "verified": ["en"],
    "metadata_only": ["vi"],
    "scripts": {"verified": ["Latn"], "metadata_only": []},
    "rtl": "unsupported",
}


def _theme(
    name: str,
    *,
    renderers: list[str],
    required_engine: str,
    common_package: str,
    stability: str,
    since: str,
    alias_of: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "alias_of": alias_of,
        "renderers": renderers,
        "required_engine": required_engine,
        "common_package": common_package,
        "renderer_adapters": {renderer: common_package for renderer in renderers},
        "brand_overrides": False,
        "semantic_tokens": [
            "ink", "muted", "hairline", "surface", "primary", "secondary",
            "evidence", "warning", "danger", "data_series", "body", "heading",
            "metadata", "table", "chart", "diagram",
        ],
        "language_support": {
            "verified": list(_LANGUAGE_SUPPORT["verified"]),
            "metadata_only": list(_LANGUAGE_SUPPORT["metadata_only"]),
            "scripts": {
                "verified": list(_LANGUAGE_SUPPORT["scripts"]["verified"]),
                "metadata_only": list(_LANGUAGE_SUPPORT["scripts"]["metadata_only"]),
            },
            "rtl": _LANGUAGE_SUPPORT["rtl"],
        },
        "stability": stability,
        "since": since,
    }


THEMES: dict[str, dict[str, Any]] = {
    "default": _theme(
        "default", renderers=["paged"], required_engine="pdflatex",
        common_package="reportkit-theme-default", stability="stable", since="1.0.0",
    ),
    "technical": _theme(
        "technical", renderers=["paged"], required_engine="pdflatex",
        common_package="reportkit-theme-default", stability="stable", since="1.9.2",
        alias_of="default",
    ),
    "institutional-research": _theme(
        "institutional-research", renderers=["paged"], required_engine="lualatex",
        common_package="reportkit-theme-institutional-research", stability="stable", since="1.7.0",
    ),
}


PUBLICATION_TYPES: dict[str, dict[str, Any]] = {
    "technical-report": {
        "name": "technical-report",
        "renderer": "paged",
        "paper": "a4",
        "themes": ["default", "technical"],
        "default_target": {"theme": "default", "paper": "a4"},
        "template": "publication-template.tex",
        "package": None,
        "selection_criteria": "General technical reports, guides, and long-form analytical documents.",
        "stability": "stable",
        "since": "1.0.0",
    },
    "equity-research": {
        "name": "equity-research",
        "renderer": "paged",
        "paper": "letter",
        "themes": ["institutional-research"],
        "default_target": {"theme": "institutional-research", "paper": "letter"},
        "template": "publication-template.tex",
        "package": "reportkit-equity-research",
        "selection_criteria": "Exhibit-led institutional equity research and investment analysis.",
        "stability": "stable",
        "since": "1.8.0",
    },
}


class PublicationRegistryError(ValueError):
    """Raised when the publication catalog cannot produce a safe target."""

    def __init__(self, message: str, *, diagnostic: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic or make_diagnostic(
            "configuration_error", message, code="RK_PUBLICATION_REGISTRY",
            docs="#/capabilities/publication_types",
        )


def _registry_error(
    message: str, *, candidates: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> PublicationRegistryError:
    return PublicationRegistryError(
        message,
        diagnostic=make_diagnostic(
            "configuration_error", message, code="RK_CONFIG_BUILD_TARGET",
            docs="#/selection", candidates=candidates or (), details=details,
        ),
    )


def _canonical_theme_name(theme: str) -> str:
    seen: set[str] = set()
    current = theme
    while True:
        if current in seen:
            raise _registry_error(f"theme alias cycle detected at {current!r}")
        seen.add(current)
        record = THEMES.get(current)
        if record is None:
            raise _registry_error(
                f"unknown theme {theme!r}; valid themes: {', '.join(sorted(THEMES))}",
                candidates=sorted(THEMES),
            )
        alias = record.get("alias_of")
        if not alias:
            return current
        current = str(alias)


def canonical_theme_name(theme: str) -> str:
    """Return the canonical implementation name for a declared theme alias."""
    return _canonical_theme_name(theme)


def required_engine_for(theme: str) -> str | None:
    """Return the canonical engine requirement for a theme or alias."""
    try:
        canonical = _canonical_theme_name(theme)
    except PublicationRegistryError:
        return None
    record = THEMES[canonical]
    return str(record.get("required_engine")) if record.get("required_engine") else None


def engine_conflict(theme: str, engine: str) -> str | None:
    """Return the stable engine diagnostic text shared by check and build."""
    required = required_engine_for(theme)
    if required is None or engine == required:
        return None
    return (
        f"theme {theme!r} requires engine {required!r}, but the resolved engine is "
        f"{engine!r}. Set document.engine: {required} in publication.yaml, or pass "
        f"--engine {required}."
    )


def _package_path(repo_root: Path, package: str, *, group: str) -> Path:
    if group == "theme":
        return repo_root / "latex_templates" / "themes" / f"{package}.sty"
    if group == "publication":
        return repo_root / "latex_templates" / "publication_types" / f"{package}.sty"
    return repo_root / "latex_templates" / f"{package}.sty"


def check_publication_registry(repo_root: Path | None = None) -> list[str]:
    """Return deterministic catalog-integrity errors without raising."""
    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    errors: list[str] = []

    for name, record in sorted(RENDERERS.items()):
        for field in ("class_adapter", "class_file", "template_base", "pandoc_writer", "geometry", "accessibility"):
            if not record.get(field):
                errors.append(f"renderer {name!r} is missing {field}")
        class_file = root / str(record.get("class_file", ""))
        if not class_file.is_file():
            errors.append(f"renderer {name!r} class file does not exist: {class_file}")
        template = root / "publication_pipeline" / "templates" / str(record.get("template_base", ""))
        if not template.is_file():
            errors.append(f"renderer {name!r} template does not exist: {template}")

    for name, record in sorted(THEMES.items()):
        try:
            canonical = _canonical_theme_name(name)
        except PublicationRegistryError as exc:
            errors.append(str(exc))
            continue
        if not record.get("renderers"):
            errors.append(f"theme {name!r} must support at least one renderer")
        for renderer in record.get("renderers", []):
            if renderer not in RENDERERS:
                errors.append(f"theme {name!r} references missing renderer {renderer!r}")
            adapter = (record.get("renderer_adapters") or {}).get(renderer)
            if not adapter:
                errors.append(f"theme {name!r} is missing its {renderer!r} renderer adapter")
            elif name == canonical and not _package_path(root, str(adapter), group="theme").is_file():
                errors.append(f"theme {name!r} package does not exist: {adapter}")
        if not record.get("common_package"):
            errors.append(f"theme {name!r} is missing common_package")

    for name, record in sorted(PUBLICATION_TYPES.items()):
        renderer = record.get("renderer")
        if renderer not in RENDERERS:
            errors.append(f"publication type {name!r} references missing renderer {renderer!r}")
            continue
        themes = record.get("themes")
        if not themes:
            errors.append(f"publication type {name!r} must declare compatible themes")
            continue
        default_target = record.get("default_target")
        if not isinstance(default_target, dict):
            errors.append(f"publication type {name!r} is missing default_target")
        elif default_target.get("theme") not in themes:
            errors.append(
                f"publication type {name!r} default_target names incompatible theme {default_target.get('theme')!r}"
            )
        for theme in themes:
            if theme not in THEMES:
                errors.append(f"publication type {name!r} references missing theme {theme!r}")
                continue
            if renderer not in THEMES[theme].get("renderers", []):
                errors.append(
                    f"publication type {name!r} uses renderer {renderer!r}, but theme {theme!r} does not support it"
                )
        template = root / "publication_pipeline" / "templates" / str(record.get("template", ""))
        if not template.is_file():
            errors.append(f"publication type {name!r} template does not exist: {template}")
        package = record.get("package")
        if package and not _package_path(root, str(package), group="publication").is_file():
            errors.append(f"publication type {name!r} package does not exist: {package}")

    return errors


def validate_publication_registry(repo_root: Path | None = None) -> None:
    errors = check_publication_registry(repo_root)
    if errors:
        raise _registry_error("publication registry is invalid: " + "; ".join(errors))


def resolve_build_target(
    publication_type: str,
    theme: str,
    explicit_paper: str | None = None,
    engine: str | None = None,
    *,
    repo_root: Path | None = None,
) -> BuildTarget:
    """Resolve one immutable renderer/theme/publication target.

    The catalog is validated before selection so a missing class, template, or
    package cannot degrade into a plausible wrong-theme build.
    """
    validate_publication_registry(repo_root)
    publication = PUBLICATION_TYPES.get(publication_type)
    if publication is None:
        raise _registry_error(
            f"unknown publication type {publication_type!r}; valid publication types: {', '.join(sorted(PUBLICATION_TYPES))}",
            candidates=sorted(PUBLICATION_TYPES),
        )
    if theme not in THEMES:
        raise _registry_error(
            f"unknown theme {theme!r}; valid themes: {', '.join(sorted(THEMES))}",
            candidates=sorted(THEMES),
        )
    if theme not in publication["themes"]:
        compatible = sorted(str(value) for value in publication["themes"])
        raise _registry_error(
            f"theme {theme!r} does not support publication type {publication_type!r}; compatible themes: {', '.join(compatible)}",
            candidates=compatible,
        )

    renderer_name = str(publication["renderer"])
    canonical_theme = _canonical_theme_name(theme)
    theme_record = THEMES[canonical_theme]
    if renderer_name not in theme_record.get("renderers", []):
        raise _registry_error(
            f"theme {theme!r} does not support renderer {renderer_name!r} for publication type {publication_type!r}",
            candidates=sorted(theme_record.get("renderers", [])),
        )
    resolved_engine = str(engine or theme_record["required_engine"])
    conflict = engine_conflict(theme, resolved_engine)
    if conflict:
        raise _registry_error(conflict, details={"theme": theme, "engine": resolved_engine})

    renderer = RENDERERS[renderer_name]
    requested_paper = explicit_paper if explicit_paper is not None else publication.get("paper")
    geometry = dict(renderer["geometry"])
    geometry["paper"] = requested_paper
    canvas = geometry.get("canvas")
    adapter = (theme_record.get("renderer_adapters") or {}).get(renderer_name)
    return BuildTarget(
        publication_type=publication_type,
        requested_theme=theme,
        theme=canonical_theme,
        alias_of=THEMES[theme].get("alias_of"),
        renderer=renderer_name,
        class_name=str(renderer["class_adapter"]),
        template=str(publication["template"]),
        pandoc_writer=str(renderer["pandoc_writer"]),
        engine=resolved_engine,
        paper=None if canvas else (str(requested_paper) if requested_paper is not None else None),
        canvas=_freeze(canvas) if canvas else None,
        geometry=_freeze(geometry),
        accessibility=_freeze(renderer["accessibility"]),
        common_package=str(theme_record["common_package"]),
        renderer_adapter=str(adapter) if adapter else None,
        publication_package=str(publication["package"]) if publication.get("package") else None,
        brand_overrides=bool(theme_record.get("brand_overrides", False)),
        language_support=_freeze(theme_record["language_support"]),
    )


def compatibility_error(publication_type: str, theme: str) -> str | None:
    """Compatibility facade retained for v1 callers."""
    try:
        publication = PUBLICATION_TYPES.get(publication_type)
        if publication is None:
            return f"unknown publication type {publication_type!r}; valid publication types: {', '.join(sorted(PUBLICATION_TYPES))}"
        if theme not in THEMES:
            return f"unknown theme {theme!r}; valid themes: {', '.join(sorted(THEMES))}"
        if theme not in publication["themes"]:
            choices = ", ".join(sorted(str(value) for value in publication["themes"]))
            return f"theme {theme!r} does not support publication type {publication_type!r}; compatible themes: {choices}"
        canonical = _canonical_theme_name(theme)
        if publication["renderer"] not in THEMES[canonical].get("renderers", []):
            return f"theme {theme!r} does not support renderer {publication['renderer']!r}"
    except PublicationRegistryError as exc:
        return str(exc)
    return None


def availability_for(*, publication_type: str | None = None) -> dict[str, list[str]]:
    if publication_type:
        publication = PUBLICATION_TYPES.get(publication_type)
        if publication is None:
            raise ValueError(
                f"unknown publication type {publication_type!r}; valid publication types: {', '.join(sorted(PUBLICATION_TYPES))}"
            )
        return {
            "publication_types": [publication_type],
            "themes": list(publication["themes"]),
            "renderers": [publication["renderer"]],
        }
    return {
        "publication_types": list(PUBLICATION_TYPES),
        "themes": list(THEMES),
        "renderers": list(RENDERERS),
    }
