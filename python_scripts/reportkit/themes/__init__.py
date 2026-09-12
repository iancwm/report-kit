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

from dataclasses import dataclass
import importlib


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


_MODULES = {
    "default": "reportkit.themes.default",
    # `technical` is a declared publication alias, not a second visual
    # implementation. Returning the same module preserves one Python Theme
    # object and one chart baseline for both names.
    "technical": "reportkit.themes.default",
    "institutional-research": "reportkit.themes.institutional_research",
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
