"""Python visualization tokens for the experimental Operator theme."""
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

# These chart-facing roles mirror the canonical semantic colors in the
# operator LaTeX theme; its additional names are aliases of these roles.
INK = "#111111"
MUTED = "#6B6B68"
HAIRLINE = "#E8E8E3"
PRIMARY = "#5B5BD6"
DECISION = INK
RESEARCH = MUTED
TIP = "#00C2A8"
RED_FLAG = "#FF4D5A"
ASSUMPTION = PRIMARY
EVIDENCE = "#00C2A8"
LIMITATION = MUTED
METRIC = PRIMARY
DELIVERABLE = "#00C2A8"
SURFACE = "#FFFFFF"
WHITE = SURFACE

# 210 mm page - 20 mm side margins = 170 mm of text width.
TEXT_WIDTH_IN = 170 / 25.4

TYPOGRAPHY = TypographyTokens(
    display="Latin Modern Sans",
    heading="Latin Modern Sans",
    body="Latin Modern Sans",
    metadata="Latin Modern Sans",
    table="Latin Modern Sans",
    chart="Latin Modern Sans",
    mono="Latin Modern Mono",
    math="Latin Modern Roman",
)
GEOMETRY = GeometryTokens(
    paper="a4",
    canvas_mm=(210.0, 297.0),
    text_width_in=TEXT_WIDTH_IN,
    margins_mm=(18.0, 20.0, 20.0, 20.0),
    column_gutter_in=0.25,
)
SPACING = SpacingTokens(paragraph=4.5, heading=15.0, component=6.0)
RULES = RuleTokens(thin=0.4, medium=0.8)
TABLES = TableTokens(body_size=9.0, header_treatment="bold-label", row_spacing=1.0)
CHARTS = ChartTokens(
    base_font=9.0,
    tick_size=8.1,
    label_size=9.0,
    line_width=1.7,
    grid_style="y",
    legend_style="above",
    hatches=("////", "", "....", "xx"),
    dashes=("-", "--", "-.", ":"),
)
DIAGRAMS = DiagramTokens(node_font=8.1, node_padding=(5.0, 4.0), node_radius=1.2, edge_weight=0.8, label_font=6.8)
SCRIPT_COVERAGE = ScriptCoverageTokens(
    verified=("Latn",),
    metadata_only=(),
    rtl="unsupported",
    font_stacks={
        "Latn": ScriptFontStack(
            body=("Latin Modern Sans",),
            heading=("Latin Modern Sans",),
            mono=("Latin Modern Mono",),
        ),
    },
    verified_languages=("en",),
    metadata_only_languages=("vi",),
)

THEME = Theme(
    name="operator",
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
    data_colors=(PRIMARY, TIP, "#606060", RED_FLAG),
    benchmark=MUTED,
    data_warm=RED_FLAG,
    data_positive=TIP,
    data_negative=RED_FLAG,
    text_width_in=TEXT_WIDTH_IN,
    figure_sizes={
        "full": (TEXT_WIDTH_IN, 3.55),
        "wide": (TEXT_WIDTH_IN, 3.05),
        "dominant": (TEXT_WIDTH_IN, 3.05),
        "compact": (TEXT_WIDTH_IN, 2.55),
        "square": (4.85, 4.35),
        "half": (TEXT_WIDTH_IN * 0.485, 1.237),
        "sidebar": (1.65, 1.65),
    },
    sans_candidates=("Latin Modern Sans", "DejaVu Sans"),
    serif_candidates=("Latin Modern Roman", "DejaVu Serif"),
    mono_candidates=("Latin Modern Mono", "DejaVu Sans Mono"),
    base_font_size=9.0,
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
