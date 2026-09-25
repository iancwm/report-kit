#!/usr/bin/env python3
"""ReportKit analytical visualization layer.

High-fidelity Matplotlib helpers for figures embedded in ReportKit technical
reports.  The module mirrors ReportKit's restrained color system, typography,
spacing, and accessibility rules while keeping quantitative analysis in Python.

Typical use
-----------

    import pandas as pd
    import reportkit_viz as rkv

    rkv.apply_theme()
    fig, ax = rkv.timeseries(df[["Portfolio", "Benchmark"]],
                             ylabel="Cumulative return",
                             y_formatter=rkv.percent_formatter(0))
    rkv.save_figure(fig, "figures/performance")

The default export is both vector PDF (for LaTeX) and high-resolution PNG
(for visual QA).  Figures deliberately omit an internal title by default;
ReportKit captions should carry the figure title and provenance.

This module is the small hub the rest of ``reportkit.viz`` composes around:
theme state (the module globals below), the process-wide Matplotlib theme
application, annotation helpers, and the CLI live here; the thirteen chart
constructors live in ``reportkit.viz.charts`` (grouped by chart family), the
LaTeX/Python palette checks live in ``reportkit.viz.palette``, and the visual
regression demo lives in ``reportkit.viz.demo``. All of it is re-exported
from this module so existing imports of ``reportkit_viz``/``reportkit.viz``
and direct ``reportkit.viz.core`` access keep working unchanged.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib as mpl
# ReportKit creates publication assets, never interactive GUI windows. Pin the
# raster backend before pyplot import so host desktop settings cannot change or
# break source builds and pixel QA.
mpl.use("Agg")
import matplotlib.pyplot as plt

# This implementation lives inside the `reportkit.viz` package. The legacy
# reportkit_viz facade imports this package, so the dependency remains one-way
# and theme modules never need to import the compatibility facade.
from reportkit.themes import get_theme
from .charts import (
    bar_chart, bubble_matrix, distribution, donut_chart, drawdown_chart, heatmap,
    risk_reward_chart, scatter_plot, timeline_chart, timeseries, tornado_chart,
    treemap_chart, waterfall_chart,
)
from .demo import build_demo
from .figure import legend_above, new_figure, save_figure, series_style, style_axes
from .formatters import (
    bps_formatter, currency_formatter, integer_formatter, multiple_formatter,
    number_formatter, percent_formatter,
)
from .palette import theme_file_for, validate_palette_against_latex, validate_theme_contract_against_latex
from .theme import apply_theme

__version__ = "1.0.0"

# -----------------------------------------------------------------------------
# ReportKit color system
# -----------------------------------------------------------------------------
# Every name below is theme-owned (reportkit.themes.*) and reassigned by
# apply_theme(), not a fixed constant -- initialized here from the default
# theme purely so importing reportkit_viz without calling apply_theme()
# first still has sane values (matching this module's pre-Step-4 behavior,
# where these actually were fixed constants). See apply_theme()'s docstring
# for why reassigning module globals, rather than threading a theme object
# through every chart function, is how theme-switching reaches the chart
# functions in reportkit.viz.charts, which read these as plain names off
# this module (``from .. import core`` then ``core.PRIMARY`` and so on).
LINE_STYLES = ("-", "--", "-.", ":", (0, (5, 1.5)), (0, (3, 1, 1, 1)))
MARKERS = (None, None, "o", "s", "D", "^")
# Line charts intentionally reserve the first two series for line style alone.
# Bubbles need a distinct shape from the first group onward because colour is
# not a sufficient encoding for accessibility.
BUBBLE_MARKERS = ("o", "s", "D", "^", "v", "P")

# Populated by theme.apply_theme() during module initialization and whenever a
# caller switches themes. Explicit declarations keep the module-level state
# visible to static analysis while chart functions continue to resolve it at
# call time.
INK = MUTED = HAIRLINE = PRIMARY = DECISION = RESEARCH = TIP = RED_FLAG = ""
ASSUMPTION = EVIDENCE = LIMITATION = METRIC = DELIVERABLE = SURFACE = WHITE = ""
DATA_COLORS: tuple[str, ...] = ()
BENCHMARK = DATA_WARM = DATA_POSITIVE = DATA_NEGATIVE = ""
LATEX_THEME_COLORS: dict[str, str] = {}
TEXT_WIDTH_IN: float = 0.0
FIGURE_SIZES: dict[str, tuple[float, float]] = {}
SANS_FONT = SERIF_FONT = MONO_FONT = ""
CHART_GRID_STYLE = "y"
CHART_LEGEND_STYLE = "above"


apply_theme()


# Concise semantic aliases for report scripts.  The *_chart names follow the
# existing API; aliases make the visual grammar's nouns convenient to discover.
treemap = treemap_chart
tornado = tornado_chart
gantt_chart = timeline_chart


# -----------------------------------------------------------------------------
# Annotation helpers for custom analytical plots
# -----------------------------------------------------------------------------
def annotate_point(
    ax: mpl.axes.Axes,
    x,
    y: float,
    text: str,
    *,
    xytext: tuple[float, float] = (8, 8),
    accent: str | None = None,
) -> None:
    """Add one restrained evidence annotation; avoid annotating every point.

    ``accent`` defaults to the *currently applied* theme's PRIMARY color,
    looked up inside the function body rather than as `accent: str =
    PRIMARY` in the signature -- a keyword default is bound once, at
    function-definition (i.e. module-import) time, so binding it directly
    to the PRIMARY global would freeze every call at whichever theme was
    active when reportkit_viz.py was first imported, never following a
    later apply_theme() switch. Found while making apply_theme() genuinely
    support runtime theme-switching (Step 4 of the institutional-theme
    spec); fixed here rather than left as a latent trap now that switching
    themes mid-session is a real, documented capability.
    """
    if accent is None:
        accent = PRIMARY
    ax.annotate(
        text,
        xy=(x, y),
        xytext=xytext,
        textcoords="offset points",
        fontsize=8.0,
        color=INK,
        ha="left",
        va="bottom",
        arrowprops={"arrowstyle": "-", "color": accent, "linewidth": 0.8},
        bbox={"boxstyle": "square,pad=0.28", "facecolor": WHITE, "edgecolor": HAIRLINE, "linewidth": 0.6},
    )


def shade_period(
    ax: mpl.axes.Axes,
    start,
    end,
    *,
    label: str | None = None,
    color: str | None = None,
    alpha: float = 0.08,
) -> None:
    """Shade a known period such as a regime or event window.

    ``color`` defaults to the currently applied theme's EVIDENCE color,
    resolved at call time -- see annotate_point()'s docstring for why that
    can't be a plain `color: str = EVIDENCE` keyword default.
    """
    if color is None:
        color = EVIDENCE
    ax.axvspan(start, end, color=color, alpha=alpha, linewidth=0, label=label)


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="ReportKit analytical visualization helpers and QA utilities."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo_parser = sub.add_parser("demo", help="generate deterministic visual-regression figures")
    demo_parser.add_argument("--out-dir", default="figures", help="output directory for demo figures")

    check_parser = sub.add_parser("check-theme", help="verify Python colors match a ReportKit theme's LaTeX palette")
    check_parser.add_argument("--theme", default="default", help="theme name to check (resolves to latex_templates/themes/reportkit-theme-<name>.sty)")
    check_parser.add_argument("--class", dest="class_path", default=None, help="explicit path override; takes precedence over --theme")

    args = parser.parse_args()
    if args.command == "demo":
        paths = build_demo(args.out_dir)
        for path in paths:
            print(path)
    elif args.command == "check-theme":
        class_path = Path(args.class_path) if args.class_path else theme_file_for(args.theme)
        try:
            theme_colors = get_theme(args.theme).latex_colors
        except ValueError as exc:
            # No reportkit.themes module for this name (open question 2:
            # "honest failure, not a false pass" -- comparing against the
            # wrong theme's Python palette would be exactly that).
            print(f"check-theme: {exc}", file=sys.stderr)
            raise SystemExit(2)
        mismatches = validate_palette_against_latex(class_path, theme_colors)
        contract_errors = validate_theme_contract_against_latex(args.theme)
        if mismatches or contract_errors:
            for item in [*mismatches, *contract_errors]:
                print(item)
            raise SystemExit(1)
        print(f"ReportKit theme contract synchronized: {args.theme} ({class_path})")


__all__ = [
    "LINE_STYLES", "MARKERS", "BUBBLE_MARKERS", "INK", "MUTED", "HAIRLINE", "PRIMARY", "DECISION",
    "RESEARCH", "TIP", "RED_FLAG", "ASSUMPTION", "EVIDENCE", "LIMITATION", "METRIC", "DELIVERABLE",
    "SURFACE", "WHITE", "DATA_COLORS", "BENCHMARK", "DATA_WARM", "DATA_POSITIVE", "DATA_NEGATIVE",
    "LATEX_THEME_COLORS", "TEXT_WIDTH_IN", "FIGURE_SIZES", "SANS_FONT", "SERIF_FONT", "MONO_FONT",
    "CHART_GRID_STYLE", "CHART_LEGEND_STYLE", "plt",
    "apply_theme", "new_figure", "style_axes", "legend_above",
    "series_style", "save_figure", "percent_formatter", "bps_formatter", "number_formatter", "integer_formatter",
    "currency_formatter", "multiple_formatter", "timeseries", "bar_chart", "distribution", "scatter_plot",
    "heatmap", "drawdown_chart", "risk_reward_chart", "donut_chart", "waterfall_chart", "treemap_chart",
    "tornado_chart", "bubble_matrix", "timeline_chart", "annotate_point", "shade_period", "theme_file_for",
    "validate_palette_against_latex", "validate_theme_contract_against_latex", "build_demo", "__version__",
]


if __name__ == "__main__":
    _cli()
