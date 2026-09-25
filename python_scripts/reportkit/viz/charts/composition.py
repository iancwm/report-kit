"""Part-of-a-whole, bridge, and scenario-spread chart constructors.

Grouped together as the charts that decompose a total into parts or a range:
a donut for proportional composition, a waterfall bridge, a hierarchical
treemap, and a tornado of low/high sensitivities. ``treemap_chart``'s
``_treemap_*`` helpers travel with it, matching how ``core.py`` kept them
adjacent before this split.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import matplotlib as mpl
from matplotlib import colors as mcolors
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from ..figure import _title, legend_above, new_figure, style_axes
from ._shared import _apply_formatter, _format_chart_value


# <reportkit-contract>
# {"kind":"chart","description":"Plot proportional data as a donut chart for sidebar embeds.","arguments":[{"name":"data","type":"data","description":"Data."},{"name":"title","type":"option","description":"Title."},{"name":"size","type":"option","description":"Size."},{"name":"colors","type":"option","description":"Colors."}],"constraints":[{"code":"slice_count","description":"Use two to four proportional slices.","min":2,"max":4}],"example":"fig, ax = rkv.donut_chart({\"Core\": 70, \"Other\": 30})","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
def donut_chart(
    data: dict[str, float],
    *,
    title: str | None = None,
    size: str | tuple[float, float] = "sidebar",
    colors: list[str] | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Plot proportional data as a donut chart for sidebar embeds.

    Renders 2–4 slices (segment split, geographic/channel mix, revenue
    composition) as a small square donut chart sized for the sidebar column
    (~2in). Per spec §29.3, reserve this for proportional compositions;
    use bar charts for other data shapes.

    Args:
        data: {label: value} dict of slice labels and their values
        title: optional chart title (typically None for sidebar charts)
        size: figure preset ("sidebar" default) or (width_in, height_in) tuple
        colors: list of hex colors for slices; cycles if fewer than slices.
                If None, uses theme data_colors.

    Returns:
        (fig, ax) for further styling or save_figure() integration
    """
    from .. import core

    if not data:
        raise ValueError("data must be non-empty")

    if colors is None:
        colors = list(core.DATA_COLORS)

    # Ensure enough colors for all slices
    colors_cycle = (colors * ((len(data) // len(colors)) + 1))[: len(data)]

    fig, ax = new_figure(size)

    labels = list(data.keys())
    values = list(data.values())

    # Draw donut (pie with hole) with theme styling
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors_cycle,
        autopct="%1.0f%%",
        startangle=90,
        textprops={"fontsize": 7.0},
        wedgeprops={"edgecolor": core.SURFACE, "linewidth": 1.2, "width": 0.4},
    )

    # Style percentage text inside slices
    for autotext in autotexts:
        autotext.set_color(core.SURFACE)
        autotext.set_fontsize(6.5)
        autotext.set_weight("bold")

    # Style slice labels
    for text in texts:
        text.set_fontsize(7.0)
        text.set_color(core.INK)

    ax.axis("off")
    _title(ax, title)
    return fig, ax


# <reportkit-contract>
# {"kind":"chart","description":"Render an opening-to-closing financial or operational bridge.","arguments":[{"name":"contributions","type":"data","description":"Contributions."},{"name":"opening","type":"option","description":"Opening."},{"name":"opening_label","type":"option","description":"Opening label."},{"name":"total_label","type":"option","description":"Total label."},{"name":"subtotals","type":"option","description":"Subtotals."},{"name":"closing_total","type":"option","description":"Closing total."},{"name":"value_formatter","type":"option","description":"Value formatter."},{"name":"ylabel","type":"option","description":"Ylabel."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.waterfall_chart({\"Growth\": 10, \"Costs\": -4})","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

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
            color = core.PRIMARY if height >= 0 else core.DATA_WARM
        elif kind == "subtotal":
            color = core.EVIDENCE
        else:
            color = core.INK
        ax.bar(i, height, bottom=bottom, color=color, width=0.62)

    # Connect only consecutive delta steps.  Totals deliberately break the
    # connector so arithmetic state remains readable without relying on color.
    previous_delta: int | None = 0
    running = float(opening)
    for i, (_, bottom, height, kind) in enumerate(bars[1:], start=1):
        if kind == "delta" and previous_delta is not None:
            ax.plot([previous_delta + 0.31, i - 0.31], [running, running], color=core.HAIRLINE, linewidth=0.8)
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


# <reportkit-contract>
# {"kind":"chart","description":"Draw a flat or nested, vector-native treemap.","arguments":[{"name":"data","type":"data","description":"Data."},{"name":"label_column","type":"option","description":"Label column."},{"name":"value_column","type":"option","description":"Value column."},{"name":"parent_column","type":"option","description":"Parent column."},{"name":"group_column","type":"option","description":"Group column."},{"name":"min_category_fraction","type":"option","description":"Min category fraction."},{"name":"min_label_fraction","type":"option","description":"Min label fraction."},{"name":"other_label","type":"option","description":"Other label."},{"name":"value_formatter","type":"option","description":"Value formatter."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.treemap_chart({\"A\": 60, \"B\": 40})","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

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
    top_colors = {label: core.DATA_COLORS[index % len(core.DATA_COLORS)] for index, label in enumerate(tree)}

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
                    ax.text(rx + 1.1, ry + rh - 1.3, label, va="top", ha="left", color=core.INK, fontsize=7.7,
                            fontweight="semibold", clip_on=True)
            else:
                ax.add_patch(mpl.patches.Rectangle((rx, ry), rw, rh, facecolor=mcolors.to_rgba(color, 0.84 if depth == 0 else 0.60), edgecolor=core.WHITE, linewidth=0.8))
                fraction = float(node) / total
                if fraction >= min_label_fraction:
                    label_text = f"{label}\n{_format_chart_value(float(node), value_formatter)}"
                    ax.text(rx + rw / 2, ry + rh / 2, label_text, ha="center", va="center", color=core.WHITE,
                            fontsize=7.4, linespacing=1.22, clip_on=True)

    draw_level(tree, (0, 0, 100, 100), 0, None)
    _title(ax, title)
    return fig, ax


# <reportkit-contract>
# {"kind":"chart","description":"Draw ordered low/high sensitivity bars around a labelled base case.","arguments":[{"name":"sensitivities","type":"data","description":"Sensitivities."},{"name":"base_case","type":"option","description":"Base case."},{"name":"low_column","type":"option","description":"Low column."},{"name":"high_column","type":"option","description":"High column."},{"name":"label_column","type":"option","description":"Label column."},{"name":"value_formatter","type":"option","description":"Value formatter."},{"name":"xlabel","type":"option","description":"Xlabel."},{"name":"size","type":"option","description":"Size."},{"name":"title","type":"option","description":"Title."}],"constraints":[],"example":"fig, ax = rkv.tornado_chart({\"Price\": (-10, 15), \"Volume\": (-5, 8)})","stability":"stable","since":"1.0.0"}
# </reportkit-contract>
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
    from .. import core

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
    ax.barh(y, low_delta, color=core.DATA_WARM, height=0.62, label="Low case")
    ax.barh(y, high_delta, color=core.PRIMARY, height=0.62, label="High case")
    ax.axvline(0, color=core.INK, linewidth=0.9, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(frame["label"])
    style_axes(ax, grid="x")
    _apply_formatter(ax.xaxis, value_formatter)
    ax.set_xlabel(xlabel or f"Change from base case ({_format_chart_value(float(base_case), value_formatter)})")
    _title(ax, title)
    legend_above(ax, ncol=2)
    return fig, ax


__all__ = ["donut_chart", "waterfall_chart", "treemap_chart", "tornado_chart"]
