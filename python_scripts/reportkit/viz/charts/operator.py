"""Stacked and numeric-index chart constructors for operator reports."""
from __future__ import annotations

from collections.abc import Mapping
import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from ..figure import _title, legend_above, new_figure, style_axes
from ._shared import _apply_formatter


# <reportkit-contract>
# {"kind":"chart","description":"Render categorical data as stacked bars with per-series hatch encodings.","arguments":[{"name":"data","type":"data","description":"Rows are categories and columns are stacked series."},{"name":"horizontal","type":"option","description":"Render horizontal bars when true."},{"name":"value_formatter","type":"option","description":"Formatter for the value axis."},{"name":"axis_label","type":"option","description":"Label for the value axis."},{"name":"sort","type":"option","description":"Sort categories by their total before plotting."},{"name":"size","type":"option","description":"Named figure size or explicit dimensions."},{"name":"title","type":"option","description":"Optional chart title."}],"constraints":[],"example":"fig, ax = rkv.stacked_bar_chart(costs, value_formatter=\"currency\")","stability":"experimental","since":"1.10.0"}
# </reportkit-contract>
def stacked_bar_chart(
    data: pd.DataFrame | Mapping[str, Mapping[str, float]],
    *,
    horizontal: bool = False,
    value_formatter: FuncFormatter | str | None = None,
    axis_label: str | None = None,
    sort: bool = False,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Render categorical data as stacked bars with theme hatch encodings.

    DataFrame rows are categories and columns are segments; columns are drawn
    bottom to top in their existing order. A mapping uses the equivalent
    ``{category: {segment: value}}`` shape.
    """
    from .. import core

    if isinstance(data, pd.DataFrame):
        frame = data.copy()
    else:
        frame = pd.DataFrame.from_dict(data, orient="index")
    if frame.empty or frame.shape[1] == 0:
        raise ValueError("stacked_bar_chart requires at least one category and one segment")
    try:
        frame = frame.astype(float).fillna(0.0)
    except (TypeError, ValueError) as exc:
        raise ValueError("stacked_bar_chart values must be numeric") from exc
    values = frame.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("stacked_bar_chart values must all be finite")
    if sort:
        order = np.argsort(values.sum(axis=1), kind="stable")
        frame = frame.iloc[order]
        values = values[order]

    if not frame.columns.is_unique:
        raise ValueError("stacked_bar_chart segment names must be unique")
    categories = [str(value) for value in frame.index]
    segment_names = [str(value) for value in frame.columns]
    positions = np.arange(len(frame))
    positive_bottom = np.zeros(len(frame), dtype=float)
    negative_bottom = np.zeros(len(frame), dtype=float)
    fig, ax = new_figure(size)
    hatches = core.CHART_HATCHES
    for index, (column, label) in enumerate(zip(frame.columns, segment_names)):
        segment = frame[column].to_numpy(dtype=float)
        hatch = hatches[index % len(hatches)] if hatches else ""
        if hatch:
            facecolor = core.SURFACE
            edgecolor = core.MUTED
            linewidth = 0.7
        else:
            # The operator theme's solid inference layer uses its indigo
            # accent; themes without hatches retain their ordinary data-color
            # rotation for multi-segment stacks.
            facecolor = (
                core.PRIMARY
                if hatches
                else core.DATA_COLORS[index % len(core.DATA_COLORS)]
            )
            edgecolor = core.WHITE
            linewidth = 0.55
        style = {
            "color": facecolor,
            "edgecolor": edgecolor,
            "linewidth": linewidth,
            "label": label,
        }
        if hatch:
            style["hatch"] = hatch

        bottom = np.where(segment >= 0, positive_bottom, negative_bottom)
        if horizontal:
            ax.barh(positions, segment, left=bottom, height=0.62, **style)
        else:
            ax.bar(positions, segment, bottom=bottom, width=0.62, **style)
        positive_bottom += np.clip(segment, 0.0, None)
        negative_bottom += np.clip(segment, None, 0.0)

    if horizontal:
        ax.set_yticks(positions)
        ax.set_yticklabels(categories)
        ax.invert_yaxis()
        style_axes(ax, grid="x")
        _apply_formatter(ax.xaxis, value_formatter)
        ax.set_xlabel(axis_label or "")
        ax.set_ylabel("")
    else:
        ax.set_xticks(positions)
        ax.set_xticklabels(categories, rotation=0)
        style_axes(ax, grid="y")
        _apply_formatter(ax.yaxis, value_formatter)
        ax.set_ylabel(axis_label or "")
        ax.set_xlabel("")

    low = min(float(negative_bottom.min()), 0.0)
    high = max(float(positive_bottom.max()), 0.0)
    span = high - low
    if span <= 0.0:
        span = 1.0
    padding = span * 0.07
    if horizontal:
        ax.set_xlim(low - padding, high + padding)
    else:
        ax.set_ylim(low - padding, high + padding)
    if frame.shape[1] > 1:
        legend_above(ax, ncol=min(frame.shape[1], 3))
    _title(ax, title)
    return fig, ax


# <reportkit-contract>
# {"kind":"chart","description":"Plot one or more series against a numeric x axis, with an optional labelled vertical marker.","arguments":[{"name":"data","type":"data","description":"Series or frame indexed by numeric x values."},{"name":"xlabel","type":"option","description":"Label for the numeric x axis."},{"name":"ylabel","type":"option","description":"Label for the y axis."},{"name":"x_formatter","type":"option","description":"Formatter for numeric x values."},{"name":"y_formatter","type":"option","description":"Formatter for y values."},{"name":"vertical_marker","type":"option","description":"Optional numeric x coordinate for a vertical reference marker."},{"name":"vertical_marker_label","type":"option","description":"Label displayed beside the vertical reference marker."},{"name":"legend","type":"option","description":"Show the series legend when there are multiple series."},{"name":"size","type":"option","description":"Named figure size or explicit dimensions."},{"name":"title","type":"option","description":"Optional chart title."}],"constraints":[],"example":"fig, ax = rkv.line_chart(costs, vertical_marker=64, vertical_marker_label=\"Credit cap\")","stability":"experimental","since":"1.10.0"}
# </reportkit-contract>
def line_chart(
    data: pd.Series | pd.DataFrame,
    *,
    xlabel: str | None = None,
    ylabel: str | None = None,
    x_formatter: FuncFormatter | str | None = None,
    y_formatter: FuncFormatter | str | None = None,
    vertical_marker: float | None = None,
    vertical_marker_label: str | None = None,
    legend: bool = True,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot series against a numeric index and optionally mark a threshold."""
    from .. import core

    if isinstance(data, pd.Series):
        frame = data.to_frame(data.name or "Series")
    else:
        frame = data
    if frame.empty or frame.shape[1] == 0:
        raise ValueError("line_chart requires at least one indexed point and one series")
    if not pd.api.types.is_numeric_dtype(frame.index.dtype):
        raise ValueError("line_chart requires a numeric data index")
    x_values = frame.index.to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(x_values).all():
        raise ValueError("line_chart numeric x values must all be finite")
    try:
        frame = frame.apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("line_chart series values must be numeric") from exc
    if np.isinf(frame.to_numpy(dtype=float, na_value=np.nan)).any():
        raise ValueError("line_chart series values must not be infinite")
    if frame.shape[1] > 6:
        raise ValueError("line_chart supports at most six series")
    if vertical_marker is not None:
        try:
            vertical_marker = float(vertical_marker)
        except (TypeError, ValueError) as exc:
            raise ValueError("line_chart vertical_marker must be numeric") from exc
        if not np.isfinite(vertical_marker):
            raise ValueError("line_chart vertical_marker must be finite")
    if vertical_marker_label is not None and vertical_marker is None:
        raise ValueError("vertical_marker_label requires vertical_marker")

    fig, ax = new_figure(size)
    dashes = core.CHART_DASHES or core.LINE_STYLES
    semantic_colors = (core.INK, core.MUTED, core.PRIMARY)
    for index, column in enumerate(frame.columns):
        color = (
            semantic_colors[index]
            if index < len(semantic_colors)
            else core.DATA_COLORS[(index - len(semantic_colors)) % len(core.DATA_COLORS)]
        )
        ax.plot(
            frame.index,
            frame[column],
            label=str(column),
            color=color,
            linestyle=dashes[index % len(dashes)],
            linewidth=1.75 if index == 0 else 1.5,
        )
    style_axes(ax, grid="y")
    ax.set_xlabel(xlabel or "")
    ax.set_ylabel(ylabel or "")
    _apply_formatter(ax.xaxis, x_formatter)
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    if legend and frame.shape[1] > 1:
        legend_above(ax)
    if vertical_marker is not None:
        ax.axvline(
            vertical_marker,
            color=core.MUTED,
            linestyle=":",
            linewidth=0.9,
            zorder=1,
        )
        if vertical_marker_label:
            ax.annotate(
                vertical_marker_label,
                xy=(vertical_marker, 1.0),
                xycoords=("data", "axes fraction"),
                xytext=(4, -3),
                textcoords="offset points",
                rotation=90,
                ha="left",
                va="top",
                color=core.MUTED,
                fontsize=7.5,
                annotation_clip=False,
            )
    return fig, ax
