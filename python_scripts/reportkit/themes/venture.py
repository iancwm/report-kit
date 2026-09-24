"""Python tokens for ReportKit's venture (pitch-deck) slide theme.

The chart-side projection of ``reportkit-theme-venture.sty``: a vivid indigo
primary, a coral secondary, near-black ink, and larger slide-native type.
Colors mirror the LaTeX palette exactly -- ``reportkit_viz.py check-theme
--theme venture`` validates that, the same contract every theme keeps.

Venture is the only theme whose registry record sets ``brand_overrides``
(decision D6). ``latex_colors`` therefore also carries ``Accent``: the
compositions read that name directly, and the effective-theme projection can
only re-point names that are part of this record.
"""
from __future__ import annotations

from . import (
    ChartTokens,
    DiagramTokens,
    GeometryTokens,
    RuleTokens,
    ScriptCoverageTokens,
    ScriptFontStack,
    SpacingTokens,
    TableTokens,
    Theme,
    TypographyTokens,
)

INK = "#111827"
MUTED = "#5B6475"
HAIRLINE = "#E3E6EE"
SURFACE = "#F4F5FA"
PRIMARY = "#4F46E5"  # Accent / LinkBlue / Principle / MetricAccent
SECONDARY = "#FF6A3D"  # Research; accent on dark frames
DECISION = "#D97706"
TIP = "#059669"
RED_FLAG = "#DC2626"
ASSUMPTION = "#B45309"
EVIDENCE = "#334155"
LIMITATION = "#6B7280"
DELIVERABLE = "#047857"
WHITE = "#FFFFFF"

# reportkit-theme-venture-slides.sty sets a 12mm safe-area margin each side
# of the 160mm x 90mm frame: 136mm usable width. The footline is taller than
# executive's, so roughly 76mm of height remains for a full-width visual.
_CANVAS_WIDTH_MM = 160
_CANVAS_HEIGHT_MM = 90
_SAFE_MARGIN_MM = 12
_USABLE_WIDTH_MM = _CANVAS_WIDTH_MM - 2 * _SAFE_MARGIN_MM
_USABLE_HEIGHT_MM = _CANVAS_HEIGHT_MM - 14
TEXT_WIDTH_IN = _USABLE_WIDTH_MM / 25.4

TYPOGRAPHY = TypographyTokens(
    display="Google Sans",
    heading="Google Sans",
    body="Google Sans",
    metadata="Google Sans",
    table="Google Sans",
    chart="Google Sans",
    mono="Latin Modern Mono",
    math="STIX",
)
GEOMETRY = GeometryTokens(
    paper=None,
    canvas_mm=(_CANVAS_WIDTH_MM, _CANVAS_HEIGHT_MM),
    text_width_in=TEXT_WIDTH_IN,
    margins_mm=(7.0, 12.0, 7.0, 12.0),
    column_gutter_in=0.3,
)
SPACING = SpacingTokens(paragraph=6.0, heading=8.0, component=5.0)
RULES = RuleTokens(thin=0.8, medium=2.0)
TABLES = TableTokens(body_size=11.0, header_treatment="bold-label", row_spacing=1.2)
CHARTS = ChartTokens(
    base_font=11.0,
    tick_size=10.0,
    label_size=11.0,
    line_width=2.4,
    grid_style="y",
    legend_style="above",
)
DIAGRAMS = DiagramTokens(node_font=8.4, node_padding=(5.0, 4.0), node_radius=3.0, edge_weight=1.1, label_font=7.2)
# The families reportkit-theme-venture.sty actually selects, in fallback
# order: Google Sans (bundled static faces) for body and display, then the
# Inter / Noto Sans / TeX Gyre Heros chain; fontspec's default Latin Modern
# Mono for code. A brand display_font replaces only display roles and is not
# a verified coverage claim.
_LATIN_SANS = ("Google Sans", "Inter", "Noto Sans", "TeX Gyre Heros")
SCRIPT_COVERAGE = ScriptCoverageTokens(
    verified=("Latn",),
    metadata_only=(),
    rtl="unsupported",
    font_stacks={
        "Latn": ScriptFontStack(
            body=_LATIN_SANS,
            heading=_LATIN_SANS,
            mono=("Latin Modern Mono",),
        ),
    },
    verified_languages=("en",),
    metadata_only_languages=("vi",),
)

THEME = Theme(
    name="venture",
    latex_colors={
        "Ink": INK,
        "Muted": MUTED,
        "Hairline": HAIRLINE,
        "Accent": PRIMARY,
        "LinkBlue": PRIMARY,
        "Principle": PRIMARY,
        "Decision": DECISION,
        "Research": SECONDARY,
        "Tip": TIP,
        "RedFlag": RED_FLAG,
        "Assumption": ASSUMPTION,
        "Evidence": EVIDENCE,
        "Limitation": LIMITATION,
        "MetricAccent": PRIMARY,
        "Deliverable": DELIVERABLE,
    },
    surface=SURFACE,
    white=WHITE,
    data_colors=(PRIMARY, SECONDARY, "#14B8A6", DECISION, "#94A3B8", EVIDENCE),
    benchmark="#9CA3AF",
    data_warm=SECONDARY,
    data_positive=TIP,
    data_negative=RED_FLAG,
    text_width_in=TEXT_WIDTH_IN,
    # Slide slots only, as for executive; the paged size names do not exist
    # on a slide canvas and fail loudly under this theme.
    figure_sizes={
        "slide-main": (TEXT_WIDTH_IN, _USABLE_HEIGHT_MM / 25.4 * 0.72),
        # visualtext/chartslide/tableslide's visual column is .48 of the
        # margined text width (reportkit-presentation.sty).
        "slide-half": (_USABLE_WIDTH_MM * 0.48 / 25.4, _USABLE_HEIGHT_MM / 25.4 * 0.66),
        "slide-hero": (_USABLE_WIDTH_MM * 0.62 / 25.4, _USABLE_HEIGHT_MM / 25.4 * 0.5),
    },
    # Google Sans is bundled in font_data/ and installed by the pinned
    # toolchain image; the fallbacks match the TeX theme's fallback chain.
    sans_candidates=("Google Sans", "Inter", "Noto Sans", "DejaVu Sans"),
    serif_candidates=("Libertinus Serif", "DejaVu Serif"),
    mono_candidates=("Latin Modern Mono", "DejaVu Sans Mono"),
    base_font_size=11.0,
    mathtext_fontset="custom",
    typography=TYPOGRAPHY,
    geometry=GEOMETRY,
    spacing=SPACING,
    rules=RULES,
    tables=TABLES,
    charts=CHARTS,
    diagrams=DIAGRAMS,
    script_coverage=SCRIPT_COVERAGE,
)
