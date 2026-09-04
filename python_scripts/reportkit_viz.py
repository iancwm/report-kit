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
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib import dates as mdates
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd

__version__ = "1.0.0"

# -----------------------------------------------------------------------------
# ReportKit color system
# -----------------------------------------------------------------------------
INK = "#24272D"
MUTED = "#687386"
HAIRLINE = "#D9DEE5"
PRIMARY = "#2C5E78"       # LinkBlue / Principle
DECISION = "#68558A"
RESEARCH = "#2B7074"
TIP = "#3F6D54"
RED_FLAG = "#A14B45"
ASSUMPTION = "#8A6A24"
EVIDENCE = "#4B6472"
LIMITATION = "#6E6A67"
METRIC = "#315E86"
DELIVERABLE = "#2C6E49"  # v1.2 addition, paired with \deliverablenote
SURFACE = "#F7F8FA"
WHITE = "#FFFFFF"

# Analytical colors use the same visual family but are not semantic callout
# labels.  Cool categorical colors avoid accidental good/bad encoding.
DATA_COLORS = (
    PRIMARY,
    RESEARCH,
    DECISION,
    EVIDENCE,
    "#728192",
    "#7B6F88",
)
BENCHMARK = "#8B949E"
DATA_WARM = "#8A6658"      # sign / diverging endpoint; not "bad"
DATA_POSITIVE = TIP        # use only when positive direction is meaningful
DATA_NEGATIVE = RED_FLAG   # use only when negative direction is meaningful


LATEX_THEME_COLORS = {
    "Ink": INK,
    "Muted": MUTED,
    "Hairline": HAIRLINE,
    "LinkBlue": PRIMARY,
    "Principle": PRIMARY,
    "Decision": DECISION,
    "Research": RESEARCH,
    "Tip": TIP,
    "RedFlag": RED_FLAG,
    "Assumption": ASSUMPTION,
    "Evidence": EVIDENCE,
    "Limitation": LIMITATION,
    "MetricAccent": METRIC,
    "Deliverable": DELIVERABLE,
}

LINE_STYLES = ("-", "--", "-.", ":", (0, (5, 1.5)), (0, (3, 1, 1, 1)))
MARKERS = (None, None, "o", "s", "D", "^")

# A4 ReportKit text width: 210mm - 2*27mm = 156mm.
TEXT_WIDTH_IN = 156 / 25.4
FIGURE_SIZES = {
    "full": (TEXT_WIDTH_IN, 3.55),
    "wide": (TEXT_WIDTH_IN, 3.05),
    "compact": (TEXT_WIDTH_IN, 2.55),
    "square": (4.85, 4.35),
}


def _available_font(candidates: Sequence[str], fallback: str = "DejaVu Sans") -> str:
    """Return the first installed font name without requiring local font files."""
    for candidate in candidates:
        try:
            font_manager.findfont(candidate, fallback_to_default=False)
            return candidate
        except ValueError:
            pass
    return fallback


SANS_FONT = _available_font(
    ["Libertinus Sans", "Linux Biolinum O", "Linux Biolinum", "Arial", "DejaVu Sans"]
)
SERIF_FONT = _available_font(
    ["Libertinus Serif", "Linux Libertine O", "Linux Libertine", "DejaVu Serif"]
)
MONO_FONT = _available_font(
    ["Libertinus Mono", "Linux Libertine Mono O", "DejaVu Sans Mono"]
)


def apply_theme() -> None:
    """Apply the ReportKit Matplotlib theme globally.

    This function is idempotent.  It is intentionally conservative: white
    canvas, restrained grid, open top/right spines, embedded TrueType text in
    PDF, and no dependency on seaborn or external style sheets.
    """
    mpl.rcParams.update(
        {
            "figure.facecolor": WHITE,
            "figure.edgecolor": WHITE,
            "figure.dpi": 130,
            "savefig.facecolor": WHITE,
            "savefig.edgecolor": WHITE,
            "savefig.dpi": 320,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
            "font.family": "sans-serif",
            "font.sans-serif": [SANS_FONT, "DejaVu Sans"],
            "font.serif": [SERIF_FONT, "DejaVu Serif"],
            "font.monospace": [MONO_FONT, "DejaVu Sans Mono"],
            "font.size": 9.0,
            "text.color": INK,
            "axes.facecolor": WHITE,
            "axes.edgecolor": HAIRLINE,
            "axes.labelcolor": INK,
            "axes.labelsize": 9.0,
            "axes.titlesize": 10.0,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.linewidth": 0.7,
            "axes.axisbelow": True,
            "axes.grid": False,
            "grid.color": HAIRLINE,
            "grid.linewidth": 0.62,
            "grid.alpha": 0.72,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 8.1,
            "ytick.labelsize": 8.1,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "legend.frameon": False,
            "legend.fontsize": 8.1,
            "legend.labelcolor": INK,
            "lines.linewidth": 1.7,
            "lines.markersize": 4.2,
            "patch.edgecolor": WHITE,
            "patch.linewidth": 0.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "mathtext.fontset": "stix",
            "axes.unicode_minus": True,
        }
    )


apply_theme()


# -----------------------------------------------------------------------------
# Core figure and styling helpers
# -----------------------------------------------------------------------------
def new_figure(
    size: str | tuple[float, float] = "full",
    *,
    constrained: bool = True,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Create one ReportKit figure with a single axes.

    ReportKit documents should prefer one analytical chart per figure.  Use
    custom Matplotlib code for true small-multiple analysis, but keep the same
    theme and export helpers.
    """
    figsize = FIGURE_SIZES[size] if isinstance(size, str) else size
    layout = "constrained" if constrained else None
    fig, ax = plt.subplots(figsize=figsize, layout=layout)
    if constrained:
        fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.02, hspace=0.02)
    return fig, ax


def style_axes(
    ax: mpl.axes.Axes,
    *,
    grid: str | None = "y",
    zero_line: bool = False,
    integer_x: bool = False,
    integer_y: bool = False,
) -> mpl.axes.Axes:
    """Apply the standard ReportKit analytical axis treatment."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(HAIRLINE)
    ax.spines["bottom"].set_color(HAIRLINE)
    ax.tick_params(axis="both", colors=MUTED)

    if grid == "y":
        ax.grid(axis="y")
    elif grid == "x":
        ax.grid(axis="x")
    elif grid == "both":
        ax.grid(axis="both")
    elif grid is None:
        ax.grid(False)
    else:
        raise ValueError("grid must be one of: 'x', 'y', 'both', or None")

    if zero_line:
        ax.axhline(0, color=EVIDENCE, linewidth=0.8, zorder=1)

    if integer_x:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    if integer_y:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    return ax


def _title(ax: mpl.axes.Axes, title: str | None) -> None:
    """Use only when a chart must stand alone outside a ReportKit caption."""
    if title:
        ax.set_title(title, loc="left", color=INK, pad=9)


def legend_above(
    ax: mpl.axes.Axes,
    *,
    ncol: int | None = None,
    order: Sequence[int] | None = None,
) -> None:
    """Place a compact legend above the plotting region without a frame."""
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return
    if order is not None:
        handles = [handles[i] for i in order]
        labels = [labels[i] for i in order]
    if ncol is None:
        ncol = min(len(handles), 3)
    ax.legend(
        handles,
        labels,
        loc="lower left",
        bbox_to_anchor=(0, 1.01),
        borderaxespad=0,
        ncol=ncol,
        columnspacing=1.4,
        handlelength=2.4,
    )


def series_style(index: int, *, benchmark: bool = False) -> dict:
    """Return a color + line style combination robust to grayscale."""
    if benchmark:
        return {"color": BENCHMARK, "linestyle": "--", "linewidth": 1.35}
    i = index % len(DATA_COLORS)
    return {
        "color": DATA_COLORS[i],
        "linestyle": LINE_STYLES[i % len(LINE_STYLES)],
        "marker": MARKERS[i % len(MARKERS)],
        "linewidth": 1.75 if i == 0 else 1.5,
    }


def save_figure(
    fig: mpl.figure.Figure,
    stem: str | Path,
    *,
    formats: Sequence[str] = ("pdf", "png"),
    dpi: int = 320,
    close: bool = True,
    metadata: Mapping[str, str] | None = None,
) -> list[Path]:
    """Save a figure in ReportKit-ready formats.

    Vector PDF is intended for LaTeX inclusion. PNG is generated for visual QA
    and environments where vector embedding is unavailable.
    """
    stem = Path(stem)
    if stem.suffix:
        stem = stem.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for fmt in formats:
        fmt = fmt.lower().lstrip(".")
        path = stem.with_suffix(f".{fmt}")
        kwargs: dict = {"bbox_inches": "tight", "pad_inches": 0.04}
        if fmt in {"png", "jpg", "jpeg", "webp"}:
            kwargs["dpi"] = dpi
        if metadata is not None and fmt in {"pdf", "png", "svg"}:
            kwargs["metadata"] = dict(metadata)
        fig.savefig(path, **kwargs)
        outputs.append(path)
    if close:
        plt.close(fig)
    return outputs


# -----------------------------------------------------------------------------
# Axis formatters
# -----------------------------------------------------------------------------
def percent_formatter(decimals: int = 0, *, scale: float = 100.0) -> FuncFormatter:
    return FuncFormatter(lambda x, _: f"{x * scale:.{decimals}f}%")


def bps_formatter(decimals: int = 0) -> FuncFormatter:
    return FuncFormatter(lambda x, _: f"{x * 10000:.{decimals}f} bp")


def number_formatter(decimals: int = 1) -> FuncFormatter:
    return FuncFormatter(lambda x, _: f"{x:,.{decimals}f}")


def integer_formatter() -> FuncFormatter:
    return FuncFormatter(lambda x, _: f"{x:,.0f}")


def currency_formatter(symbol: str = "$", decimals: int = 0) -> FuncFormatter:
    return FuncFormatter(lambda x, _: f"{symbol}{x:,.{decimals}f}")


def multiple_formatter(decimals: int = 1) -> FuncFormatter:
    return FuncFormatter(lambda x, _: f"{x:.{decimals}f}×")


def _apply_formatter(axis, formatter: FuncFormatter | str | None) -> None:
    if formatter is None:
        return
    if isinstance(formatter, str):
        presets = {
            "percent": percent_formatter(0),
            "percent1": percent_formatter(1),
            "bps": bps_formatter(0),
            "integer": integer_formatter(),
            "number": number_formatter(1),
            "multiple": multiple_formatter(1),
        }
        if formatter not in presets:
            raise ValueError(f"unknown formatter preset: {formatter}")
        formatter = presets[formatter]
    axis.set_major_formatter(formatter)


def _format_datetime_axis(ax: mpl.axes.Axes, index: pd.Index) -> None:
    if not isinstance(index, pd.DatetimeIndex) or len(index) == 0:
        return
    span_days = max((index.max() - index.min()).days, 1)
    if span_days <= 550:
        locator = mdates.MonthLocator(interval=3)
    elif span_days <= 5 * 365:
        locator = mdates.MonthLocator(interval=6)
    elif span_days <= 10 * 365:
        locator = mdates.YearLocator(base=1)
    else:
        locator = mdates.YearLocator(base=2)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))


# -----------------------------------------------------------------------------
# High-level analytical chart helpers
# -----------------------------------------------------------------------------
def timeseries(
    data: pd.Series | pd.DataFrame,
    *,
    ylabel: str | None = None,
    xlabel: str | None = None,
    y_formatter: FuncFormatter | str | None = None,
    benchmark: str | None = None,
    reference_line: float | None = None,
    legend: bool = True,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot one to six time series with ReportKit line semantics."""
    if isinstance(data, pd.Series):
        name = data.name or "Series"
        data = data.to_frame(name)
    if data.shape[1] > 6:
        raise ValueError("ReportKit time-series charts should normally show no more than six series")

    fig, ax = new_figure(size)
    for i, column in enumerate(data.columns):
        is_benchmark = benchmark is not None and column == benchmark
        ax.plot(data.index, data[column], label=str(column), **series_style(i, benchmark=is_benchmark))

    style_axes(ax, grid="y")
    _format_datetime_axis(ax, data.index)
    if reference_line is not None:
        ax.axhline(reference_line, color=HAIRLINE, linewidth=0.9, zorder=0)
    ax.set_ylabel(ylabel or "")
    ax.set_xlabel(xlabel or "")
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    if legend and data.shape[1] > 1:
        legend_above(ax)
    return fig, ax


def bar_chart(
    data: pd.Series | Mapping[str, float],
    *,
    horizontal: bool = True,
    highlight: str | Sequence[str] | None = None,
    value_formatter: FuncFormatter | str | None = None,
    axis_label: str | None = None,
    sort: bool = False,
    zero_line: bool = True,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Clean categorical bar chart, useful for exposures and decompositions."""
    s = pd.Series(data, dtype=float)
    if sort:
        s = s.sort_values()
    highlights = {highlight} if isinstance(highlight, str) else set(highlight or [])
    colors = [PRIMARY if (not highlights or str(idx) in highlights) else "#A8B1BA" for idx in s.index]

    fig, ax = new_figure(size)
    if horizontal:
        ax.barh([str(x) for x in s.index], s.values, color=colors, height=0.62)
        ax.invert_yaxis()
        style_axes(ax, grid="x")
        if zero_line:
            ax.axvline(0, color=EVIDENCE, linewidth=0.8, zorder=1)
        _apply_formatter(ax.xaxis, value_formatter)
        ax.set_xlabel(axis_label or "")
        ax.set_ylabel("")
    else:
        ax.bar([str(x) for x in s.index], s.values, color=colors, width=0.62)
        style_axes(ax, grid="y", zero_line=zero_line)
        _apply_formatter(ax.yaxis, value_formatter)
        ax.set_ylabel(axis_label or "")
        ax.set_xlabel("")
    _title(ax, title)
    return fig, ax


def distribution(
    values: Sequence[float] | pd.Series | np.ndarray,
    *,
    bins: int | str = "fd",
    xlabel: str | None = None,
    x_formatter: FuncFormatter | str | None = None,
    reference: float | None = None,
    density: bool = False,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Histogram without decorative KDE assumptions."""
    x = np.asarray(pd.Series(values).dropna(), dtype=float)
    fig, ax = new_figure(size)
    ax.hist(x, bins=bins, density=density, color=PRIMARY, alpha=0.88, edgecolor=WHITE, linewidth=0.55)
    style_axes(ax, grid="y")
    if reference is not None:
        ax.axvline(reference, color=DECISION, linewidth=1.35, linestyle="--")
    ax.set_xlabel(xlabel or "")
    ax.set_ylabel("Density" if density else "Count")
    _apply_formatter(ax.xaxis, x_formatter)
    _title(ax, title)
    return fig, ax


def scatter_plot(
    x: Sequence[float] | pd.Series | np.ndarray,
    y: Sequence[float] | pd.Series | np.ndarray,
    *,
    xlabel: str,
    ylabel: str,
    fit_line: bool = False,
    x_formatter: FuncFormatter | str | None = None,
    y_formatter: FuncFormatter | str | None = None,
    reference_x: float | None = None,
    reference_y: float | None = None,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Scatter plot with optional first-order fit for diagnostics."""
    xy = pd.DataFrame({"x": x, "y": y}).dropna()
    fig, ax = new_figure(size)
    ax.scatter(xy["x"], xy["y"], s=24, color=PRIMARY, alpha=0.68, linewidths=0)
    style_axes(ax, grid="both")

    if fit_line and len(xy) >= 2:
        coeff = np.polyfit(xy["x"].to_numpy(), xy["y"].to_numpy(), 1)
        xx = np.linspace(float(xy["x"].min()), float(xy["x"].max()), 100)
        ax.plot(xx, coeff[0] * xx + coeff[1], color=DECISION, linewidth=1.3, linestyle="--", label="Linear fit")
        legend_above(ax, ncol=1)
    if reference_x is not None:
        ax.axvline(reference_x, color=HAIRLINE, linewidth=0.9)
    if reference_y is not None:
        ax.axhline(reference_y, color=HAIRLINE, linewidth=0.9)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _apply_formatter(ax.xaxis, x_formatter)
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    return fig, ax


def _sequential_cmap() -> mpl.colors.Colormap:
    return mcolors.LinearSegmentedColormap.from_list(
        "reportkit_sequential", ["#F7F8FA", "#BCCBD3", "#6F91A4", PRIMARY]
    )


def _diverging_cmap() -> mpl.colors.Colormap:
    return mcolors.LinearSegmentedColormap.from_list(
        "reportkit_diverging", [DATA_WARM, "#E5DAD5", "#FAFAFA", "#D7E2E7", PRIMARY]
    )


def heatmap(
    matrix: pd.DataFrame | np.ndarray,
    *,
    row_labels: Sequence[str] | None = None,
    col_labels: Sequence[str] | None = None,
    center: float | None = 0.0,
    vmin: float | None = None,
    vmax: float | None = None,
    annotate: bool = False,
    annotation_format: str = ".2f",
    cbar_label: str | None = None,
    size: str | tuple[float, float] = "square",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Sequential or diverging heatmap for correlations and scenario matrices."""
    if isinstance(matrix, pd.DataFrame):
        values = matrix.to_numpy(dtype=float)
        row_labels = list(matrix.index.astype(str)) if row_labels is None else row_labels
        col_labels = list(matrix.columns.astype(str)) if col_labels is None else col_labels
    else:
        values = np.asarray(matrix, dtype=float)

    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("heatmap matrix contains no finite values")
    if vmin is None:
        vmin = float(finite.min())
    if vmax is None:
        vmax = float(finite.max())

    fig, ax = new_figure(size)
    if center is None:
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        cmap = _sequential_cmap()
    else:
        # Ensure the center lies strictly inside the normalization range.
        if not vmin < center < vmax:
            bound = max(abs(vmin - center), abs(vmax - center), 1e-12)
            vmin, vmax = center - bound, center + bound
        norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=center, vmax=vmax)
        cmap = _diverging_cmap()

    im = ax.imshow(values, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(values.shape[1]))
    ax.set_yticks(np.arange(values.shape[0]))
    if col_labels is not None:
        ax.set_xticklabels(col_labels)
    if row_labels is not None:
        ax.set_yticklabels(row_labels)
    ax.tick_params(axis="x", rotation=35, length=0)
    ax.tick_params(axis="y", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    if annotate:
        if values.size > 100:
            raise ValueError("annotated heatmaps should normally contain no more than 100 cells")
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                val = values[i, j]
                if not np.isfinite(val):
                    continue
                rgba = cmap(norm(val))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                text_color = WHITE if luminance < 0.52 else INK
                ax.text(j, i, format(val, annotation_format), ha="center", va="center", color=text_color, fontsize=7.3)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.035)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors=MUTED, labelsize=7.8, width=0.5, length=2.5)
    if cbar_label:
        cbar.set_label(cbar_label, color=INK, size=8.2)
    _title(ax, title)
    return fig, ax


def drawdown_chart(
    drawdown: pd.Series,
    *,
    ylabel: str = "Drawdown",
    y_formatter: FuncFormatter | str | None = "percent",
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot a precomputed drawdown series as a restrained filled area."""
    s = pd.Series(drawdown).dropna()
    fig, ax = new_figure(size)
    ax.fill_between(s.index, s.values, 0, color=PRIMARY, alpha=0.17, linewidth=0)
    ax.plot(s.index, s.values, color=PRIMARY, linewidth=1.35)
    style_axes(ax, grid="y")
    _format_datetime_axis(ax, s.index)
    ax.axhline(0, color=HAIRLINE, linewidth=0.9)
    ax.set_ylabel(ylabel)
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    return fig, ax


def waterfall_chart(
    contributions: pd.Series | Mapping[str, float],
    *,
    total_label: str = "Total",
    value_formatter: FuncFormatter | str | None = None,
    ylabel: str | None = None,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Attribution-style waterfall using warm/cool sign encoding.

    Warm/cool encodes arithmetic sign, not desirability.  Total is neutral ink.
    """
    s = pd.Series(contributions, dtype=float)
    vals = s.to_numpy()
    starts = np.r_[0.0, np.cumsum(vals)[:-1]]
    colors = [PRIMARY if v >= 0 else DATA_WARM for v in vals]

    labels = [str(x) for x in s.index] + [total_label]
    fig, ax = new_figure(size)
    x = np.arange(len(vals))
    ax.bar(x, vals, bottom=starts, color=colors, width=0.62)

    cumulative = np.cumsum(vals)
    for i in range(len(vals) - 1):
        ax.plot([i + 0.31, i + 1 - 0.31], [cumulative[i], cumulative[i]], color=HAIRLINE, linewidth=0.8)

    total = float(vals.sum())
    ax.bar(len(vals), total, color=INK, width=0.62)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    style_axes(ax, grid="y", zero_line=True)
    _apply_formatter(ax.yaxis, value_formatter)
    ax.set_ylabel(ylabel or "")
    _title(ax, title)
    return fig, ax


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
    accent: str = PRIMARY,
) -> None:
    """Add one restrained evidence annotation; avoid annotating every point."""
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
    color: str = EVIDENCE,
    alpha: float = 0.08,
) -> None:
    """Shade a known period such as a regime or event window."""
    ax.axvspan(start, end, color=color, alpha=alpha, linewidth=0, label=label)


# -----------------------------------------------------------------------------
# Theme synchronization
# -----------------------------------------------------------------------------
def validate_palette_against_latex(class_path: str | Path) -> list[str]:
    """Return human-readable mismatches between Python and reportkit.cls colors."""
    class_path = Path(class_path)
    text = class_path.read_text(encoding="utf-8")
    found = {
        name: f"#{value.upper()}"
        for name, value in re.findall(r"\\definecolor\{([^}]+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}", text)
    }
    mismatches: list[str] = []
    for name, expected in LATEX_THEME_COLORS.items():
        actual = found.get(name)
        if actual is None:
            mismatches.append(f"missing LaTeX color: {name}")
        elif actual.upper() != expected.upper():
            mismatches.append(f"{name}: LaTeX {actual} != Python {expected}")
    return mismatches


# -----------------------------------------------------------------------------
# Demo / regression figures
# -----------------------------------------------------------------------------
def build_demo(out_dir: str | Path) -> list[Path]:
    """Generate deterministic sample finance figures for visual regression QA."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    rng = np.random.default_rng(14)
    dates = pd.date_range("2022-01-31", periods=44, freq="ME")
    portfolio_r = rng.normal(0.0075, 0.027, len(dates))
    benchmark_r = rng.normal(0.0050, 0.024, len(dates))
    portfolio = pd.Series(np.cumprod(1 + portfolio_r) - 1, index=dates, name="Portfolio")
    benchmark = pd.Series(np.cumprod(1 + benchmark_r) - 1, index=dates, name="Benchmark")
    perf = pd.concat([portfolio, benchmark], axis=1)

    fig, _ = timeseries(perf, ylabel="Cumulative return", y_formatter=percent_formatter(0), benchmark="Benchmark")
    outputs += save_figure(fig, out_dir / "performance")

    wealth = 1 + portfolio
    dd = wealth / wealth.cummax() - 1
    fig, _ = drawdown_chart(dd, y_formatter=percent_formatter(0))
    outputs += save_figure(fig, out_dir / "drawdown")

    exposures = pd.Series(
        {"Value": 0.34, "Quality": 0.18, "Momentum": -0.12, "Size": 0.07, "Low beta": -0.21}
    )
    fig, _ = bar_chart(exposures, horizontal=True, value_formatter=number_formatter(2), axis_label="Standardized exposure")
    outputs += save_figure(fig, out_dir / "factor_exposures")

    monthly = pd.Series(portfolio_r)
    fig, _ = distribution(monthly, xlabel="Monthly return", x_formatter=percent_formatter(0), reference=0)
    outputs += save_figure(fig, out_dir / "return_distribution")

    corr = pd.DataFrame(
        [
            [1.00, 0.41, -0.22, 0.15],
            [0.41, 1.00, -0.08, 0.31],
            [-0.22, -0.08, 1.00, -0.36],
            [0.15, 0.31, -0.36, 1.00],
        ],
        index=["Value", "Quality", "Momentum", "Low beta"],
        columns=["Value", "Quality", "Momentum", "Low beta"],
    )
    fig, _ = heatmap(corr, vmin=-1, vmax=1, center=0, annotate=True, cbar_label="Correlation")
    outputs += save_figure(fig, out_dir / "correlation")

    forecasts = rng.normal(0, 0.035, 95)
    realized = 0.42 * forecasts + rng.normal(0, 0.028, 95)
    fig, _ = scatter_plot(
        forecasts,
        realized,
        xlabel="Forecast return",
        ylabel="Realized return",
        fit_line=True,
        x_formatter=percent_formatter(0),
        y_formatter=percent_formatter(0),
        reference_x=0,
        reference_y=0,
    )
    outputs += save_figure(fig, out_dir / "forecast_scatter")

    attr = pd.Series({"Selection": 0.0062, "Value": 0.0031, "Momentum": -0.0024, "Trading": -0.0012, "Other": 0.0007})
    fig, _ = waterfall_chart(attr, total_label="Active return", value_formatter=percent_formatter(1), ylabel="Contribution")
    outputs += save_figure(fig, out_dir / "attribution")

    return outputs


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="ReportKit analytical visualization helpers and QA utilities."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo_parser = sub.add_parser("demo", help="generate deterministic visual-regression figures")
    demo_parser.add_argument("--out-dir", default="figures", help="output directory for demo figures")

    check_parser = sub.add_parser("check-theme", help="verify Python colors match reportkit.cls")
    check_parser.add_argument("--class", dest="class_path", default="reportkit.cls", help="path to reportkit.cls")

    args = parser.parse_args()
    if args.command == "demo":
        paths = build_demo(args.out_dir)
        for path in paths:
            print(path)
    elif args.command == "check-theme":
        mismatches = validate_palette_against_latex(args.class_path)
        if mismatches:
            for item in mismatches:
                print(item)
            raise SystemExit(1)
        print(f"ReportKit palette synchronized: {args.class_path}")


if __name__ == "__main__":
    _cli()
