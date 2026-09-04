#!/usr/bin/env python3
"""Generate analytical figures for the Career Exploration Framework guide.

Only one figure in this report is genuinely data-driven: the frequency with
which competencies appear across a sample of job advertisements (Module 2,
Recruitment Reverse Engineering). Everything else in the guide is a
conceptual/structural relationship and stays in the native ReportKit diagram
grammar instead.
"""
from pathlib import Path
import pandas as pd
import reportkit_viz as rkv

FIGURES = Path("figures")
FIGURES.mkdir(exist_ok=True)

# Illustrative values matching the worked example in the source framework.
competency_frequency = pd.Series(
    {
        "SQL": 0.78,
        "Communication": 0.67,
        "Python": 0.63,
        "Cloud": 0.42,
        "Spark": 0.31,
    }
)

fig, ax = rkv.bar_chart(
    competency_frequency,
    horizontal=True,
    sort=True,
    value_formatter=rkv.percent_formatter(0),
    axis_label="Share of sampled job advertisements",
    zero_line=False,
    size="compact",
)
rkv.save_figure(fig, FIGURES / "competency_frequency")

print("wrote figures/competency_frequency.pdf + .png")
