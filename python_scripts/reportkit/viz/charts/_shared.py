"""Formatting helpers shared by more than one chart family.

Kept separate from any single chart module because both helpers back charts
in more than one file under ``reportkit.viz.charts``: ``_apply_formatter`` is
used by most of the module's charts, and ``_format_chart_value`` backs
``risk_reward_chart`` (in ``timeseries.py``) as well as ``treemap_chart`` and
``tornado_chart`` (in ``composition.py``).
"""
from __future__ import annotations

from matplotlib.ticker import FuncFormatter

from ..formatters import (
    bps_formatter, integer_formatter, multiple_formatter, number_formatter, percent_formatter,
)


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


__all__ = ["_apply_formatter", "_format_chart_value"]
