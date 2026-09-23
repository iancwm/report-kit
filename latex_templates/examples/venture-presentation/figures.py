#!/usr/bin/env python3
"""Generate the fictional Lumiquay pitch deck's chart, product image and logo.

The chart and product image are drawn under the publication's *effective*
theme: ``reportkit_viz.apply_publication_theme`` resolves ``publication.yaml``
(venture theme plus the D6 ``brand`` section) into the same immutable record
the build materializes into ``reportkit-theme-overrides.tex``, so chart and
slide colours cannot drift apart.

The logo is a fixed, fictional brand asset (a brand's mark does not follow a
slide theme), so it is drawn with literal colours and written once to
``assets/``, where ``brand.logo`` points.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python_scripts"))

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch  # noqa: E402

import reportkit_viz as rkv  # noqa: E402

EXAMPLE = Path(__file__).resolve().parent
FIGURES = EXAMPLE / "figures"
ASSETS = EXAMPLE / "assets"
# Deterministic PDF metadata so regenerated assets are byte-stable.
METADATA = {"CreationDate": None, "Creator": "ReportKit venture fixture"}


def draw_logo() -> None:
    fig = plt.figure(figsize=(1.9, 0.5))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 3.8)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(Circle((0.5, 0.5), 0.38, color="#0E7C66"))
    ax.add_patch(Circle((0.62, 0.62), 0.14, color="#FFB020"))
    ax.text(1.05, 0.47, "Lumiquay", fontsize=17, fontweight="bold", color="#10231D", va="center")
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / "lumiquay-mark.pdf", metadata=METADATA, transparent=True)
    plt.close(fig)


def draw_arr() -> None:
    fig, ax = rkv.bar_chart(
        {"Q1\n'25": 0.4, "Q2\n'25": 0.7, "Q3\n'25": 1.1, "Q4\n'25": 1.6, "Q1\n'26": 2.3, "Q2\n'26": 3.1},
        horizontal=False,
        highlight="Q2\n'26",
        value_formatter=lambda value, _pos: f"${value:.1f}M",
        size="slide-half",
    )
    rkv.save_figure(fig, FIGURES / "arr-growth", formats=("pdf",), metadata=METADATA)


def draw_product() -> None:
    """A fictional product screenshot: store temperature pulse with an alert."""
    fig = plt.figure(figsize=rkv.FIGURE_SIZES["slide-half"])
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 64)
    ax.axis("off")
    ink, muted, primary, secondary = rkv.INK, rkv.MUTED, rkv.PRIMARY, rkv.RESEARCH
    ax.add_patch(FancyBboxPatch((1, 1), 98, 62, boxstyle="round,pad=0,rounding_size=3", facecolor="white", edgecolor="#D5DAE3", linewidth=1))
    ax.add_patch(FancyBboxPatch((1, 55), 98, 8, boxstyle="round,pad=0,rounding_size=3", facecolor="#F1F3F7", edgecolor="none"))
    for index, colour in enumerate(("#E5484D", "#F5A524", "#30A46C")):
        ax.add_patch(Circle((5 + index * 3.2, 59), 1.0, color=colour))
    ax.text(50, 59, "Lumiquay Pulse  ·  Store 14", ha="center", va="center", fontsize=5.4, color=muted)
    ax.add_patch(FancyBboxPatch((4, 5), 26, 46, boxstyle="round,pad=0,rounding_size=2", facecolor="#F6F7FA", edgecolor="none"))
    rows = (("Dairy chiller", "ok"), ("Produce mist", "ok"), ("Freezer 2", "alert"), ("Deli case", "ok"), ("Walk-in", "ok"))
    for index, (label, state) in enumerate(rows):
        y = 45 - index * 8.5
        ax.add_patch(Circle((8, y), 1.1, color=secondary if state == "alert" else primary))
        ax.text(11, y, label, va="center", fontsize=5.2, color=ink, fontweight="bold" if state == "alert" else "normal")
    ax.text(34, 48, "Freezer 2 breaches -15 °C in ~40 min", fontsize=5.8, color=ink, fontweight="bold")
    ax.text(34, 43.5, "Door-seal wear detected · technician suggested", fontsize=4.7, color=muted)
    xs = [34 + step * 2.6 for step in range(23)]
    temps = [22, 22.5, 21.8, 22.2, 22.9, 23.4, 24.1, 24.8, 25.9, 27.0, 28.4, 29.1, 30.3, 31.4, 32.8, 34.0]
    ax.plot(xs[: len(temps)], temps, color=primary, linewidth=2.2, solid_capstyle="round")
    forecast = [temps[-1] + 1.3 * step for step in range(len(xs) - len(temps) + 1)]
    ax.plot(xs[len(temps) - 1:], forecast, color=secondary, linewidth=2.2, linestyle=(0, (2, 1.6)))
    ax.axhline(40, xmin=0.34, xmax=0.95, color=secondary, linewidth=0.9, alpha=0.7)
    ax.text(95, 36.4, "breach", ha="right", fontsize=4.4, color=secondary)
    ax.add_patch(FancyBboxPatch((34, 5), 28, 11, boxstyle="round,pad=0,rounding_size=2", facecolor=primary, edgecolor="none"))
    ax.text(48, 10.5, "Dispatch technician", ha="center", va="center", fontsize=5.0, color="white", fontweight="bold")
    ax.text(66, 10.5, "Move stock to Freezer 1", va="center", fontsize=4.8, color=muted)
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "product-pulse.pdf", metadata=METADATA)
    plt.close(fig)


def main() -> None:
    # The logo comes first: brand.logo must exist before the effective theme
    # can be resolved (normalization hashes the exact file).
    draw_logo()
    effective = rkv.apply_publication_theme(EXAMPLE)
    print(f"effective theme {effective.theme} palette {effective.palette_hash[:12]}")
    draw_arr()
    draw_product()
    print(f"wrote {FIGURES} and {ASSETS}")


if __name__ == "__main__":
    main()
