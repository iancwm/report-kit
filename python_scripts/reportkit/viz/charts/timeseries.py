"""Date- and quarter-indexed chart constructors.

Grouped together because each one formats a date-like axis: ``timeseries``,
``drawdown_chart``, and ``risk_reward_chart`` share ``_format_datetime_axis``;
``timeline_chart`` is quarter- or date-aware through its own
``_quarter_start``/``_timeline_boolean`` helpers, which travel with it here
for the same reason ``core.py`` kept ``_treemap_*`` beside ``treemap_chart``.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import matplotlib as mpl
from matplotlib import dates as mdates
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from ..figure import _title, legend_above, new_figure, series_style, style_axes
from ._shared import _apply_formatter, _format_chart_value


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


# <reportkit-contract>
# {"kind":"chart","description":"Plot one to six time series with ReportKit line semantics.","arguments":[{"name":"data","type":"data","description":"Data."},{"name":"ylabel","type":"option","description":"Ylabel."},{"name":"xlabel","type":"option","description":"Xlabel."},{"name":"y_formatter","type":"option","description":"Y formatter."},{"name":"benchmark","type":"option","description":"Benchmark."},{"name":"reference_line","type":"option","description":"Reference line."},{"name":"legend","type":"option","description":"Legend."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"data = pd.Series([1, 2, 3]); fig, ax = rkv.timeseries(data)","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

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
        ax.axhline(reference_line, color=core.HAIRLINE, linewidth=0.9, zorder=0)
    ax.set_ylabel(ylabel or "")
    ax.set_xlabel(xlabel or "")
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    if legend and data.shape[1] > 1:
        legend_above(ax)
    return fig, ax


# <reportkit-contract>
# {"kind":"chart","description":"Plot a precomputed drawdown series as a restrained filled area.","arguments":[{"name":"drawdown","type":"data","description":"Drawdown."},{"name":"ylabel","type":"option","description":"Ylabel."},{"name":"y_formatter","type":"option","description":"Y formatter."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.drawdown_chart(pd.Series([0, -0.1, -0.05]))","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
def drawdown_chart(
    drawdown: pd.Series,
    *,
    ylabel: str = "Drawdown",
    y_formatter: FuncFormatter | str | None = "percent",
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot a precomputed drawdown series as a restrained filled area."""
    from .. import core

    s = pd.Series(drawdown).dropna()
    fig, ax = new_figure(size)
    ax.fill_between(s.index, s.values, 0, color=core.PRIMARY, alpha=0.17, linewidth=0)
    ax.plot(s.index, s.values, color=core.PRIMARY, linewidth=1.35)
    style_axes(ax, grid="y")
    _format_datetime_axis(ax, s.index)
    ax.axhline(0, color=core.HAIRLINE, linewidth=0.9)
    ax.set_ylabel(ylabel)
    _apply_formatter(ax.yaxis, y_formatter)
    _title(ax, title)
    return fig, ax


# <reportkit-contract>
# {"kind":"chart","description":"Plot a price history with bear/base/bull reference levels.","arguments":[{"name":"price_history","type":"data","description":"Price history."},{"name":"bear","type":"option","description":"Bear."},{"name":"base","type":"option","description":"Base."},{"name":"bull","type":"option","description":"Bull."},{"name":"current","type":"option","description":"Current."},{"name":"bear_label","type":"option","description":"Bear label."},{"name":"base_label","type":"option","description":"Base label."},{"name":"bull_label","type":"option","description":"Bull label."},{"name":"value_formatter","type":"option","description":"Value formatter."},{"name":"ylabel","type":"option","description":"Ylabel."},{"name":"xlabel","type":"option","description":"Xlabel."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"prices = pd.Series([90, 100]); fig, ax = rkv.risk_reward_chart(prices, bear=80, base=110, bull=140)","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
def risk_reward_chart(
    price_history: pd.Series,
    *,
    bear: float,
    base: float,
    bull: float,
    current: float | None = None,
    bear_label: str = "Bear",
    base_label: str = "Base",
    bull_label: str = "Bull",
    value_formatter: FuncFormatter | str | None = None,
    ylabel: str = "Share price ($)",
    xlabel: str | None = None,
    size: str | tuple[float, float] = "full",
    title: str | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot a price history with bear/base/bull reference levels.

    This is the risk/reward primitive spec §18 asks for, generated "through
    reportkit_viz.py" as that section itself prefers, rather than as a
    LaTeX-side `\\riskrewardchart` macro drawn in raw TikZ/pgfplots --
    `reportkit-equity-research.sty`'s own risk/reward primitives
    (`\\bullcase`/`\\basecase`/`\\bearcase`) intentionally stop at the page's
    surrounding text and expect the chart itself, via this function, to
    arrive as an ordinary `\\includegraphics` inside an `exhibit`. Matches
    Appendix A's risk/reward exhibit: a historical price line with three
    horizontal dashed levels, each labeled with its case name and value at
    the right edge; `current`, if given, marks the series' most recent
    point (useful when it differs slightly from `price_history`'s own last
    value, e.g. an intraday quote newer than the daily series).

    Colors reuse each theme's existing negative/warm/accent roles
    (DATA_NEGATIVE/DATA_WARM/METRIC) rather than adding bear/base/bull-
    specific theme fields -- see
    `reportkit.themes.institutional_research`'s module docstring for why
    those three already line up with Appendix A's actual bear=red/
    bull=gold/base=teal convention for that theme.
    """
    from .. import core

    s = pd.Series(price_history).dropna()
    fig, ax = new_figure(size)
    ax.plot(s.index, s.values, color=core.PRIMARY, linewidth=1.5, zorder=3)
    if current is not None:
        ax.scatter([s.index[-1]], [current], color=core.PRIMARY, s=26, zorder=4)

    for label, value, color in (
        (bear_label, bear, core.DATA_NEGATIVE),
        (base_label, base, core.METRIC),
        (bull_label, bull, core.DATA_WARM),
    ):
        ax.axhline(value, color=color, linewidth=1.1, linestyle="--", zorder=2)
        ax.annotate(
            f"{label} {_format_chart_value(value, value_formatter)}",
            xy=(s.index[-1], value),
            # Offset up and to the right of the line's own value, not
            # centered on it (va="center" would sit the text baseline
            # directly on the dashed rule, so the rule visually strikes
            # through the label -- found by actually rendering this
            # fixture's risk/reward exhibit in Step 5, matching how
            # Appendix A's own pgfplots \node placed its bear/base/bull
            # labels 2 units above the reference line rather than on it).
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=7.6,
            color=color,
            va="bottom",
            ha="left",
        )

    style_axes(ax, grid="y")
    _format_datetime_axis(ax, s.index)
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _apply_formatter(ax.yaxis, value_formatter)
    _title(ax, title)
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


# <reportkit-contract>
# {"kind":"chart","description":"Render a dated or quarterly planning timeline with bars and milestones.","arguments":[{"name":"tasks","type":"data","description":"Tasks."},{"name":"label_column","type":"option","description":"Label column."},{"name":"start_column","type":"option","description":"Start column."},{"name":"end_column","type":"option","description":"End column."},{"name":"workstream_column","type":"option","description":"Workstream column."},{"name":"milestone_column","type":"option","description":"Milestone column."},{"name":"current_date","type":"option","description":"Current date."},{"name":"scale","type":"option","description":"Scale."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[{"code":"max_tasks","description":"A timeline supports at most 30 tasks.","value":30}],"example":"fig, ax = rkv.timeline_chart([{\"label\":\"Build\",\"start\":\"2026 Q1\",\"end\":\"2026 Q2\"}])","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

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
    if len(streams) > len(core.DATA_COLORS):
        raise ValueError(f"timeline_chart supports at most {len(core.DATA_COLORS)} workstreams")
    stream_colors = {stream: core.DATA_COLORS[index] for index, stream in enumerate(streams)}
    fig, ax = new_figure(size)
    y = np.arange(len(frame))
    for index, row in frame.iterrows():
        stream = str(row[workstream_column]) if workstream_column else ""
        color = stream_colors[stream]
        if row["_milestone"]:
            ax.scatter(row["_start"], index, marker="D", s=42, color=color, edgecolors=core.WHITE, linewidths=0.65, zorder=3)
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
        ax.axvline(marker, color=core.RED_FLAG, linewidth=1.0, linestyle="--", zorder=2)
        ax.annotate("Today", (marker, 1), xycoords=("data", "axes fraction"), xytext=(3, -2), textcoords="offset points",
                    color=core.RED_FLAG, fontsize=7.4, ha="left", va="top")
    if scale == "quarter" or (scale == "auto" and all(re.fullmatch(r"\d{4}\s*[- ]?Q[1-4]", str(value).strip(), re.I) for value in frame[start_column])):
        locator = mdates.MonthLocator(bymonth=(1, 4, 7, 10))
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{mdates.num2date(value).year} Q{(mdates.num2date(value).month - 1) // 3 + 1}"))
    else:
        _format_datetime_axis(ax, pd.DatetimeIndex(frame["_start"].tolist() + frame["_end"].tolist()))
    ax.tick_params(axis="y", length=0)
    _title(ax, title)
    return fig, ax


__all__ = ["timeseries", "drawdown_chart", "risk_reward_chart", "timeline_chart"]
