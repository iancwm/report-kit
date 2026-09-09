#!/usr/bin/env python3
"""Generate analytical figures for the equity-research example, "Nexa Cloud
Solutions (NXCL): AI infrastructure demand holds up; services mix provides
an offset."

Every number here is drawn from the reconciled financial model documented
at the top of report.tex (open question 6 of
docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md
-- see that comment block for the full derivation, not repeated here).
This script uses only the public reportkit_viz API (apply_theme,
risk_reward_chart, timeseries, new_figure, style_axes, legend_above,
save_figure, the DATA_COLORS/formatter helpers) -- per new_figure()'s own
docstring, custom Matplotlib code built on those same helpers is the
intended path for a chart shape (the stacked platform-mix bar) that has no
dedicated ReportKit chart function yet, not a fork of the theme system.

Run from this directory with the repository's python_scripts/ on
sys.path, e.g.:

    PYTHONPATH=../../../python_scripts python3 figures.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import reportkit_viz as rkv

FIGURES = Path(__file__).resolve().parent / "figures"
FIGURES.mkdir(exist_ok=True)

rkv.apply_theme("institutional-research")

# -----------------------------------------------------------------------------
# Exhibit 1 -- usage index: illustrative launch-cohort engagement, indexed to
# 100 at launch. Not a reconciled financial figure (no $ tie-out needed) --
# purely a qualitative "usage holds up even as deployment cycles lengthen"
# shape, matching the spec's Appendix A reference visually.
# -----------------------------------------------------------------------------
weeks = [0, 3, 6, 9, 12, 15, 18, 21, 24]
usage_index = pd.DataFrame(
    {
        "FY23 launch": [58, 81, 71, 65, 66, 78, 62, 57, 55],
        "FY24 launch": [62, 96, 83, 71, 70, 87, 64, 59, 56],
        "FY25 launch": [55, 73, 66, 63, 62, 72, 60, 56, 54],
        "FY26 launch": [59, 87, 78, 68, 68, 82, 63, 58, 55],
    },
    index=weeks,
)
fig, ax = rkv.timeseries(
    usage_index,
    ylabel="Index (launch week = base)",
    xlabel="Weeks since launch",
    legend=True,
    size="full",
)
ax.set_ylim(40, 105)
rkv.save_figure(fig, FIGURES / "usage_index", formats=("pdf",))

# -----------------------------------------------------------------------------
# Exhibit 2 -- platform mix as a share of total revenue. Percentages are
# each fiscal year's Subscription/AI Orchestration/Services revenue over
# total revenue from the reconciled model (report.tex's reconciliation
# note): e.g. FY27E = 1,626 / 711 / 203 over 2,540 = 64% / 28% / 8%. No
# dedicated ReportKit "stacked_bar_chart" helper exists yet, so this
# composes new_figure/style_axes/legend_above/DATA_COLORS directly --
# exactly what new_figure()'s docstring calls "true small-multiple
# analysis": custom Matplotlib code on the same theme and export helpers,
# not a bespoke chart style forked away from the theme.
# -----------------------------------------------------------------------------
years = ["FY25A", "FY26E", "FY27E", "FY28E"]
subscription = [72, 68, 64, 61]
orchestration = [21, 25, 28, 30]
services = [7, 7, 8, 9]
assert [a + b + c for a, b, c in zip(subscription, orchestration, services)] == [100, 100, 100, 100]

fig, ax = rkv.new_figure("compact")
colors = rkv.DATA_COLORS
ax.bar(years, subscription, color=colors[0], width=0.6, label="Subscription")
ax.bar(years, orchestration, bottom=subscription, color=colors[1], width=0.6, label="AI Orchestration")
bottom_services = [a + b for a, b in zip(subscription, orchestration)]
ax.bar(years, services, bottom=bottom_services, color=colors[2], width=0.6, label="Services")
rkv.style_axes(ax, grid="y")
ax.set_ylim(0, 100)
ax.set_ylabel("Share of revenue")
ax.yaxis.set_major_formatter(rkv.percent_formatter(0, scale=1.0))
rkv.legend_above(ax, ncol=3)
rkv.save_figure(fig, FIGURES / "platform_mix", formats=("pdf",))

# -----------------------------------------------------------------------------
# Exhibit 3 -- gross margin, FY25A-FY28E, straight from the model's Gross
# Margin row (report.tex's reconciliation note / Exhibit 5).
# -----------------------------------------------------------------------------
gross_margin = pd.Series({"FY25A": 78.0, "FY26E": 79.0, "FY27E": 80.0, "FY28E": 80.5}, name="Gross margin")
fig, ax = rkv.timeseries(
    gross_margin,
    ylabel="Gross margin",
    y_formatter=rkv.percent_formatter(1, scale=1.0),
    legend=False,
    size="compact",
)
ax.set_ylim(76, 82)
rkv.save_figure(fig, FIGURES / "gross_margin", formats=("pdf",))

# -----------------------------------------------------------------------------
# Exhibit 5 (risk/reward, page 3) -- generated through risk_reward_chart(),
# spec section 18's preferred path (rather than a LaTeX-side
# \riskrewardchart macro). Bear/base/bull levels match report.tex's rating
# strip and Exhibit 7 (SOTP) price target exactly: base=$245 is the same
# published target as the front page and Exhibit 7's valuation table.
# -----------------------------------------------------------------------------
price_dates = pd.date_range("2024-09-30", "2026-08-31", freq="ME")
price_path = [
    128, 133, 136, 142, 150, 148, 152, 158, 162, 168, 171, 165,
    181, 176, 183, 189, 201, 195, 188, 179, 182, 186, 190, 182.5,
][: len(price_dates)]
price_history = pd.Series(price_path, index=price_dates, name="NXCL")
fig, ax = rkv.risk_reward_chart(
    price_history,
    bear=135,
    base=245,
    bull=310,
    current=182.50,
    value_formatter=rkv.currency_formatter(),
    ylabel="Share price ($)",
)
rkv.save_figure(fig, FIGURES / "risk_reward", formats=("pdf",))

# Business mix sidebar chart (per spec §29.3, proportional data in sidebar)
data = {
    "Consulting": 52,
    "Managed Services": 48,
}
fig, ax = rkv.donut_chart(data, size="sidebar")
rkv.save_figure(fig, FIGURES / "business_mix", formats=("pdf",))

print(f"wrote {len(list(FIGURES.glob('*.pdf')))} figures to {FIGURES}")
