"""Python tokens for ReportKit's stable executive slide theme.

The token record is the chart-side projection of the consulting/strategy
system in ``reportkit-theme-executive.sty``: restrained navy/teal structure,
one warm decision accent, and compact slide-native figure slots.

Colors mirror latex_templates/themes/reportkit-theme-executive.sty's
palette exactly -- reportkit_viz.py check-theme --theme executive validates
that stays true, the same contract every other theme's Python module keeps.
"""
from __future__ import annotations

from . import (
    ChartTokens,
    DiagramTokens,
    GeometryTokens,
    RuleTokens,
    ScriptCoverageTokens,
    SpacingTokens,
    TableTokens,
    Theme,
    TypographyTokens,
)

INK = "#17202A"
MUTED = "#566273"
HAIRLINE = "#D8DEE7"
SURFACE = "#F2F5F8"
ACCENT = "#0B7285"  # LinkBlue / Principle / Accent
DECISION = "#C26A2D"
RESEARCH = "#3C6E71"
TIP = "#2F855A"
RED_FLAG = "#B54747"
ASSUMPTION = "#9A6B1E"
EVIDENCE = "#39566F"
LIMITATION = "#6B7280"
METRIC = "#0B7285"
DELIVERABLE = "#2D6A4F"
WHITE = "#FFFFFF"

# Phase C (decision D5): Beamer's aspectratio=169 produces a 160mm x 90mm
# frame natively; reportkit-theme-executive-slides.sty sets an 8mm safe-area
# text margin each side (that file's own comment says to update this
# derivation if that number ever changes -- no cross-language token sync
# mechanism exists yet, the same gap every paged theme's \geometry{} margins
# already have against TEXT_WIDTH_IN below). 160 - 2*8 = 144mm usable width;
# 90mm tall minus the footline (~4mm) and top breathing room (~6mm) leaves
# roughly 80mm of usable height for a full-width visual.
_CANVAS_WIDTH_MM = 160
_CANVAS_HEIGHT_MM = 90
_SAFE_MARGIN_MM = 8
_USABLE_WIDTH_MM = _CANVAS_WIDTH_MM - 2 * _SAFE_MARGIN_MM
_USABLE_HEIGHT_MM = _CANVAS_HEIGHT_MM - 10
TEXT_WIDTH_IN = _USABLE_WIDTH_MM / 25.4

TYPOGRAPHY = TypographyTokens(
    display="Libertinus Sans",
    heading="Libertinus Sans",
    body="Libertinus Sans",
    metadata="Libertinus Sans",
    table="Libertinus Sans",
    chart="Libertinus Sans",
    mono="Libertinus Mono",
    math="STIX",
)
GEOMETRY = GeometryTokens(
    paper=None,
    canvas_mm=(_CANVAS_WIDTH_MM, _CANVAS_HEIGHT_MM),
    text_width_in=TEXT_WIDTH_IN,
    margins_mm=(5.0, 8.0, 5.0, 8.0),
    column_gutter_in=0.25,
)
SPACING = SpacingTokens(paragraph=4.0, heading=6.0, component=4.0)
RULES = RuleTokens(thin=0.6, medium=0.9)
TABLES = TableTokens(body_size=10.0, header_treatment="bold-label", row_spacing=1.0)
CHARTS = ChartTokens(
    base_font=10.0,
    tick_size=9.1,
    label_size=10.0,
    line_width=1.7,
    grid_style="y",
    legend_style="above",
)
DIAGRAMS = DiagramTokens(node_font=8.1, node_padding=(5.0, 4.0), node_radius=1.2, edge_weight=0.8, label_font=6.8)
SCRIPT_COVERAGE = ScriptCoverageTokens(verified=("Latn",), metadata_only=(), rtl="unsupported")

THEME = Theme(
    name="executive",
    latex_colors={
        "Ink": INK,
        "Muted": MUTED,
        "Hairline": HAIRLINE,
        "LinkBlue": ACCENT,
        "Principle": ACCENT,
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
    data_colors=(ACCENT, RESEARCH, DECISION, EVIDENCE, "#7A8794", "#9A765C"),
    benchmark="#9198A5",
    data_warm="#A85C45",
    data_positive=TIP,
    data_negative=RED_FLAG,
    text_width_in=TEXT_WIDTH_IN,
    # Phase C: slide visualization slots, not the seven paged size
    # names (full/wide/dominant/compact/square/half/sidebar) -- those are
    # paged-layout concepts (equity-research's sidebar pane, a full A4 text
    # column, ...) that don't have an obvious slide-canvas equivalent, and
    # no composition in reportkit-presentation.sty references them. A
    # slide-compatible theme's figure_sizes therefore carries only these
    # three keys; a chart call for "full" or "sidebar" under this theme
    # fails with a clear KeyError rather than silently reusing a paged
    # theme's page-relative dimensions on a 160mm-wide canvas.
    figure_sizes={
        # Full-width visual (visualtext's own visual column is narrower --
        # see "half" -- but fullvisual/architectureslide span the whole
        # usable width).
        "slide-main": (TEXT_WIDTH_IN, _USABLE_HEIGHT_MM / 25.4 * 0.72),
        # Matches visualtext/chartslide/tableslide's own visual column width
        # (.48\linewidth of the frame's already-margined text area, from
        # reportkit-presentation.sty's rkpresentation@visualtext@start).
        "slide-half": (_USABLE_WIDTH_MM * 0.48 / 25.4, _USABLE_HEIGHT_MM / 25.4 * 0.62),
        # A smaller supporting visual (e.g. alongside a herometric).
        "slide-hero": (_USABLE_WIDTH_MM * 0.62 / 25.4, _USABLE_HEIGHT_MM / 25.4 * 0.5),
    },
    # The stable executive fixture chooses the bundled Libertinus family for
    # reproducible direct and pipeline builds; the fallback candidates keep
    # consumer projects usable when the bundle is not installed system-wide.
    sans_candidates=("Libertinus Sans", "Linux Biolinum O", "Linux Biolinum", "Arial", "DejaVu Sans"),
    serif_candidates=("Libertinus Serif", "Linux Libertine O", "Linux Libertine", "DejaVu Serif"),
    mono_candidates=("Libertinus Mono", "Linux Libertine Mono O", "DejaVu Sans Mono"),
    base_font_size=10.0,
    mathtext_fontset="stix",
    typography=TYPOGRAPHY,
    geometry=GEOMETRY,
    spacing=SPACING,
    rules=RULES,
    tables=TABLES,
    charts=CHARTS,
    diagrams=DIAGRAMS,
    script_coverage=SCRIPT_COVERAGE,
)
