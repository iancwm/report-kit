"""Theme resolution and process-wide Matplotlib token application."""
from __future__ import annotations

from typing import Any, Sequence

import matplotlib as mpl
from matplotlib import font_manager

from reportkit.themes import get_theme


def _available_font(candidates: Sequence[str], fallback: str = "DejaVu Sans") -> str:
    """Return the first installed font name without requiring local font files."""
    for candidate in candidates:
        try:
            font_manager.findfont(candidate, fallback_to_default=False)
            return candidate
        except ValueError:
            pass
    return fallback


def apply_theme(theme: str = "default") -> None:
    """Apply a ReportKit Matplotlib theme globally, by name.

    Theme tokens are copied into the canonical chart implementation's module
    namespace because its chart functions intentionally resolve those values
    at call time. This preserves the documented theme-switching behaviour
    while keeping theme resolution separate from figure and chart concerns.
    Theme state is process-global and therefore not thread-safe: do not switch
    themes concurrently in a process that is rendering figures.
    """
    from . import core

    resolved = get_theme(theme)
    core.INK = resolved.latex_colors["Ink"]
    core.MUTED = resolved.latex_colors["Muted"]
    core.HAIRLINE = resolved.latex_colors["Hairline"]
    core.PRIMARY = resolved.latex_colors["LinkBlue"]
    core.DECISION = resolved.latex_colors["Decision"]
    core.RESEARCH = resolved.latex_colors["Research"]
    core.TIP = resolved.latex_colors["Tip"]
    core.RED_FLAG = resolved.latex_colors["RedFlag"]
    core.ASSUMPTION = resolved.latex_colors["Assumption"]
    core.EVIDENCE = resolved.latex_colors["Evidence"]
    core.LIMITATION = resolved.latex_colors["Limitation"]
    core.METRIC = resolved.latex_colors["MetricAccent"]
    core.DELIVERABLE = resolved.latex_colors["Deliverable"]
    core.SURFACE = resolved.surface
    core.WHITE = resolved.white

    # Analytical colors use the same visual family but are not semantic
    # callout labels. Cool categorical colors avoid accidental good/bad
    # encoding -- see each theme module for its own data_colors rationale.
    core.DATA_COLORS = resolved.data_colors
    core.BENCHMARK = resolved.benchmark
    core.DATA_WARM = resolved.data_warm
    core.DATA_POSITIVE = resolved.data_positive
    core.DATA_NEGATIVE = resolved.data_negative

    # Copy mutable containers so callers cannot mutate the Theme object.
    core.LATEX_THEME_COLORS = dict(resolved.latex_colors)
    core.TEXT_WIDTH_IN = resolved.text_width_in
    core.FIGURE_SIZES = dict(resolved.figure_sizes)

    sans_font = _available_font(resolved.sans_candidates)
    serif_font = _available_font(resolved.serif_candidates)
    mono_font = _available_font(resolved.mono_candidates)
    core.SANS_FONT, core.SERIF_FONT, core.MONO_FONT = sans_font, serif_font, mono_font

    base = resolved.base_font_size
    rcparams: dict[str, Any] = {
        "figure.facecolor": core.WHITE,
        "figure.edgecolor": core.WHITE,
        "figure.dpi": 130,
        "savefig.facecolor": core.WHITE,
        "savefig.edgecolor": core.WHITE,
        "savefig.dpi": 320,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "font.family": "sans-serif",
        "font.sans-serif": [sans_font, "DejaVu Sans"],
        "font.serif": [serif_font, "DejaVu Serif"],
        "font.monospace": [mono_font, "DejaVu Sans Mono"],
        "font.size": base,
        "text.color": core.INK,
        "axes.facecolor": core.WHITE,
        "axes.edgecolor": core.HAIRLINE,
        "axes.labelcolor": core.INK,
        "axes.labelsize": base,
        "axes.titlesize": base + 1.0,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.linewidth": 0.7,
        "axes.axisbelow": True,
        "axes.grid": False,
        "grid.color": core.HAIRLINE,
        "grid.linewidth": 0.62,
        "grid.alpha": 0.72,
        "xtick.color": core.MUTED,
        "ytick.color": core.MUTED,
        "xtick.labelsize": base - 0.9,
        "ytick.labelsize": base - 0.9,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "legend.frameon": False,
        "legend.fontsize": base - 0.9,
        "legend.labelcolor": core.INK,
        "lines.linewidth": 1.7,
        "lines.markersize": 4.2,
        "patch.edgecolor": core.WHITE,
        "patch.linewidth": 0.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "mathtext.fontset": resolved.mathtext_fontset,
        "axes.unicode_minus": True,
    }
    if resolved.mathtext_fontset == "custom":
        rcparams.update({"mathtext.rm": sans_font, "mathtext.it": sans_font, "mathtext.bf": sans_font})
    mpl.rcParams.update(rcparams)


__all__ = ["_available_font", "apply_theme"]
