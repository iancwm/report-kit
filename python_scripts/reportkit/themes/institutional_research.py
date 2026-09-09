"""Python theme tokens for the institutional-research theme (spec §13-§15,
§20). See `latex_templates/themes/reportkit-theme-institutional-research.sty`
for the matching LaTeX palette; `reportkit_viz.py check-theme --theme
institutional-research` validates the two stay in sync (this module is what
closes the honest-failure gap Step 1's plan predicted for that check before
this module existed).

The semantic-callout colors below (`PRINCIPLE`, `DECISION`, ... down to
`DELIVERABLE`) are kept at the same hex values as `default.py`'s, for the
same reason the `.sty` file keeps them the same as
`reportkit-theme-default.sty`'s: spec §21 asks the theme to quiet the
callout *chrome*, not recolor each category -- see that `.sty` file's
palette comment for the longer version of this decision.

FONT LICENSING NOTICE: This theme specifies Google Sans as the primary
typeface. The Google Sans font files included in font_data/ are licensed
under Apache License 2.0 (sourced from Google Fonts). Publications built
with this theme must preserve the font attribution and license notice.
See font_data/GOOGLE_SANS_LICENSE.md for full licensing details.
"""
from __future__ import annotations

from . import Theme

INK = "#202124"
MUTED = "#6B7075"
HAIRLINE = "#D9DDE1"
LINK_BLUE = "#2477A7"  # SeriesBlue in the .sty file
ACCENT = "#18A999"
SURFACE = "#F7F8F8"
WHITE = "#FFFFFF"

# Same hex values as default.py's semantic-callout colors -- see module
# docstring.
PRINCIPLE = "#2C5E78"
DECISION = "#68558A"
RESEARCH = "#2B7074"
TIP = "#3F6D54"
RED_FLAG = "#A14B45"
ASSUMPTION = "#8A6A24"
EVIDENCE = "#4B6472"
LIMITATION = "#6E6A67"
DELIVERABLE = "#2C6E49"

SERIES_GOLD = "#D6A84B"
BEAR_RED = "#A94343"
BULL_GREEN = "#2C6E49"

# US Letter text width, derived from
# themes/reportkit-theme-institutional-research.sty's geometry:
# 215.9mm (8.5in) - 14mm left margin - 14mm right margin = 187.9mm.
TEXT_WIDTH_IN = 187.9 / 25.4

THEME = Theme(
    name="institutional-research",
    latex_colors={
        "Ink": INK,
        "Muted": MUTED,
        "Hairline": HAIRLINE,
        "LinkBlue": LINK_BLUE,
        "Principle": PRINCIPLE,
        "Decision": DECISION,
        "Research": RESEARCH,
        "Tip": TIP,
        "RedFlag": RED_FLAG,
        "Assumption": ASSUMPTION,
        "Evidence": EVIDENCE,
        "Limitation": LIMITATION,
        "MetricAccent": ACCENT,
        "Deliverable": DELIVERABLE,
    },
    surface=SURFACE,
    white=WHITE,
    # Cool, restrained categorical colors (spec §20: "Colors should be
    # scarce ... <5% of visible page area"), matching Appendix A's
    # secondary-series palette (Accent teal, SeriesBlue, SeriesGold) plus
    # two muted extensions for a longer series list.
    data_colors=(ACCENT, LINK_BLUE, SERIES_GOLD, MUTED, "#5C8A84", "#7B93A6"),
    benchmark=MUTED,
    data_warm=SERIES_GOLD,
    data_positive=BULL_GREEN,
    data_negative=BEAR_RED,
    text_width_in=TEXT_WIDTH_IN,
    # Ratio-derived from TEXT_WIDTH_IN (open question 4), reusing the exact
    # width:height ratios default.py's absolute numbers already embody
    # (full 0.578, wide/dominant 0.497, compact 0.415; square width 0.790x
    # of text width with a 0.897 height:width ratio) -- those ratios read as
    # "16:9-ish landscape" (full) through "squarer" (compact) regardless of
    # which theme's text width they're applied to, which is exactly what
    # the implementation plan's open-question-4 resolution asked for
    # ("one configurable aspect ratio per named size"). Only `half` (sized
    # for reportkit-equity-research.sty's exhibitpair, 0.485\linewidth per
    # pane) uses a different ratio (compact's, since a half-width pane
    # reads better squarer than full-width-derived proportions would).
    figure_sizes={
        "full": (TEXT_WIDTH_IN, 4.276),
        "wide": (TEXT_WIDTH_IN, 3.674),
        "dominant": (TEXT_WIDTH_IN, 3.674),
        "compact": (TEXT_WIDTH_IN, 3.071),
        "square": (5.842, 5.240),
        "half": (3.588, 1.490),
    },
    # Google Sans is the primary typeface for this theme. It is licensed under
    # Apache License 2.0 and sourced from Google Fonts. The static-weight
    # instantiations (Regular/Medium/Bold) are in font_data/. Font fallbacks
    # (Inter, Noto Sans, Arial, DejaVu Sans) are provided for systems where
    # Google Sans is unavailable. See THIRD-PARTY-NOTICES.md and
    # font_data/GOOGLE_SANS_LICENSE.md for full licensing information.
    sans_candidates=("Google Sans", "Inter", "Noto Sans", "Arial", "DejaVu Sans"),
    # Spec §14: eliminate serif leakage entirely under this theme -- serif
    # and mono candidates resolve to the same sans chain rather than a
    # distinct serif family, so nothing in a chart can accidentally pick up
    # a serif font the way STIX mathtext could under the default theme
    # (mathtext_fontset="custom" below closes that specific leak; these
    # candidate lists close it for font.serif/font.monospace too, in case
    # any chart helper ever sets a family explicitly rather than through
    # font.family).
    serif_candidates=("Google Sans", "Inter", "Noto Sans", "Arial", "DejaVu Sans"),
    mono_candidates=("Google Sans", "Inter", "Noto Sans", "DejaVu Sans Mono"),
    # Not re-tuned from default.py's 9.0: both themes' chart base size are
    # independent of the LaTeX document body size (10pt vs 10.7pt) they sit
    # alongside, and this session has no way to see a real printed page to
    # judge whether institutional-research's charts want a different base.
    # Revisit with Step 5's fixture, once there's something to look at.
    base_font_size=9.0,
    mathtext_fontset="custom",
)
