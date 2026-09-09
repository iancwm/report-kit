"""Python theme tokens for ReportKit's default theme.

Every value here is `reportkit_viz.py`'s original, pre-Step-4 hardcoded
constant, moved verbatim (not recomputed) so `apply_theme("default")` --
also the module's zero-argument default -- reproduces today's chart output
exactly. See `latex_templates/themes/reportkit-theme-default.sty` for the
matching LaTeX palette; `reportkit_viz.py check-theme` (no `--theme`, or
`--theme default`) validates the two stay in sync.
"""
from __future__ import annotations

from . import Theme

INK = "#24272D"
MUTED = "#687386"
HAIRLINE = "#D9DEE5"
PRIMARY = "#2C5E78"  # LinkBlue / Principle
DECISION = "#68558A"
RESEARCH = "#2B7074"
TIP = "#3F6D54"
RED_FLAG = "#A14B45"
ASSUMPTION = "#8A6A24"
EVIDENCE = "#4B6472"
LIMITATION = "#6E6A67"
METRIC = "#315E86"
DELIVERABLE = "#2C6E49"
SURFACE = "#F7F8FA"
WHITE = "#FFFFFF"

# A4 ReportKit text width: 210mm - 2*27mm = 156mm.
TEXT_WIDTH_IN = 156 / 25.4

THEME = Theme(
    name="default",
    latex_colors={
        "Ink": INK,
        "Muted": MUTED,
        "Hairline": HAIRLINE,
        "LinkBlue": PRIMARY,
        "Principle": PRIMARY,
        "Decision": DECISION,
        "Research": RESEARCH,
        "Tip": TIP,
        "RedFlag": RED_FLAG,
        "Assumption": ASSUMPTION,
        "Evidence": EVIDENCE,
        "Limitation": LIMITATION,
        "MetricAccent": METRIC,
        "Deliverable": DELIVERABLE,
    },
    surface=SURFACE,
    white=WHITE,
    # Analytical colors use the same visual family but are not semantic
    # callout labels. Cool categorical colors avoid accidental good/bad
    # encoding.
    data_colors=(PRIMARY, RESEARCH, DECISION, EVIDENCE, "#728192", "#7B6F88"),
    benchmark="#8B949E",
    data_warm="#8A6658",  # sign / diverging endpoint; not "bad"
    data_positive=TIP,  # use only when positive direction is meaningful
    data_negative=RED_FLAG,  # use only when negative direction is meaningful
    text_width_in=TEXT_WIDTH_IN,
    figure_sizes={
        "full": (TEXT_WIDTH_IN, 3.55),
        "wide": (TEXT_WIDTH_IN, 3.05),
        # `dominant` is spec §15's proposed name for the same not-quite-
        # full-width size `wide` already occupies -- the implementation
        # plan's resolution to open question 3 keeps `wide` as a working
        # alias rather than dropping it, since it's public API existing
        # publications call (`new_figure("wide")`).
        "dominant": (TEXT_WIDTH_IN, 3.05),
        "compact": (TEXT_WIDTH_IN, 2.55),
        "square": (4.85, 4.35),
        # New in Step 4: sized for a half-width exhibit pane (matches
        # reportkit-equity-research.sty's exhibitpair, which uses
        # 0.485\linewidth per pane). Doesn't exist pre-Step-4, so adding it
        # here doesn't touch any existing publication's output.
        "half": (TEXT_WIDTH_IN * 0.485, 1.237),
        "sidebar": (1.65, 1.65),  # ~1.7in square for proportional data in sidebar (default A4 theme)
    },
    sans_candidates=("Libertinus Sans", "Linux Biolinum O", "Linux Biolinum", "Arial", "DejaVu Sans"),
    serif_candidates=("Libertinus Serif", "Linux Libertine O", "Linux Libertine", "DejaVu Serif"),
    mono_candidates=("Libertinus Mono", "Linux Libertine Mono O", "DejaVu Sans Mono"),
    base_font_size=9.0,
    mathtext_fontset="stix",
)
