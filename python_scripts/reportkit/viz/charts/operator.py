"""Operator-theme chart API reserved for Lane F's implementation."""
from __future__ import annotations

from collections.abc import Mapping
import matplotlib as mpl
import pandas as pd
from matplotlib.ticker import FuncFormatter


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
    """Render categorical data as stacked bars with per-series hatch encodings."""
    raise NotImplementedError("stacked_bar_chart implementation belongs to Lane F")


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
    """Plot one or more numeric-x series with an optional labelled marker."""
    raise NotImplementedError("line_chart implementation belongs to Lane F")
