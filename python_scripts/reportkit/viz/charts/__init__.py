"""Chart constructors exposed as a small concern-specific namespace.

Implementations are split across ``timeseries.py`` (date-indexed charts),
``relationships.py`` (comparative/statistical charts), and ``composition.py``
(part-of-a-whole and scenario-spread charts); ``_shared.py`` holds formatting
helpers used by more than one of those files. See each module's docstring for
its grouping rationale.
"""
from .composition import donut_chart, tornado_chart, treemap_chart, waterfall_chart
from .relationships import bar_chart, bubble_matrix, distribution, heatmap, scatter_plot
from .timeseries import drawdown_chart, risk_reward_chart, timeline_chart, timeseries

__all__ = [
    "bar_chart", "bubble_matrix", "distribution", "donut_chart", "drawdown_chart", "heatmap",
    "risk_reward_chart", "scatter_plot", "timeline_chart", "timeseries", "tornado_chart",
    "treemap_chart", "waterfall_chart",
]
