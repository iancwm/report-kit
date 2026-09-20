#!/usr/bin/env python3
"""Generate the fictional NexaGrid strategy deck's analytical bridge."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python_scripts"))

import reportkit_viz as rkv


FIGURES = Path(__file__).resolve().parent / "figures"


def main() -> None:
    rkv.apply_theme("executive")
    fig, _ = rkv.waterfall_chart(
        {"Platform": 18, "Workflow": 12, "Governance": 7, "Manual rework": -9},
        opening=100,
        opening_label="2026 base",
        total_label="2027 run-rate",
        value_formatter="number",
        ylabel="Operating leverage index",
        size="slide-half",
    )
    outputs = rkv.save_figure(fig, FIGURES / "adoption-bridge", formats=("pdf",))
    print("wrote " + ", ".join(str(path) for path in outputs))


if __name__ == "__main__":
    main()
