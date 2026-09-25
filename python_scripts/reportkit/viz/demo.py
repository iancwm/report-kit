"""Deterministic sample figures used for visual regression QA.

Separated from ``core.py`` because ``build_demo`` is a demo/QA driver that
calls the public chart API, not a chart implementation itself.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from reportkit.context import month_end_freq
from .charts import (
    bar_chart, bubble_matrix, distribution, drawdown_chart, heatmap, risk_reward_chart,
    scatter_plot, timeline_chart, timeseries, tornado_chart, treemap_chart, waterfall_chart,
)
from .figure import save_figure
from .formatters import currency_formatter, number_formatter, percent_formatter


def build_demo(out_dir: str | Path) -> list[Path]:
    """Generate deterministic sample finance figures for visual regression QA."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    rng = np.random.default_rng(14)
    dates = pd.date_range("2022-01-31", periods=44, freq=month_end_freq())
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

    price = 182.50 * wealth / wealth.iloc[-1]
    fig, _ = risk_reward_chart(
        price, bear=135, base=245, bull=310, current=182.50,
        value_formatter=currency_formatter(),
    )
    outputs += save_figure(fig, out_dir / "risk_reward")

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


__all__ = ["build_demo"]
