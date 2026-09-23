#!/usr/bin/env python3
"""Generate the visuals for the editorial feature fixture, "The river that
learned to count".

Everything here is fictional: Varenholm, its delta, its gauge network and
every number are invented for this example. The script uses only the public
reportkit_viz API (apply_theme, new_figure, timeseries, bar_chart,
style_axes, save_figure and the theme color globals), so the charts inherit
the editorial palette and Libertinus Sans chart text rather than local
styling.

Run from the repository root, e.g.:

    PYTHONPATH=python_scripts python3 latex_templates/examples/editorial-feature/figures.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import reportkit_viz as rkv

FIGURES = Path(__file__).resolve().parent / "figures"
FIGURES.mkdir(exist_ok=True)

rkv.apply_theme("editorial")


def _save(fig, name: str) -> None:
    # PDF only: the fixture includes vector figures; SOURCE_DATE_EPOCH keeps
    # Matplotlib's PDF metadata deterministic when the caller sets it.
    rkv.save_figure(fig, FIGURES / name, formats=("pdf",), metadata={"Creator": "ReportKit editorial fixture"})


# -----------------------------------------------------------------------------
# Opening visual -- an abstract survey drawing of the delta: braided channels
# and the gauge stations placed along them. Illustrative, not a map.
# -----------------------------------------------------------------------------
fig, ax = rkv.new_figure((rkv.TEXT_WIDTH_IN, 2.55))
x = np.linspace(0, 10, 400)
channels = [
    (0.0, 0.55, 1.3, rkv.PRIMARY, 2.4),
    (0.8, 0.35, 0.9, rkv.EVIDENCE, 1.4),
    (-0.9, 0.42, 1.7, rkv.EVIDENCE, 1.2),
    (1.6, 0.25, 0.6, rkv.MUTED, 0.9),
    (-1.7, 0.30, 2.1, rkv.MUTED, 0.9),
]
for offset, amplitude, phase, color, width in channels:
    spread = offset * (x / 10) ** 1.4
    ax.plot(x, spread + amplitude * np.sin(x * 0.9 + phase), color=color, linewidth=width, solid_capstyle="round")
rng = np.random.default_rng(7)
stations_x = np.sort(rng.uniform(0.6, 9.6, 40))
stations_y = []
for sx in stations_x:
    offset, amplitude, phase, _, _ = channels[int(rng.integers(0, len(channels)))]
    stations_y.append(offset * (sx / 10) ** 1.4 + amplitude * np.sin(sx * 0.9 + phase))
ax.scatter(stations_x, stations_y, s=16, color=rkv.WHITE, edgecolor=rkv.DECISION, linewidth=1.1, zorder=3)
ax.text(0.2, 1.85, "UPLAND", color=rkv.MUTED, fontsize=7, ha="left")
ax.text(9.8, -2.25, "SEA", color=rkv.MUTED, fontsize=7, ha="right")
ax.set_xlim(0, 10)
ax.set_ylim(-2.5, 2.1)
ax.set_axis_off()
_save(fig, "opening-delta")

# -----------------------------------------------------------------------------
# Full-width exhibit -- median flood-warning lead time, hours.
# -----------------------------------------------------------------------------
years = pd.date_range("2018-12-31", periods=8, freq="YE")
lead = pd.DataFrame(
    {
        "Gauge network": [3.1, 3.4, 5.2, 7.9, 10.6, 12.8, 13.9, 14.6],
        "Visual watch (before gauges)": [3.1, 3.2, 3.0, 3.3, 3.1, 3.2, 3.0, 3.1],
    },
    index=years,
)
fig, ax = rkv.timeseries(
    lead,
    ylabel="Median warning lead time (hours)",
    benchmark="Visual watch (before gauges)",
    size="compact",
)
_save(fig, "warning-lead-time")

# -----------------------------------------------------------------------------
# Column exhibit -- gauges installed per district by the end of the survey.
# -----------------------------------------------------------------------------
gauges = pd.Series({"North Reach": 6, "Mill Bank": 9, "Old Harbour": 11, "Salt Flats": 8, "Ferry Point": 6})
fig, ax = rkv.bar_chart(gauges, horizontal=True, highlight="Old Harbour", axis_label="Gauges installed", size="column")
_save(fig, "gauges-by-district")
