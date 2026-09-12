"""Figure construction, axis styling, and export helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def new_figure(
    size: str | tuple[float, float] = "full",
    *,
    constrained: bool = True,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Create one ReportKit figure with a single axes."""
    from . import core

    figsize = core.FIGURE_SIZES[size] if isinstance(size, str) else size
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
    from . import core

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(core.HAIRLINE)
    ax.spines["bottom"].set_color(core.HAIRLINE)
    ax.tick_params(axis="both", colors=core.MUTED)

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
        ax.axhline(0, color=core.EVIDENCE, linewidth=0.8, zorder=1)
    if integer_x:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    if integer_y:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    return ax


def _title(ax: mpl.axes.Axes, title: str | None) -> None:
    """Use only when a chart must stand alone outside a ReportKit caption."""
    if title:
        from . import core

        ax.set_title(title, loc="left", color=core.INK, pad=9)


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
    """Return a color and line-style combination robust to grayscale."""
    from . import core

    if benchmark:
        return {"color": core.BENCHMARK, "linestyle": "--", "linewidth": 1.35}
    i = index % len(core.DATA_COLORS)
    return {
        "color": core.DATA_COLORS[i],
        "linestyle": core.LINE_STYLES[i % len(core.LINE_STYLES)],
        "marker": core.MARKERS[i % len(core.MARKERS)],
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
    """Save a figure in ReportKit-ready vector and raster formats."""
    stem = Path(stem)
    if stem.suffix:
        stem = stem.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for fmt in formats:
        fmt = fmt.lower().lstrip(".")
        path = stem.with_suffix(f".{fmt}")
        kwargs: dict[str, Any] = {"bbox_inches": "tight", "pad_inches": 0.04}
        if fmt in {"png", "jpg", "jpeg", "webp"}:
            kwargs["dpi"] = dpi
        if metadata is not None and fmt in {"pdf", "png", "svg"}:
            kwargs["metadata"] = dict(metadata)
        fig.savefig(path, **kwargs)
        outputs.append(path)
    if close:
        plt.close(fig)
    return outputs


__all__ = ["legend_above", "new_figure", "save_figure", "series_style", "style_axes"]
