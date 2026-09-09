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
from typing import Any, Mapping, Sequence

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
    opening: float = 0.0,
    opening_label: str = "Opening",
    total_label: str = "Total",
    subtotals: Mapping[str, int] | Sequence[tuple[str, int]] | None = None,
    closing_total: float | None = None,
    value_formatter: FuncFormatter | str | None = None,
    ylabel: str | None = None,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Render an opening-to-closing financial or operational bridge.

    ``contributions`` contains signed deltas in their intended reading order.
    ``subtotals`` maps a subtotal label to the number of deltas after which it
    should be shown (for example, ``{"Gross profit": 3}``).  The closing
    total defaults to ``opening + contributions.sum()``; an explicit
    ``closing_total`` is useful when reconciling a separately reported total.
    Warm/cool encodes arithmetic sign, not desirability.
    """
    s = pd.Series(contributions, dtype=float)
    if s.empty:
        raise ValueError("waterfall_chart requires at least one contribution")
    if not np.isfinite(s.to_numpy()).all():
        raise ValueError("waterfall_chart contributions must all be finite numbers")
    if not np.isfinite(opening):
        raise ValueError("waterfall_chart opening must be a finite number")
    if closing_total is not None and not np.isfinite(closing_total):
        raise ValueError("waterfall_chart closing_total must be a finite number")

    subtotal_items = list(subtotals.items()) if isinstance(subtotals, Mapping) else list(subtotals or [])
    subtotal_after: dict[int, list[str]] = {}
    for label, position in subtotal_items:
        if not isinstance(position, (int, np.integer)) or not 1 <= position <= len(s):
            raise ValueError(
                f"waterfall subtotal '{label}' must follow an integer contribution position from 1 to {len(s)}"
            )
        subtotal_after.setdefault(int(position), []).append(str(label))

    vals = s.to_numpy()
    running = float(opening)
    bars: list[tuple[str, float, float, str]] = [(opening_label, 0.0, float(opening), "total")]
    for position, (label, value) in enumerate(s.items(), start=1):
        bars.append((str(label), running, float(value), "delta"))
        running += float(value)
        for subtotal_label in subtotal_after.get(position, []):
            bars.append((subtotal_label, 0.0, running, "subtotal"))
    closing = running if closing_total is None else float(closing_total)
    if closing_total is not None and not np.isclose(closing, running, rtol=1e-9, atol=1e-12):
        raise ValueError(
            "waterfall_chart closing_total does not reconcile to opening plus contributions; "
            "add the missing bridge item instead"
        )
    bars.append((total_label, 0.0, closing, "total"))

    fig, ax = new_figure(size)
    x = np.arange(len(bars))
    for i, (_, bottom, height, kind) in enumerate(bars):
        if kind == "delta":
            color = PRIMARY if height >= 0 else DATA_WARM
        elif kind == "subtotal":
            color = EVIDENCE
        else:
            color = INK
        ax.bar(i, height, bottom=bottom, color=color, width=0.62)

    # Connect only consecutive delta steps.  Totals deliberately break the
    # connector so arithmetic state remains readable without relying on color.
    previous_delta: int | None = 0
    running = float(opening)
    for i, (_, bottom, height, kind) in enumerate(bars[1:], start=1):
        if kind == "delta" and previous_delta is not None:
            ax.plot([previous_delta + 0.31, i - 0.31], [running, running], color=HAIRLINE, linewidth=0.8)
            running = bottom + height
            previous_delta = i
        elif kind == "delta":
            running = bottom + height
            previous_delta = i
        else:
            previous_delta = None

    ax.set_xticks(x)
    ax.set_xticklabels([item[0] for item in bars], rotation=25, ha="right")
    style_axes(ax, grid="y", zero_line=True)
    _apply_formatter(ax.yaxis, value_formatter)
    ax.set_ylabel(ylabel or "")
    _title(ax, title)
    return fig, ax


def _format_chart_value(value: float, formatter: FuncFormatter | str | None) -> str:
    """Format a value for an in-chart label using the public formatter API."""
    if formatter is None:
        return f"{value:,.3g}"
    if isinstance(formatter, str):
        presets: dict[str, FuncFormatter] = {
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
    return str(formatter(value, 0))


def _treemap_rectangles(
    items: Sequence[tuple[Any, float]], x: float, y: float, width: float, height: float
) -> dict[Any, tuple[float, float, float, float]]:
    """Return deterministic, value-proportional rectangles without extra deps.

    The balanced binary subdivision is intentionally modest rather than a
    clever-looking dependency: it stays vector-native and makes small report
    figures reproducible across environments.
    """
    if not items:
        return {}
    ordered = sorted(items, key=lambda item: (-item[1], str(item[0])))
    if len(ordered) == 1:
        return {ordered[0][0]: (x, y, width, height)}
    total = sum(item[1] for item in ordered)
    running = 0.0
    split = 1
    best_distance = float("inf")
    for index, (_, value) in enumerate(ordered[:-1], start=1):
        running += value
        distance = abs(total / 2 - running)
        if distance <= best_distance:
            best_distance = distance
            split = index
        else:
            break
    first, second = ordered[:split], ordered[split:]
    first_total = sum(item[1] for item in first)
    ratio = first_total / total
    if width >= height:
        first_rect = _treemap_rectangles(first, x, y, width * ratio, height)
        second_rect = _treemap_rectangles(second, x + width * ratio, y, width * (1 - ratio), height)
    else:
        first_rect = _treemap_rectangles(first, x, y, width, height * ratio)
        second_rect = _treemap_rectangles(second, x, y + height * ratio, width, height * (1 - ratio))
    return first_rect | second_rect


def _treemap_mapping(data: Mapping[Any, Any], path: tuple[str, ...] = ()) -> dict[str, Any]:
    """Normalize nested mapping input to a small validated tree."""
    tree: dict[str, Any] = {}
    for raw_label, raw_value in data.items():
        label = str(raw_label)
        if isinstance(raw_value, Mapping):
            if not raw_value:
                raise ValueError(f"treemap hierarchy '{'/'.join(path + (label,))}' cannot be empty")
            tree[label] = _treemap_mapping(raw_value, path + (label,))
        else:
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"treemap value for '{'/'.join(path + (label,))}' must be numeric") from exc
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"treemap value for '{'/'.join(path + (label,))}' must be finite and greater than zero")
            tree[label] = value
    return tree


def _treemap_value(node: Any) -> float:
    return float(node) if not isinstance(node, Mapping) else sum(_treemap_value(child) for child in node.values())


def _treemap_from_frame(
    data: pd.DataFrame,
    *,
    label_column: str,
    value_column: str,
    parent_column: str | None,
    group_column: str | None,
) -> dict[str, Any]:
    required = {label_column, value_column}
    if parent_column:
        required.add(parent_column)
    if group_column:
        required.add(group_column)
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"treemap data is missing required column(s): {', '.join(sorted(missing))}")
    frame = data.loc[:, list(required)].copy()
    frame[label_column] = frame[label_column].astype(str)
    if frame[label_column].duplicated().any():
        raise ValueError("treemap hierarchy labels must be unique when a DataFrame is used")
    values = pd.to_numeric(frame[value_column], errors="coerce")
    if values.isna().any() or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("treemap values must be finite numbers greater than zero")
    frame[value_column] = values

    if not parent_column:
        flat = dict(zip(frame[label_column], frame[value_column]))
        if group_column:
            grouped: dict[str, dict[str, float]] = {}
            for group, label, value in frame[[group_column, label_column, value_column]].itertuples(index=False):
                grouped.setdefault(str(group), {})[str(label)] = float(value)
            return grouped
        return flat

    labels = set(frame[label_column])
    parents: dict[str, str | None] = {}
    children: dict[str, list[str]] = {label: [] for label in labels}
    values_by_label = dict(zip(frame[label_column], frame[value_column]))
    for label, parent in frame[[label_column, parent_column]].itertuples(index=False):
        parent_label = None if pd.isna(parent) or str(parent).strip() == "" else str(parent)
        if parent_label is not None and parent_label not in labels:
            raise ValueError(f"treemap parent '{parent_label}' for '{label}' is not present in the data")
        parents[str(label)] = parent_label
        if parent_label is not None:
            children[parent_label].append(str(label))

    def build(label: str, ancestry: tuple[str, ...] = ()) -> Any:
        if label in ancestry:
            raise ValueError(f"treemap hierarchy contains a cycle at '{label}'")
        if not children[label]:
            return float(values_by_label[label])
        return {child: build(child, ancestry + (label,)) for child in children[label]}

    roots = [label for label in labels if parents[label] is None]
    if not roots:
        raise ValueError("treemap hierarchy needs at least one root node")
    # Validate disconnected components as well: otherwise a cycle alongside a
    # valid root would be silently omitted from the rendered hierarchy.
    for label in labels:
        build(label)
    return {root: build(root) for root in roots}


def treemap_chart(
    data: pd.Series | Mapping[str, float | Mapping] | pd.DataFrame,
    *,
    label_column: str = "label",
    value_column: str = "value",
    parent_column: str | None = None,
    group_column: str | None = None,
    min_category_fraction: float = 0.02,
    min_label_fraction: float = 0.045,
    other_label: str = "Other",
    value_formatter: FuncFormatter | str | None = None,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Draw a flat or nested, vector-native treemap.

    A mapping of scalars or a Series produces a flat chart.  A nested mapping
    produces hierarchy; DataFrames support either flat ``label``/``value``
    data or a unique-label parent hierarchy.  Flat categories below
    ``min_category_fraction`` are combined into ``other_label`` so the chart
    does not pretend tiny values are equally legible.
    """
    if not 0 <= min_category_fraction < 1 or not 0 <= min_label_fraction < 1:
        raise ValueError("treemap minimum category and label fractions must be in [0, 1)")
    if isinstance(data, pd.DataFrame):
        tree = _treemap_from_frame(
            data, label_column=label_column, value_column=value_column,
            parent_column=parent_column, group_column=group_column,
        )
    elif isinstance(data, pd.Series):
        tree = _treemap_mapping(data.to_dict())
    elif isinstance(data, Mapping):
        tree = _treemap_mapping(data)
    else:
        raise TypeError("treemap_chart data must be a pandas Series, DataFrame, or mapping")
    if not tree:
        raise ValueError("treemap_chart requires at least one category")

    # Combine only a flat tree.  Grouped and nested input intentionally retains
    # its declared hierarchy, which itself gives small leaves useful context.
    if all(not isinstance(value, Mapping) for value in tree.values()):
        total = _treemap_value(tree)
        small = {label: value for label, value in tree.items() if value / total < min_category_fraction}
        if small and len(small) < len(tree):
            tree = {label: value for label, value in tree.items() if label not in small}
            tree[other_label] = sum(small.values())

    total = _treemap_value(tree)
    fig, ax = new_figure(size)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("auto")
    ax.axis("off")
    top_colors = {label: DATA_COLORS[index % len(DATA_COLORS)] for index, label in enumerate(tree)}

    def draw_level(nodes: Mapping[str, Any], bounds: tuple[float, float, float, float], depth: int, top_label: str | None) -> None:
        x, y, width, height = bounds
        items = [(label, _treemap_value(value)) for label, value in nodes.items()]
        rectangles = _treemap_rectangles(items, x, y, width, height)
        for label, node in nodes.items():
            rx, ry, rw, rh = rectangles[label]
            branch = label if top_label is None else top_label
            color = top_colors[branch]
            if isinstance(node, Mapping):
                ax.add_patch(mpl.patches.Rectangle((rx, ry), rw, rh, facecolor=mcolors.to_rgba(color, 0.08), edgecolor=color, linewidth=1.0))
                inset = min(0.65, rw / 9, rh / 9)
                if rw > inset * 2 and rh > inset * 2:
                    draw_level(node, (rx + inset, ry + inset, rw - 2 * inset, rh - 2 * inset), depth + 1, branch)
                if rw * rh / 10000 >= min_label_fraction:
                    ax.text(rx + 1.1, ry + rh - 1.3, label, va="top", ha="left", color=INK, fontsize=7.7,
                            fontweight="semibold", clip_on=True)
            else:
                ax.add_patch(mpl.patches.Rectangle((rx, ry), rw, rh, facecolor=mcolors.to_rgba(color, 0.84 if depth == 0 else 0.60), edgecolor=WHITE, linewidth=0.8))
                fraction = float(node) / total
                if fraction >= min_label_fraction:
                    label_text = f"{label}\n{_format_chart_value(float(node), value_formatter)}"
                    ax.text(rx + rw / 2, ry + rh / 2, label_text, ha="center", va="center", color=WHITE,
                            fontsize=7.4, linespacing=1.22, clip_on=True)

    draw_level(tree, (0, 0, 100, 100), 0, None)
    _title(ax, title)
    return fig, ax


def tornado_chart(
    sensitivities: Mapping[str, Sequence[float]] | pd.DataFrame,
    *,
    base_case: float = 0.0,
    low_column: str = "low",
    high_column: str = "high",
    label_column: str | None = None,
    value_formatter: FuncFormatter | str | None = None,
    xlabel: str | None = None,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Draw ordered low/high sensitivity bars around a labelled base case."""
    if not np.isfinite(base_case):
        raise ValueError("tornado_chart base_case must be a finite number")
    if isinstance(sensitivities, pd.DataFrame):
        required = {low_column, high_column}
        if label_column:
            required.add(label_column)
        missing = required - set(sensitivities.columns)
        if missing:
            raise ValueError(f"tornado data is missing required column(s): {', '.join(sorted(missing))}")
        labels = sensitivities[label_column].astype(str) if label_column else sensitivities.index.astype(str)
        frame = pd.DataFrame({"label": labels, "low": sensitivities[low_column], "high": sensitivities[high_column]})
    elif isinstance(sensitivities, Mapping):
        rows = []
        for label, pair in sensitivities.items():
            if len(pair) != 2:
                raise ValueError(f"tornado sensitivity '{label}' must contain exactly (low, high)")
            rows.append((str(label), pair[0], pair[1]))
        frame = pd.DataFrame(rows, columns=["label", "low", "high"])
    else:
        raise TypeError("tornado_chart sensitivities must be a DataFrame or mapping of (low, high) pairs")
    if frame.empty:
        raise ValueError("tornado_chart requires at least one sensitivity")
    frame[["low", "high"]] = frame[["low", "high"]].apply(pd.to_numeric, errors="coerce")
    if frame[["low", "high"]].isna().any().any() or not np.isfinite(frame[["low", "high"]].to_numpy()).all():
        raise ValueError("tornado low and high values must be finite numbers")
    frame["spread"] = (frame["high"] - frame["low"]).abs()
    frame = frame.sort_values("spread", ascending=True, kind="stable")

    fig, ax = new_figure(size)
    y = np.arange(len(frame))
    low_delta = frame["low"].to_numpy() - base_case
    high_delta = frame["high"].to_numpy() - base_case
    ax.barh(y, low_delta, color=DATA_WARM, height=0.62, label="Low case")
    ax.barh(y, high_delta, color=PRIMARY, height=0.62, label="High case")
    ax.axvline(0, color=INK, linewidth=0.9, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(frame["label"])
    style_axes(ax, grid="x")
    _apply_formatter(ax.xaxis, value_formatter)
    ax.set_xlabel(xlabel or f"Change from base case ({_format_chart_value(float(base_case), value_formatter)})")
    _title(ax, title)
    legend_above(ax, ncol=2)
    return fig, ax


def _bubble_areas(values: Sequence[float], minimum: float, maximum: float) -> np.ndarray:
    raw = np.asarray(values, dtype=float)
    if not np.isfinite(raw).all() or (raw < 0).any():
        raise ValueError("bubble sizes must be finite, non-negative numbers")
    if np.all(raw == 0):
        return np.zeros_like(raw)
    if float(raw.max()) == float(raw.min()):
        return np.full_like(raw, (minimum + maximum) / 2)
    return minimum + (raw - raw.min()) / (raw.max() - raw.min()) * (maximum - minimum)


def bubble_matrix(
    data: pd.DataFrame,
    *,
    x: str,
    y: str,
    xlabel: str,
    ylabel: str,
    size_column: str | None = None,
    label_column: str | None = None,
    group_column: str | None = None,
    reference_x: float | None = None,
    reference_y: float | None = None,
    quadrant_labels: Mapping[str, str] | None = None,
    x_formatter: FuncFormatter | str | None = None,
    y_formatter: FuncFormatter | str | None = None,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """DataFrame-oriented scatter/bubble matrix with optional quadrants.

    ``quadrant_labels`` accepts ``upper-left``, ``upper-right``,
    ``lower-left``, and ``lower-right`` keys and requires both reference lines.
    """
    required = {x, y}
    for column in (size_column, label_column, group_column):
        if column:
            required.add(column)
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"bubble matrix data is missing required column(s): {', '.join(sorted(missing))}")
    frame = data.loc[:, list(required)].copy()
    frame[x] = pd.to_numeric(frame[x], errors="coerce")
    frame[y] = pd.to_numeric(frame[y], errors="coerce")
    frame = frame[np.isfinite(frame[x]) & np.isfinite(frame[y])]
    if frame.empty:
        raise ValueError("bubble_matrix requires at least one row with finite x and y values")
    areas = _bubble_areas(frame[size_column], 30, 260) if size_column else np.full(len(frame), 34.0)
    if quadrant_labels and (reference_x is None or reference_y is None):
        raise ValueError("quadrant_labels requires both reference_x and reference_y")

    fig, ax = new_figure(size)
    if group_column:
        groups = list(pd.unique(frame[group_column].astype(str)))
        if len(groups) > len(DATA_COLORS):
            raise ValueError(f"bubble_matrix supports at most {len(DATA_COLORS)} groups")
        for index, group in enumerate(groups):
            mask = frame[group_column].astype(str) == group
            ax.scatter(frame.loc[mask, x], frame.loc[mask, y], s=areas[mask.to_numpy()], color=DATA_COLORS[index],
                       alpha=0.72, linewidths=0.45, edgecolors=WHITE, label=group)
    else:
        ax.scatter(frame[x], frame[y], s=areas, color=PRIMARY, alpha=0.72, linewidths=0.45, edgecolors=WHITE)
    style_axes(ax, grid="both")
    if reference_x is not None:
        ax.axvline(reference_x, color=EVIDENCE, linewidth=0.85, linestyle="--", zorder=1)
    if reference_y is not None:
        ax.axhline(reference_y, color=EVIDENCE, linewidth=0.85, linestyle="--", zorder=1)
    if label_column:
        offsets = ((6, 6), (6, -10), (-6, 6), (-6, -10))
        for index, row in enumerate(frame.itertuples(index=False)):
            ax.annotate(str(getattr(row, label_column)), (getattr(row, x), getattr(row, y)),
                        xytext=offsets[index % len(offsets)], textcoords="offset points", fontsize=7.3,
                        ha="left" if offsets[index % len(offsets)][0] > 0 else "right",
                        va="bottom" if offsets[index % len(offsets)][1] > 0 else "top")
    if quadrant_labels:
        positions = {
            "upper-left": (0.02, 0.98, "left", "top"), "upper-right": (0.98, 0.98, "right", "top"),
            "lower-left": (0.02, 0.02, "left", "bottom"), "lower-right": (0.98, 0.02, "right", "bottom"),
        }
        for key, text in quadrant_labels.items():
            normalized = key.lower().replace("_", "-")
            if normalized not in positions:
                raise ValueError(f"unknown quadrant label '{key}'; use upper/lower-left/right")
            px, py, ha, va = positions[normalized]
            ax.text(px, py, str(text), transform=ax.transAxes, ha=ha, va=va, color=MUTED, fontsize=7.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _apply_formatter(ax.xaxis, x_formatter)
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    if group_column:
        legend_above(ax, ncol=min(len(groups), 3))
    return fig, ax


def _quarter_start(value: Any) -> pd.Timestamp:
    """Coerce a date or common YYYY-QN quarter label to a timestamp."""
    if isinstance(value, pd.Period):
        return value.asfreq("D", "start").to_timestamp()
    text = str(value).strip()
    match = re.fullmatch(r"(\d{4})\s*[- ]?Q([1-4])", text, flags=re.IGNORECASE)
    if match:
        return pd.Period(f"{match.group(1)}Q{match.group(2)}", freq="Q").start_time
    try:
        parsed = pd.to_datetime(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"timeline date '{value}' is not a valid date or quarter label") from exc
    if pd.isna(parsed):
        raise ValueError(f"timeline date '{value}' is not a valid date or quarter label")
    return pd.Timestamp(parsed)


def _timeline_boolean(value: Any) -> bool:
    """Parse an explicit milestone flag without treating arbitrary text as true."""
    if pd.isna(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0", ""}:
            return False
    raise ValueError(f"timeline milestone value '{value}' must be boolean")


def timeline_chart(
    tasks: pd.DataFrame | Sequence[Mapping[str, Any]],
    *,
    label_column: str = "label",
    start_column: str = "start",
    end_column: str = "end",
    workstream_column: str | None = "workstream",
    milestone_column: str | None = "milestone",
    current_date: Any | None = None,
    scale: str = "auto",
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Render a dated or quarterly planning timeline with bars and milestones.

    Each task needs a label and start.  Non-milestones also need an end date;
    dates may be normal pandas-compatible values or ``YYYY QN`` labels.
    Workstreams are shown in the row labels, so category colors are supportive
    rather than the sole carrier of meaning.
    """
    if scale not in {"auto", "date", "quarter"}:
        raise ValueError("timeline scale must be 'auto', 'date', or 'quarter'")
    frame = pd.DataFrame(tasks).copy()
    required = {label_column, start_column}
    if milestone_column is None:
        required.add(end_column)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"timeline data is missing required column(s): {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError("timeline_chart requires at least one task")
    if workstream_column and workstream_column not in frame:
        frame[workstream_column] = ""
    if milestone_column and milestone_column not in frame:
        frame[milestone_column] = False
    frame["_start"] = frame[start_column].map(_quarter_start)
    frame["_milestone"] = frame[milestone_column].map(_timeline_boolean) if milestone_column else False
    if end_column not in frame and (~frame["_milestone"]).any():
        raise ValueError(f"timeline data needs '{end_column}' for every non-milestone task")
    if end_column in frame:
        frame["_end"] = frame[end_column].where(frame[end_column].notna(), frame[start_column]).map(_quarter_start)
    else:
        frame["_end"] = frame["_start"]
    invalid_order = (~frame["_milestone"]) & (frame["_end"] < frame["_start"])
    if invalid_order.any():
        label = str(frame.loc[invalid_order, label_column].iloc[0])
        raise ValueError(f"timeline task '{label}' ends before it starts")
    if len(frame) > 30:
        raise ValueError("timeline_chart supports at most 30 tasks; split dense plans into separate figures")

    frame = frame.sort_values(["_start", label_column], kind="stable").reset_index(drop=True)
    streams = list(pd.unique(frame[workstream_column].fillna("").astype(str))) if workstream_column else [""]
    if len(streams) > len(DATA_COLORS):
        raise ValueError(f"timeline_chart supports at most {len(DATA_COLORS)} workstreams")
    stream_colors = {stream: DATA_COLORS[index] for index, stream in enumerate(streams)}
    fig, ax = new_figure(size)
    y = np.arange(len(frame))
    for index, row in frame.iterrows():
        stream = str(row[workstream_column]) if workstream_column else ""
        color = stream_colors[stream]
        if row["_milestone"]:
            ax.scatter(row["_start"], index, marker="D", s=42, color=color, edgecolors=WHITE, linewidths=0.65, zorder=3)
        else:
            duration = max((row["_end"] - row["_start"]).days, 1)
            ax.barh(index, duration, left=row["_start"], height=0.52, color=color, alpha=0.86)
    labels = [f"{row[workstream_column]} — {row[label_column]}" if workstream_column and str(row[workstream_column]).strip() else str(row[label_column]) for _, row in frame.iterrows()]
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    style_axes(ax, grid="x")
    if current_date is not None:
        marker = _quarter_start(current_date)
        ax.axvline(marker, color=RED_FLAG, linewidth=1.0, linestyle="--", zorder=2)
        ax.annotate("Today", (marker, 1), xycoords=("data", "axes fraction"), xytext=(3, -2), textcoords="offset points",
                    color=RED_FLAG, fontsize=7.4, ha="left", va="top")
    if scale == "quarter" or (scale == "auto" and all(re.fullmatch(r"\d{4}\s*[- ]?Q[1-4]", str(value).strip(), re.I) for value in frame[start_column])):
        locator = mdates.MonthLocator(bymonth=(1, 4, 7, 10))
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{mdates.num2date(value).year} Q{(mdates.num2date(value).month - 1) // 3 + 1}"))
    else:
        _format_datetime_axis(ax, pd.DatetimeIndex(frame["_start"].tolist() + frame["_end"].tolist()))
    ax.tick_params(axis="y", length=0)
    _title(ax, title)
    return fig, ax


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
def theme_file_for(theme: str, repo_root: str | Path | None = None) -> Path:
    """Resolve a theme name to its LaTeX file, e.g. "default" -> themes/reportkit-theme-default.sty.

    Since v1.6.0, ReportKit's palette lives in a theme file under
    latex_templates/themes/, not in reportkit.cls itself -- see
    docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md,
    open question 2.
    """
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    return root / "latex_templates" / "themes" / f"reportkit-theme-{theme}.sty"


def validate_palette_against_latex(class_path: str | Path) -> list[str]:
    """Return human-readable mismatches between Python and a ReportKit theme's LaTeX colors.

    Currently validates against the single, shared LATEX_THEME_COLORS dict --
    the default theme's Python-side palette. A per-theme Python token module
    (reportkit.themes.*) arrives with the visualization-integration step of
    the institutional-theme work; until then, checking a non-default theme
    here is expected to report mismatches rather than false-pass.
    """
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

    allocation = {
        "Public markets": {"Equities": 0.47, "Rates": 0.18, "Credit": 0.11},
        "Private markets": {"Buyout": 0.12, "Infrastructure": 0.07, "Real estate": 0.05},
    }
    fig, _ = treemap_chart(allocation, value_formatter="percent", title="Illustrative allocation")
    outputs += save_figure(fig, out_dir / "allocation_treemap")

    sensitivity = {"Revenue growth": (0.041, 0.069), "Margin": (0.047, 0.064), "Multiple": (0.039, 0.071)}
    fig, _ = tornado_chart(sensitivity, base_case=0.055, value_formatter="percent1", xlabel="Change in IRR")
    outputs += save_figure(fig, out_dir / "sensitivity_tornado")

    initiatives = pd.DataFrame(
        {
            "value": [0.81, 0.72, 0.43, 0.55], "effort": [0.62, 0.31, 0.44, 0.77],
            "investment": [8, 4, 3, 6], "initiative": ["Data platform", "Client portal", "Controls", "Automation"],
            "portfolio": ["Core", "Growth", "Core", "Growth"],
        }
    )
    fig, _ = bubble_matrix(
        initiatives, x="effort", y="value", xlabel="Implementation effort", ylabel="Expected value",
        size_column="investment", label_column="initiative", group_column="portfolio", reference_x=0.5, reference_y=0.5,
        quadrant_labels={"upper-right": "Strategic priorities", "upper-left": "Quick wins"},
    )
    outputs += save_figure(fig, out_dir / "initiative_matrix")

    plan = pd.DataFrame(
        {
            "label": ["Foundation", "Pilot", "Launch"], "start": ["2026 Q1", "2026 Q2", "2026 Q4"],
            "end": ["2026 Q2", "2026 Q4", None], "workstream": ["Platform", "Product", "Product"],
            "milestone": [False, False, True],
        }
    )
    fig, _ = timeline_chart(plan, current_date="2026 Q3", scale="quarter")
    outputs += save_figure(fig, out_dir / "delivery_timeline")

    return outputs


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
        mismatches = validate_palette_against_latex(class_path)
        if mismatches:
            for item in mismatches:
                print(item)
            raise SystemExit(1)
        print(f"ReportKit palette synchronized: {class_path}")


if __name__ == "__main__":
    _cli()
