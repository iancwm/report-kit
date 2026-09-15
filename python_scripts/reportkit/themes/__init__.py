"""Per-theme Python tokens for ReportKit's visualization layer.

Resolves open question 8 from the institutional-research theme + equity-
research profile spec
(docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md):
theme modules live inside the `reportkit` package, matching that spec's
target tree (§2). The chart implementation imports these tokens without
making the theme package depend on matplotlib (font *resolution* -- turning a
list of candidate names into the one that's actually available -- stays in
`reportkit.viz`, which owns `matplotlib.font_manager`; this package supplies
the candidate lists).

Each theme submodule (`default`, `institutional_research`) builds and
exports a module-level `THEME: Theme` constant. `reportkit_viz.apply_theme
(name)` resolves a name to its module via `get_theme()` and applies every
field to both `matplotlib.rcParams` and the chart implementation's module-level
color/geometry constants (`INK`, `MUTED`, `FIGURE_SIZES`, ...), which the
rest of that module's ~20 chart functions already read as plain globals --
see `reportkit.viz`'s `apply_theme()` docstring for why that's the
integration point rather than threading a `Theme` argument through every
chart function.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import importlib


@dataclass(frozen=True)
class TypographyTokens:
    """Semantic font roles shared by document and chart renderers."""

    display: str
    heading: str
    body: str
    metadata: str
    table: str
    chart: str
    mono: str
    math: str


@dataclass(frozen=True)
class GeometryTokens:
    """Theme geometry in explicit, renderer-neutral units."""

    paper: str | None
    canvas_mm: tuple[float, float] | None
    text_width_in: float
    # (top, right, bottom, left), in millimetres.
    margins_mm: tuple[float, float, float, float]
    column_gutter_in: float


@dataclass(frozen=True)
class SpacingTokens:
    """Theme spacing values in points."""

    paragraph: float
    heading: float
    component: float


@dataclass(frozen=True)
class RuleTokens:
    """Theme rule weights in points."""

    thin: float
    medium: float


@dataclass(frozen=True)
class TableTokens:
    """Theme table treatment in points plus a semantic header policy."""

    body_size: float
    header_treatment: str
    row_spacing: float


@dataclass(frozen=True)
class ChartTokens:
    """Theme chart defaults consumed by the Matplotlib adapter."""

    base_font: float
    tick_size: float
    label_size: float
    line_width: float
    grid_style: str
    legend_style: str


@dataclass(frozen=True)
class DiagramTokens:
    """Theme diagram-chrome defaults shared with the LaTeX token layer."""

    node_font: float
    node_padding: tuple[float, float]
    node_radius: float
    edge_weight: float
    label_font: float


@dataclass(frozen=True)
class ScriptCoverageTokens:
    """Declared text-script coverage for diagnostics and build contracts."""

    verified: tuple[str, ...]
    metadata_only: tuple[str, ...]
    rtl: str


@dataclass(frozen=True)
class Theme:
    """Everything `reportkit.viz` needs to render one ReportKit theme.

    `latex_colors` mirrors the chart implementation's historical `LATEX_THEME_COLORS`
    dict exactly -- the same 14 keys, checked against the matching LaTeX
    theme file's `\\definecolor` block by `reportkit_viz.py check-theme` /
    `validate_palette_against_latex()`. The remaining color fields
    (`surface`, `white`, `data_colors`, ...) are analytical/chart-only
    colors with no LaTeX counterpart to sync against.
    """

    name: str
    latex_colors: dict[str, str]
    surface: str
    white: str
    data_colors: tuple[str, ...]
    benchmark: str
    data_warm: str
    data_positive: str
    data_negative: str
    # Derived from the theme's LaTeX geometry (paper size minus margins),
    # per spec §15 -- not an embedded constant unrelated to the page the
    # figure will actually sit on. See each theme module for the derivation.
    text_width_in: float
    # Ratio-derived per named size where the theme is new enough not to owe
    # any publication byte-identical output (spec's open question 4);
    # default.py keeps its literal pre-Step-4 numbers instead, for the
    # backward-compatibility guarantee spec §26 makes for the *document*
    # theme and this project extends to the chart theme by the same logic.
    figure_sizes: dict[str, tuple[float, float]]
    sans_candidates: tuple[str, ...]
    serif_candidates: tuple[str, ...]
    mono_candidates: tuple[str, ...]
    base_font_size: float
    # "stix" (matplotlib's default math font, serif) or "custom". Only
    # "custom" additionally needs reportkit.viz's apply_theme() to point
    # mathtext.rm/it/bf at the theme's own resolved sans font -- see spec
    # §14 and that function's implementation.
    mathtext_fontset: str
    # Explicit semantic records. The scalar and mapping fields above remain
    # compatibility views for existing chart callers.
    typography: TypographyTokens
    geometry: GeometryTokens
    spacing: SpacingTokens
    rules: RuleTokens
    tables: TableTokens
    charts: ChartTokens
    diagrams: DiagramTokens
    script_coverage: ScriptCoverageTokens


_MODULES = {
    "default": "reportkit.themes.default",
    # `technical` is a declared publication alias, not a second visual
    # implementation. Returning the same module preserves one Python Theme
    # object and one chart baseline for both names.
    "technical": "reportkit.themes.default",
    "institutional-research": "reportkit.themes.institutional_research",
    "executive": "reportkit.themes.executive",
}


def get_theme(name: str) -> Theme:
    """Resolve a theme name -- the same one `publication.yaml`'s
    `document.theme` / `\\documentclass[theme=...]` uses -- to its Python
    token set. Raises ValueError for a theme with no registered Python
    module, naming what's actually available, rather than silently
    substituting the wrong theme's tokens (the same "honest failure, not a
    false pass" principle open question 2 established for `check-theme`)."""
    module_name = _MODULES.get(name)
    if module_name is None:
        raise ValueError(
            f"no reportkit.themes module for theme {name!r}; known themes: {', '.join(available_themes())}"
        )
    module = importlib.import_module(module_name)
    return module.THEME


def available_themes() -> tuple[str, ...]:
    return tuple(sorted(_MODULES))


def validate_theme_contract(theme: Theme) -> list[str]:
    """Return contract violations for one resolved Python theme.

    This is deliberately independent of Matplotlib so registry and static
    contract tests can validate every theme in a minimal environment. The
    LaTeX package checks live in reportkit.viz.core because they require
    repository paths; both layers are reported by the single check-theme
    command.
    """
    errors: list[str] = []
    records = {
        "typography": theme.typography,
        "geometry": theme.geometry,
        "spacing": theme.spacing,
        "rules": theme.rules,
        "tables": theme.tables,
        "charts": theme.charts,
        "diagrams": theme.diagrams,
        "script_coverage": theme.script_coverage,
    }
    for record_name, record in records.items():
        for field in fields(record):
            value = getattr(record, field.name)
            if isinstance(value, str) and not value.strip():
                errors.append(f"{record_name}.{field.name} must not be empty")
            elif isinstance(value, (int, float)) and value <= 0:
                errors.append(f"{record_name}.{field.name} must be positive")

    if not theme.name.strip():
        errors.append("name must not be empty")
    if not theme.latex_colors:
        errors.append("latex_colors must not be empty")
    if not theme.data_colors:
        errors.append("data_colors must not be empty")
    if not theme.sans_candidates:
        errors.append("sans_candidates must not be empty")
    if not theme.mono_candidates:
        errors.append("mono_candidates must not be empty")
    if theme.geometry.text_width_in != theme.text_width_in:
        errors.append("geometry.text_width_in must match compatibility text_width_in")
    if theme.charts.base_font != theme.base_font_size:
        errors.append("charts.base_font must match compatibility base_font_size")
    if theme.geometry.canvas_mm is None and theme.geometry.paper is None:
        errors.append("geometry must declare paper or canvas_mm")
    if len(theme.geometry.margins_mm) != 4:
        errors.append("geometry.margins_mm must contain top/right/bottom/left")
    if not theme.script_coverage.verified:
        errors.append("script_coverage.verified must not be empty")
    if theme.script_coverage.rtl not in {"supported", "unsupported", "partial"}:
        errors.append("script_coverage.rtl must be supported, unsupported, or partial")
    return errors
