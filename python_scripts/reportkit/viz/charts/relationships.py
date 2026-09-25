"""Comparative and statistical chart constructors.

Grouped together as the charts that compare values across categories or
variables (bars, distributions, scatter, a correlation/scenario heatmap, and
a size-encoded scatter/bubble matrix), as opposed to the date-indexed charts
in ``timeseries.py`` or the part-of-a-whole charts in ``composition.py``.
``heatmap``'s private colormap builders and ``bubble_matrix``'s
``_bubble_areas`` travel with the one chart each backs.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import matplotlib as mpl
from matplotlib import colors as mcolors
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from ..figure import _title, legend_above, new_figure, style_axes
from ._shared import _apply_formatter


# <reportkit-contract>
# {"kind":"chart","description":"Clean categorical bar chart, useful for exposures and decompositions.","arguments":[{"name":"data","type":"data","description":"Data."},{"name":"horizontal","type":"option","description":"Horizontal."},{"name":"highlight","type":"option","description":"Highlight."},{"name":"value_formatter","type":"option","description":"Value formatter."},{"name":"axis_label","type":"option","description":"Axis label."},{"name":"sort","type":"option","description":"Sort."},{"name":"zero_line","type":"option","description":"Zero line."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.bar_chart({\"A\": 2, \"B\": 1})","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

    s = pd.Series(data, dtype=float)
    if sort:
        s = s.sort_values()
    highlights = {highlight} if isinstance(highlight, str) else set(highlight or [])
    colors = [core.PRIMARY if (not highlights or str(idx) in highlights) else "#A8B1BA" for idx in s.index]

    fig, ax = new_figure(size)
    if horizontal:
        ax.barh([str(x) for x in s.index], s.values, color=colors, height=0.62)
        ax.invert_yaxis()
        style_axes(ax, grid="x")
        if zero_line:
            ax.axvline(0, color=core.EVIDENCE, linewidth=0.8, zorder=1)
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


# <reportkit-contract>
# {"kind":"chart","description":"Histogram without decorative KDE assumptions.","arguments":[{"name":"values","type":"data","description":"Values."},{"name":"bins","type":"option","description":"Bins."},{"name":"xlabel","type":"option","description":"Xlabel."},{"name":"x_formatter","type":"option","description":"X formatter."},{"name":"reference","type":"option","description":"Reference."},{"name":"density","type":"option","description":"Density."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.distribution([1, 2, 2, 3])","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

    x = np.asarray(pd.Series(values).dropna(), dtype=float)
    fig, ax = new_figure(size)
    ax.hist(x, bins=bins, density=density, color=core.PRIMARY, alpha=0.88, edgecolor=core.WHITE, linewidth=0.55)
    style_axes(ax, grid="y")
    if reference is not None:
        ax.axvline(reference, color=core.DECISION, linewidth=1.35, linestyle="--")
    ax.set_xlabel(xlabel or "")
    ax.set_ylabel("Density" if density else "Count")
    _apply_formatter(ax.xaxis, x_formatter)
    _title(ax, title)
    return fig, ax


# <reportkit-contract>
# {"kind":"chart","description":"Scatter plot with optional first-order fit for diagnostics.","arguments":[{"name":"x","type":"data","description":"X."},{"name":"y","type":"option","description":"Y."},{"name":"xlabel","type":"option","description":"Xlabel."},{"name":"ylabel","type":"option","description":"Ylabel."},{"name":"fit_line","type":"option","description":"Fit line."},{"name":"x_formatter","type":"option","description":"X formatter."},{"name":"y_formatter","type":"option","description":"Y formatter."},{"name":"reference_x","type":"option","description":"Reference x."},{"name":"reference_y","type":"option","description":"Reference y."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.scatter_plot([1, 2], [2, 3], xlabel=\"X\", ylabel=\"Y\")","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

    xy = pd.DataFrame({"x": x, "y": y}).dropna()
    fig, ax = new_figure(size)
    ax.scatter(xy["x"], xy["y"], s=24, color=core.PRIMARY, alpha=0.68, linewidths=0)
    style_axes(ax, grid="both")

    if fit_line and len(xy) >= 2:
        coeff = np.polyfit(xy["x"].to_numpy(), xy["y"].to_numpy(), 1)
        xx = np.linspace(float(xy["x"].min()), float(xy["x"].max()), 100)
        ax.plot(xx, coeff[0] * xx + coeff[1], color=core.DECISION, linewidth=1.3, linestyle="--", label="Linear fit")
        legend_above(ax, ncol=1)
    if reference_x is not None:
        ax.axvline(reference_x, color=core.HAIRLINE, linewidth=0.9)
    if reference_y is not None:
        ax.axhline(reference_y, color=core.HAIRLINE, linewidth=0.9)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _apply_formatter(ax.xaxis, x_formatter)
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    return fig, ax


def _sequential_cmap() -> mpl.colors.Colormap:
    from .. import core

    return mcolors.LinearSegmentedColormap.from_list(
        "reportkit_sequential", ["#F7F8FA", "#BCCBD3", "#6F91A4", core.PRIMARY]
    )


def _diverging_cmap() -> mpl.colors.Colormap:
    from .. import core

    return mcolors.LinearSegmentedColormap.from_list(
        "reportkit_diverging", [core.DATA_WARM, "#E5DAD5", "#FAFAFA", "#D7E2E7", core.PRIMARY]
    )


# <reportkit-contract>
# {"kind":"chart","description":"Sequential or diverging heatmap for correlations and scenario matrices.","arguments":[{"name":"matrix","type":"data","description":"Matrix."},{"name":"row_labels","type":"option","description":"Row labels."},{"name":"col_labels","type":"option","description":"Col labels."},{"name":"center","type":"option","description":"Center."},{"name":"vmin","type":"option","description":"Vmin."},{"name":"vmax","type":"option","description":"Vmax."},{"name":"annotate","type":"option","description":"Annotate."},{"name":"annotation_format","type":"option","description":"Annotation format."},{"name":"cbar_label","type":"option","description":"Cbar label."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.heatmap([[1, 2], [3, 4]])","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

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
                text_color = core.WHITE if luminance < 0.52 else core.INK
                ax.text(j, i, format(val, annotation_format), ha="center", va="center", color=text_color, fontsize=7.3)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.035)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors=core.MUTED, labelsize=7.8, width=0.5, length=2.5)
    if cbar_label:
        cbar.set_label(cbar_label, color=core.INK, size=8.2)
    _title(ax, title)
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


# <reportkit-contract>
# {"kind":"chart","description":"DataFrame-oriented scatter/bubble matrix with optional quadrants.","arguments":[{"name":"data","type":"data","description":"Data."},{"name":"x","type":"option","description":"X."},{"name":"y","type":"option","description":"Y."},{"name":"xlabel","type":"option","description":"Xlabel."},{"name":"ylabel","type":"option","description":"Ylabel."},{"name":"size_column","type":"option","description":"Size column."},{"name":"label_column","type":"option","description":"Label column."},{"name":"group_column","type":"option","description":"Group column."},{"name":"reference_x","type":"option","description":"Reference x."},{"name":"reference_y","type":"option","description":"Reference y."},{"name":"quadrant_labels","type":"option","description":"Quadrant labels."},{"name":"x_formatter","type":"option","description":"X formatter."},{"name":"y_formatter","type":"option","description":"Y formatter."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"data = pd.DataFrame({\"x\":[1],\"y\":[2]}); fig, ax = rkv.bubble_matrix(data, x=\"x\", y=\"y\", xlabel=\"X\", ylabel=\"Y\")","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

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
        if len(groups) > len(core.DATA_COLORS):
            raise ValueError(f"bubble_matrix supports at most {len(core.DATA_COLORS)} groups")
        for index, group in enumerate(groups):
            mask = frame[group_column].astype(str) == group
            ax.scatter(frame.loc[mask, x], frame.loc[mask, y], s=areas[mask.to_numpy()], color=core.DATA_COLORS[index],
                       marker=core.BUBBLE_MARKERS[index % len(core.BUBBLE_MARKERS)], alpha=0.72, linewidths=0.45,
                       edgecolors=core.WHITE, label=group)
    else:
        ax.scatter(frame[x], frame[y], s=areas, color=core.PRIMARY, alpha=0.72, linewidths=0.45, edgecolors=core.WHITE)
    style_axes(ax, grid="both")
    if reference_x is not None:
        ax.axvline(reference_x, color=core.EVIDENCE, linewidth=0.85, linestyle="--", zorder=1)
    if reference_y is not None:
        ax.axhline(reference_y, color=core.EVIDENCE, linewidth=0.85, linestyle="--", zorder=1)
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
            ax.text(px, py, str(text), transform=ax.transAxes, ha=ha, va=va, color=core.MUTED, fontsize=7.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _apply_formatter(ax.xaxis, x_formatter)
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    if group_column:
        legend_above(ax, ncol=min(len(groups), 3))
    return fig, ax


__all__ = ["bar_chart", "distribution", "scatter_plot", "heatmap", "bubble_matrix"]
