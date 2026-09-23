"""Validation and materialization for the constrained brand surface.

The publication builder is deliberately not coupled to this module's file
format.  It can resolve one :class:`EffectiveTheme`, write the TeX rendering
of that record, and pass :func:`materialize_chart_overrides` to the chart
adapter.  Keeping those projections here prevents a brand colour or font from
being normalized differently for TeX and Python charts.

The registry remains the authority for whether a theme may accept a brand
section.  Only a registry record with ``brand_overrides: true`` opts in
(Phase D: ``venture``); every other theme rejects an attempted brand
configuration.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

from .themes import Theme, get_theme, theme_supports_brand_overrides


BRAND_KEYS = ("primary", "secondary", "logo", "display_font")
FONT_POLICIES = ("strict", "fallback")
LOGO_SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg")
_LOGO_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_TEX_COLOR_RE = re.compile(
    r"\\definecolor\{(RKEffective[A-Za-z0-9]+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}"
)


class ThemeOverrideError(ValueError):
    """Raised when a configured brand value cannot be materialized safely."""


def _stable_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    else:
        payload = _stable_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def normalize_hex_color(value: Any, field: str = "color") -> str:
    """Return a canonical uppercase ``#RRGGBB`` color.

    The accepted syntax is intentionally narrower than CSS.  In particular,
    shorthand colors, alpha channels, named colors, and values without the
    leading ``#`` are not accepted because they cannot be represented
    identically by the generated xcolor and Matplotlib projections.
    """
    if not isinstance(value, str) or not _HEX_RE.fullmatch(value):
        raise ThemeOverrideError(f"brand.{field} must be a six-digit hex color in #RRGGBB form")
    return value.upper()


def normalize_font_policy(value: Any = "fallback") -> str:
    """Validate the existing strict/fallback font policy vocabulary."""
    if not isinstance(value, str) or value not in FONT_POLICIES:
        raise ThemeOverrideError(
            f"theme.font_policy {value!r} is not recognized; use 'strict' or 'fallback'."
        )
    return value


def normalize_display_font(value: Any) -> str:
    """Normalize a display-font family while rejecting TeX/path injection."""
    if not isinstance(value, str):
        raise ThemeOverrideError("brand.display_font must be a non-empty font family name")
    normalized = " ".join(value.split())
    if not normalized:
        raise ThemeOverrideError("brand.display_font must be a non-empty font family name")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ThemeOverrideError("brand.display_font must not contain control characters")
    if any(char in normalized for char in "{}\\/\\\n"):
        raise ThemeOverrideError("brand.display_font must be a font family name, not a path or TeX command")
    return normalized


def _resolved_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def normalize_logo_path(value: Any, publication_root: Path | str | None) -> Path:
    """Resolve a logo and require it to be a regular file below the project.

    ``Path.resolve()`` follows symlinks before the containment check, so a
    symlink in ``assets/`` cannot escape the publication root.  Requiring an
    existing file also means the build layer can hash the exact asset rather
    than discovering a missing logo after TeX starts.
    """
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ThemeOverrideError("brand.logo must be a non-empty relative or in-root file path")
    if publication_root is None:
        raise ThemeOverrideError("brand.logo requires a publication root for containment validation")
    root = Path(publication_root).resolve()
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    if not _resolved_inside(resolved, root) or resolved == root:
        raise ThemeOverrideError(
            f"brand.logo {value!r} must resolve inside the publication root {root}"
        )
    if not resolved.is_file():
        raise ThemeOverrideError(f"brand.logo does not name a regular file: {resolved}")
    _require_includable_logo(resolved.relative_to(root).as_posix())
    return resolved


def _require_includable_logo(relative: str) -> None:
    """Reject logos TeX cannot include verbatim from the staged tree.

    The logo reaches TeX as a root-relative path inside ``\\includegraphics``.
    Restricting it to a portable character set and to formats every slide
    engine can place avoids escaping a path (an escaped ``\\_`` is not a
    filename) and avoids discovering an SVG only after TeX starts.
    """
    if not _LOGO_PATH_RE.fullmatch(relative):
        raise ThemeOverrideError(
            f"brand.logo {relative!r} may contain only letters, digits, '.', '-', '_' and '/'"
        )
    if Path(relative).suffix.lower() not in LOGO_SUFFIXES:
        raise ThemeOverrideError(
            f"brand.logo {relative!r} must be one of: {', '.join(LOGO_SUFFIXES)}"
        )


@dataclass(frozen=True)
class BrandOverrides:
    """The four normalized, user-controlled brand values.

    ``logo`` is an absolute, resolved path only after normalization.  It is
    retained as a path for staging and hashing; TeX/chart projections expose a
    root-relative POSIX path instead.
    """

    primary: str | None = None
    secondary: str | None = None
    logo: Path | None = None
    display_font: str | None = None

    @property
    def configured(self) -> bool:
        return any(value is not None for value in (self.primary, self.secondary, self.logo, self.display_font))

    def as_dict(self, *, publication_root: Path | str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "primary": self.primary,
            "secondary": self.secondary,
            "logo": _logo_display_path(self.logo, publication_root) if self.logo else None,
            "display_font": self.display_font,
        }
        return result


def _logo_display_path(logo: Path | None, publication_root: Path | str | None) -> str | None:
    if logo is None:
        return None
    if publication_root is not None:
        root = Path(publication_root).resolve()
        if not _resolved_inside(logo, root):
            raise ThemeOverrideError(f"logo path {logo} is outside publication root {root}")
        return logo.relative_to(root).as_posix()
    return logo.as_posix()


def normalize_brand_overrides(
    values: Mapping[str, Any] | BrandOverrides | None,
    *,
    theme: str | None = None,
    publication_root: Path | str | None = None,
    font_policy: str = "fallback",
    registry: Mapping[str, Mapping[str, Any]] | None = None,
) -> BrandOverrides:
    """Parse and validate the exact four-key brand configuration.

    An absent or empty section is a no-op and deliberately does not require a
    theme capability.  Any actual value requires an explicit selected theme
    and a registry record with ``brand_overrides: true``.
    """
    if values is None:
        return BrandOverrides()
    if isinstance(values, BrandOverrides):
        if not values.configured:
            return values
        raw = {
            key: value
            for key, value in (
                ("primary", values.primary),
                ("secondary", values.secondary),
                ("logo", values.logo),
                ("display_font", values.display_font),
            )
            if value is not None
        }
    elif isinstance(values, Mapping):
        raw = values
    else:
        raise ThemeOverrideError("brand must be a mapping")

    unknown = sorted(set(raw) - set(BRAND_KEYS))
    if unknown:
        raise ThemeOverrideError(
            f"brand contains unknown key {unknown[0]!r}; known keys: {', '.join(BRAND_KEYS)}"
        )
    if not raw:
        return BrandOverrides()
    if theme is None or not str(theme):
        raise ThemeOverrideError("brand overrides require a selected theme")
    if not theme_supports_brand_overrides(str(theme), registry=registry):
        raise ThemeOverrideError(
            f"theme {theme!r} does not permit brand overrides; the registry capability "
            "'brand_overrides' is false"
        )
    policy = normalize_font_policy(font_policy)
    # Keep the local variable meaningful in the contract: policy is validated
    # here, while actual strict font availability is checked by the chart and
    # TeX consumers that have access to their respective font resolvers.
    del policy

    normalized_primary = (
        normalize_hex_color(raw["primary"], "primary") if "primary" in raw else None
    )
    normalized_secondary = (
        normalize_hex_color(raw["secondary"], "secondary") if "secondary" in raw else None
    )
    if "logo" in raw:
        if isinstance(raw["logo"], Path):
            normalized_logo = raw["logo"].resolve()
            root = Path(publication_root).resolve() if publication_root is not None else None
            if root is not None and (not _resolved_inside(normalized_logo, root) or normalized_logo == root):
                raise ThemeOverrideError(f"logo path {normalized_logo} is outside publication root {root}")
            if not normalized_logo.is_file():
                raise ThemeOverrideError(f"brand.logo does not name a regular file: {normalized_logo}")
            _require_includable_logo(
                normalized_logo.relative_to(root).as_posix() if root is not None else normalized_logo.name
            )
        else:
            normalized_logo = normalize_logo_path(raw["logo"], publication_root)
    else:
        normalized_logo = None
    normalized_font = (
        normalize_display_font(raw["display_font"]) if "display_font" in raw else None
    )
    return BrandOverrides(
        primary=normalized_primary,
        secondary=normalized_secondary,
        logo=normalized_logo,
        display_font=normalized_font,
    )


def _base_secondary(theme: Theme) -> str:
    return theme.latex_colors.get("Research", theme.data_colors[1] if len(theme.data_colors) > 1 else theme.data_colors[0])


def _effective_palette(theme: Theme, brand: BrandOverrides) -> tuple[dict[str, str], tuple[str, ...]]:
    colors = {str(key): str(value).upper() for key, value in theme.latex_colors.items()}
    primary = brand.primary or colors.get("LinkBlue", theme.data_colors[0])
    secondary = brand.secondary or _base_secondary(theme)

    # These are the shared semantic roles represented by the constrained
    # primary/secondary controls. Only replace names present in a base theme;
    # future themes can add a role without changing this projection.
    # ``Accent`` and ``MetricAccent`` are primary roles: every slide theme
    # sets them equal to LinkBlue, and the presentation compositions draw
    # kickers, hero metrics and card rails from ``Accent``.
    if brand.primary:
        for key in ("LinkBlue", "Principle", "Accent", "MetricAccent"):
            if key in colors:
                colors[key] = primary
    if brand.secondary:
        for key in ("Research", "SeriesBlue"):
            if key in colors:
                colors[key] = secondary

    data_colors = list(theme.data_colors)
    if data_colors and brand.primary:
        data_colors[0] = primary
    if len(data_colors) > 1 and brand.secondary:
        data_colors[1] = secondary
    return colors, tuple(data_colors)


@dataclass(frozen=True)
class EffectiveTheme:
    """One immutable theme projection shared by TeX and chart consumers."""

    base_theme: Theme
    brand: BrandOverrides
    latex_colors: Mapping[str, str]
    data_colors: tuple[str, ...]
    display_font: str
    font_policy: str
    font_path: str
    font_configured: bool
    publication_root: Path | None
    palette_hash: str
    font_hash: str
    logo_hash: str | None

    @property
    def theme(self) -> str:
        return self.base_theme.name

    @property
    def configured(self) -> bool:
        return self.brand.configured or self.font_configured

    @property
    def primary(self) -> str:
        return self.latex_colors.get("LinkBlue", self.data_colors[0])

    @property
    def secondary(self) -> str:
        return self.latex_colors.get("Research", self.data_colors[1] if len(self.data_colors) > 1 else self.primary)

    def as_dict(self) -> dict[str, Any]:
        root = self.publication_root
        return {
            "theme": self.theme,
            "brand": self.brand.as_dict(publication_root=root),
            "palette": dict(sorted(self.latex_colors.items())),
            "chart": {
                "primary": self.primary,
                "secondary": self.secondary,
                "data_colors": list(self.data_colors),
            },
            "font": {
                "display_font": self.display_font,
                "policy": self.font_policy,
                "path": self.font_path,
                "configured": self.font_configured,
            },
            "logo": _logo_display_path(self.brand.logo, root) if self.brand.logo else None,
            "hashes": {
                "palette": self.palette_hash,
                "font": self.font_hash,
                "logo": self.logo_hash,
            },
        }


def build_effective_theme(
    theme: str | Theme = "default",
    brand: Mapping[str, Any] | BrandOverrides | None = None,
    *,
    publication_root: Path | str | None = None,
    font_policy: str = "fallback",
    font_family: str | None = None,
    font_path: str = "",
    font_configured: bool | None = None,
    registry: Mapping[str, Mapping[str, Any]] | None = None,
) -> EffectiveTheme:
    """Build the shared immutable record from a base theme and brand values."""
    base = get_theme(theme) if isinstance(theme, str) else theme
    selected_name = base.name if isinstance(theme, Theme) else theme
    normalized_brand = normalize_brand_overrides(
        brand,
        theme=selected_name,
        publication_root=publication_root,
        font_policy=font_policy,
        registry=registry,
    )
    policy = normalize_font_policy(font_policy)
    if font_path is not None and not isinstance(font_path, str):
        raise ThemeOverrideError("theme.font_path must be a string")
    normalized_font_path = str(font_path or "")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized_font_path):
        raise ThemeOverrideError("theme.font_path must not contain control characters")
    display_font = normalized_brand.display_font or font_family or base.typography.display
    display_font = normalize_display_font(display_font)
    materialize_fonts = (
        bool(font_family is not None or normalized_font_path)
        if font_configured is None
        else bool(font_configured)
    )
    colors, data_colors = _effective_palette(base, normalized_brand)
    frozen_colors = MappingProxyType(dict(sorted(colors.items())))
    root = Path(publication_root).resolve() if publication_root is not None else None
    logo_hash = hashlib.sha256(normalized_brand.logo.read_bytes()).hexdigest() if normalized_brand.logo else None
    return EffectiveTheme(
        base_theme=base,
        brand=normalized_brand,
        latex_colors=frozen_colors,
        data_colors=data_colors,
        display_font=display_font,
        font_policy=policy,
        font_path=normalized_font_path,
        font_configured=materialize_fonts,
        publication_root=root,
        palette_hash=_sha256(dict(sorted(frozen_colors.items()))),
        font_hash=_sha256({"display_font": display_font, "font_policy": policy, "font_path": normalized_font_path}),
        logo_hash=logo_hash,
    )


def resolve_effective_theme(
    config: Mapping[str, Any],
    *,
    theme: str | None = None,
    publication_root: Path | str | None = None,
    profile: str | None = None,
    registry: Mapping[str, Mapping[str, Any]] | None = None,
) -> EffectiveTheme:
    """Resolve config sections and produce one effective theme record.

    This convenience entry point mirrors the config module's existing
    ``resolve_document``/``resolve_theme`` functions without making the low-
    level materializer depend on the config parser.
    """
    from .config import _profile_section, resolve_brand, resolve_document, resolve_theme as resolve_theme_config

    document = resolve_document(dict(config), profile)
    selected_theme = theme or str(document.get("theme", "default"))
    theme_config = resolve_theme_config(dict(config), profile)
    brand = resolve_brand(
        dict(config),
        theme=selected_theme,
        source_root=Path(publication_root) if publication_root is not None else None,
        profile=profile,
        registry=registry,
    )
    return build_effective_theme(
        selected_theme,
        brand,
        publication_root=publication_root,
        font_policy=theme_config.get("font_policy", "fallback"),
        font_family=theme_config.get("font_family"),
        font_path=theme_config.get("font_path", ""),
        font_configured=bool(_profile_section(dict(config), "theme", profile)),
        registry=registry,
    )


def _tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def render_tex_overrides(effective: EffectiveTheme) -> str:
    """Render a deterministic ``reportkit-theme-overrides.tex`` payload."""
    if not effective.configured:
        return "% ReportKit theme overrides: none.\n"

    lines = [
        "% Generated by reportkit.theme_overrides; do not edit.",
        "% The palette, font, logo and hashes come from one EffectiveTheme record.",
        f"% ReportKit theme: {effective.theme}",
        f"% Palette SHA-256: {effective.palette_hash}",
        f"% Font SHA-256: {effective.font_hash}",
        f"% Logo SHA-256: {effective.logo_hash or 'none'}",
    ]
    for name, color in sorted(effective.latex_colors.items()):
        lines.append(f"\\definecolor{{RKEffective{name}}}{{HTML}}{{{color[1:]}}}")
    for name in sorted(effective.latex_colors):
        lines.append(f"\\colorlet{{{name}}}{{RKEffective{name}}}")
    lines.extend([
        r"\newcommand{\RKBrandPrimaryColor}{RKEffectiveLinkBlue}",
        r"\newcommand{\RKBrandSecondaryColor}{RKEffectiveResearch}",
        rf"\newcommand{{\RKBrandDisplayFont}}{{{_tex_escape(effective.display_font)}}}",
        rf"\newcommand{{\RKBrandFontPolicy}}{{{_tex_escape(effective.font_policy)}}}",
    ])
    if effective.brand.display_font or effective.font_configured:
        # Existing theme packages may expose these setters; the guard keeps
        # this file harmless for themes whose typography is not configurable.
        lines.extend([
            r"\ifcsname setreportkitfontfamily\endcsname",
            r"  \setreportkitfontfamily{\RKBrandDisplayFont}",
            r"\fi",
            rf"\ifcsname setreportkitfontpath\endcsname\setreportkitfontpath{{{_tex_escape(effective.font_path)}}}\fi",
            rf"\ifcsname setreportkitfontpolicy\endcsname\setreportkitfontpolicy{{{_tex_escape(effective.font_policy)}}}\fi",
        ])
    if effective.brand.logo:
        logo = _logo_display_path(effective.brand.logo, effective.publication_root)
        assert logo is not None
        # Normalization restricted the path to [A-Za-z0-9._/-], so it is
        # emitted verbatim: an escaped ``\_`` would not name the staged file.
        _require_includable_logo(logo)
        lines.extend([
            rf"\newcommand{{\RKBrandLogo}}{{{logo}}}",
            r"\newif\ifRKBrandHasLogo",
            r"\RKBrandHasLogotrue",
        ])
    else:
        lines.extend([
            r"\newcommand{\RKBrandLogo}{}",
            r"\newif\ifRKBrandHasLogo",
            r"\RKBrandHasLogofalse",
        ])
    return "\n".join(lines) + "\n"


def materialize_tex_overrides(
    effective: EffectiveTheme,
    path: Path | str | None = None,
) -> str | Path:
    """Render and optionally write the deterministic TeX override file.

    With no ``path`` the content is returned for callers that stage files
    themselves.  With a path, the parent directory is created and the path is
    returned after writing UTF-8 content.
    """
    content = render_tex_overrides(effective)
    if path is None:
        return content
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def materialize_chart_overrides(effective: EffectiveTheme) -> dict[str, Any]:
    """Return the deterministic chart projection of an effective theme."""
    return {
        "theme": effective.theme,
        "primary": effective.primary,
        "secondary": effective.secondary,
        "data_colors": list(effective.data_colors),
        "latex_colors": dict(sorted(effective.latex_colors.items())),
        "display_font": effective.display_font,
        "font_policy": effective.font_policy,
        "logo": _logo_display_path(effective.brand.logo, effective.publication_root)
        if effective.brand.logo
        else None,
        "hashes": {
            "palette": effective.palette_hash,
            "font": effective.font_hash,
            "logo": effective.logo_hash,
        },
    }


def chart_overrides(effective: EffectiveTheme) -> dict[str, Any]:
    """Compatibility alias for the chart projection API."""
    return materialize_chart_overrides(effective)


def validate_tex_overrides(content_or_path: str | Path, effective: EffectiveTheme) -> list[str]:
    """Compare generated TeX effective colors with the shared Python record."""
    content = (
        Path(content_or_path).read_text(encoding="utf-8")
        if isinstance(content_or_path, Path)
        else content_or_path
    )
    found = {name.removeprefix("RKEffective"): f"#{value.upper()}" for name, value in _TEX_COLOR_RE.findall(content)}
    errors: list[str] = []
    if not effective.configured:
        return errors if content == "% ReportKit theme overrides: none.\n" else ["unconfigured theme must materialize as a no-op"]
    for name, expected in sorted(effective.latex_colors.items()):
        actual = found.get(name)
        if actual is None:
            errors.append(f"missing generated TeX color: {name}")
        elif actual.upper() != expected.upper():
            errors.append(f"{name}: generated TeX {actual} != Python {expected}")
    return errors


def apply_chart_overrides(effective: EffectiveTheme) -> None:
    """Apply one effective theme to the process-global chart adapter.

    Matplotlib is imported lazily so config validation and pure-Python build
    planning do not acquire a plotting dependency.
    """
    from matplotlib import font_manager
    import matplotlib as mpl

    from .viz import core

    colors = effective.latex_colors
    core.INK = colors.get("Ink", core.INK)
    core.MUTED = colors.get("Muted", core.MUTED)
    core.HAIRLINE = colors.get("Hairline", core.HAIRLINE)
    core.PRIMARY = colors.get("LinkBlue", core.PRIMARY)
    core.DECISION = colors.get("Decision", core.DECISION)
    core.RESEARCH = colors.get("Research", core.RESEARCH)
    core.TIP = colors.get("Tip", core.TIP)
    core.RED_FLAG = colors.get("RedFlag", core.RED_FLAG)
    core.ASSUMPTION = colors.get("Assumption", core.ASSUMPTION)
    core.EVIDENCE = colors.get("Evidence", core.EVIDENCE)
    core.LIMITATION = colors.get("Limitation", core.LIMITATION)
    core.METRIC = colors.get("MetricAccent", core.METRIC)
    core.DELIVERABLE = colors.get("Deliverable", core.DELIVERABLE)
    core.DATA_COLORS = effective.data_colors
    core.LATEX_THEME_COLORS = dict(colors)

    if effective.brand.display_font or effective.font_configured:
        try:
            font_manager.findfont(effective.display_font, fallback_to_default=False)
            chart_font = effective.display_font
        except ValueError:
            if effective.font_policy == "strict":
                raise ThemeOverrideError(
                    f"brand.display_font {effective.display_font!r} is unavailable under strict font policy"
                )
            chart_font = "DejaVu Sans"
            for candidate in (*effective.base_theme.sans_candidates, "DejaVu Sans"):
                try:
                    font_manager.findfont(candidate, fallback_to_default=False)
                    chart_font = candidate
                    break
                except ValueError:
                    continue
        core.SANS_FONT = chart_font
        mpl.rcParams["font.sans-serif"] = [chart_font, "DejaVu Sans"]
        if effective.base_theme.mathtext_fontset == "custom":
            mpl.rcParams.update({"mathtext.rm": chart_font, "mathtext.it": chart_font, "mathtext.bf": chart_font})
    mpl.rcParams.update({
        "text.color": core.INK,
        "axes.labelcolor": core.INK,
        "xtick.color": core.MUTED,
        "ytick.color": core.MUTED,
    })


# Concise names are useful to build-layer callers and keep the public API
# discoverable without requiring them to know the implementation verb.
normalize_brand = normalize_brand_overrides
effective_theme = build_effective_theme
render_tex = render_tex_overrides
render_chart = materialize_chart_overrides
validate_generated_tex_colors = validate_tex_overrides


__all__ = [
    "BRAND_KEYS", "FONT_POLICIES", "LOGO_SUFFIXES", "BrandOverrides", "EffectiveTheme", "ThemeOverrideError",
    "apply_chart_overrides", "build_effective_theme", "chart_overrides", "effective_theme",
    "materialize_chart_overrides", "materialize_tex_overrides", "normalize_brand",
    "normalize_brand_overrides", "normalize_display_font", "normalize_font_policy",
    "normalize_hex_color", "normalize_logo_path", "render_chart", "render_tex",
    "render_tex_overrides", "resolve_effective_theme", "validate_generated_tex_colors",
    "validate_tex_overrides",
]
