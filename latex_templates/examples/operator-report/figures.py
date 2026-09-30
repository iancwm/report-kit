#!/usr/bin/env python3
"""Generate the fictional operator-theme evidence figures.

Every name and value in this file is invented for the ReportKit fixture.
Run from the repository root with ``PYTHONPATH=python_scripts``. The PDF
outputs are embedded by ``report.tex`` and PNG copies are for visual QA.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import reportkit_viz as rkv


HERE = Path(__file__).resolve().parent
FIGURES = HERE / "figures"
FIGURES.mkdir(exist_ok=True)

rkv.apply_theme("operator")


def _save(fig, stem: str) -> None:
    rkv.save_figure(
        fig,
        FIGURES / stem,
        formats=("pdf", "png"),
        metadata={"Creator": "ReportKit fictional operator fixture"},
    )


# Figure 3 — equal-weight count of documented statements in the invented
# comparison packet. These are counts, not a weighted product score.
evidence = pd.Series(
    {
        "Kestrel Loom": 9,
        "Morrow Dock": 6,
        "Cinder Relay": 7,
    },
    name="Documented statements",
)
fig, ax = rkv.bar_chart(
    evidence,
    horizontal=True,
    axis_label="Documented statements (of 9)",
    value_formatter="integer",
    value_labels="outside",
    size="full",
)
_save(fig, "fig-3-evidence-status")


# Figure 5 — monthly review effort and inference charges for fictional run
# profiles. Review uses the theme's first hatch; inference remains solid.
costs = pd.DataFrame(
    {
        "Review": [7.2, 9.6, 10.8, 12.0],
        "Inference": [1.8, 2.6, 3.4, 4.1],
    },
    index=["Small pilot", "Routine month", "Busy month", "Cap month"],
)
fig, ax = rkv.stacked_bar_chart(
    costs,
    horizontal=False,
    value_formatter=rkv.currency_formatter(),
    axis_label="Illustrative monthly cost (fictional dollars)",
    sort=False,
    size="full",
)
_save(fig, "fig-5-cost-per-attempt")


# Figure 6 — three invented cost policies indexed by attempted run count. The
# marker at 64 denotes a fictional credit allowance, not a hard run limit.
attempts = [0, 16, 32, 48, 64, 80, 96]
conditional_cost = pd.DataFrame(
    {
        "Local ledger": [18.0 + 0.12 * count for count in attempts],
        "Managed credits": [24.0 + 0.12 * max(count - 64, 0) for count in attempts],
        "Hosted queue + review": [31.0 + 0.10 * count for count in attempts],
    },
    index=attempts,
)
fig, ax = rkv.line_chart(
    conditional_cost,
    xlabel="Attempts per month",
    ylabel="Illustrative monthly cost (fictional dollars)",
    vertical_marker=64,
    vertical_marker_label="64-credit allowance",
    legend=True,
    size="full",
)
_save(fig, "fig-6-conditional-cost")

print(f"wrote 3 fictional operator figures to {FIGURES}")
