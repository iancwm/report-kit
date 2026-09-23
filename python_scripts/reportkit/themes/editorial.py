"""Python tokens for ReportKit's editorial (feature-article) theme.

The chart-side projection of ``reportkit-theme-editorial.sty``: warm ink,
one oxblood accent, muted slate/ochre/sage data colors, and Libertinus Sans
for chart text so exhibits read as metadata beside the Libertinus Serif
reading body.

Colors mirror latex_templates/themes/reportkit-theme-editorial.sty's palette
exactly -- ``reportkit_viz.py check-theme --theme editorial`` validates that.
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

INK = "#1E1C1A"
MUTED = "#6B655E"
HAIRLINE = "#D9D3CA"
SURFACE = "#F6F2EC"
ACCENT = "#9B2F24"
LINK = "#8A2C22"
PRINCIPLE = "#3D5A73"
DECISION = "#9B2F24"
RESEARCH = "#4E6E68"
TIP = "#5A7A52"
RED_FLAG = "#A8412F"
ASSUMPTION = "#9A7128"
EVIDENCE = "#4F5B66"
LIMITATION = "#736B63"
DELIVERABLE = "#3F6B4E"
WHITE = "#FFFFFF"
OCHRE = "#C08A2E"

# A4 (210mm) minus reportkit-theme-editorial-paged.sty's 30mm/30mm margins
# = 150mm. featurecolumns uses a 7mm gutter, so one column is 71.5mm; an
# inset (span=column outside featurecolumns) exhibit is 0.82 of the text
# width. Update these derivations if that adapter's geometry changes.
_TEXT_WIDTH_MM = 150.0
_GUTTER_MM = 7.0
_COLUMN_WIDTH_MM = (_TEXT_WIDTH_MM - _GUTTER_MM) / 2
_INSET_FRACTION = 0.82
TEXT_WIDTH_IN = _TEXT_WIDTH_MM / 25.4

TYPOGRAPHY = TypographyTokens(
    display="Libertinus Serif Display",
    heading="Libertinus Serif Display",
    body="Libertinus Serif",
    metadata="Libertinus Sans",
    table="Libertinus Sans",
    chart="Libertinus Sans",
    mono="Libertinus Mono",
    math="Libertinus Math",
)
GEOMETRY = GeometryTokens(
    paper="a4",
    canvas_mm=(210.0, 297.0),
    text_width_in=TEXT_WIDTH_IN,
    margins_mm=(24.0, 30.0, 26.0, 30.0),
    column_gutter_in=_GUTTER_MM / 25.4,
)
SPACING = SpacingTokens(paragraph=0.5, heading=16.0, component=11.0)
RULES = RuleTokens(thin=0.35, medium=0.8)
TABLES = TableTokens(body_size=8.4, header_treatment="bold-label", row_spacing=1.08)
CHARTS = ChartTokens(
    base_font=8.6,
    tick_size=7.8,
    label_size=8.6,
    line_width=1.6,
    grid_style="y",
    legend_style="above",
)
DIAGRAMS = DiagramTokens(node_font=7.4, node_padding=(4.0, 3.0), node_radius=0.6, edge_weight=0.9, label_font=6.5)
# Honest coverage: only English Latin-script typography is exercised by the
# reviewed fixture. Libertinus has Vietnamese, Greek and Cyrillic glyphs, but
# glyph presence is not verified typography, so nothing else is declared
# verified (Vietnamese stays metadata-only via the registry's language
# declaration) and RTL is unsupported.
# Families below are exactly what reportkit-theme-editorial.sty selects for
# Latin script: \RequirePackage{libertinus} (Serif body, Sans metadata, Mono)
# plus the \newfontfamily Libertinus Serif Display headline face. Headings
# below display size (subsections, kickers, labels) use Libertinus Sans.
SCRIPT_COVERAGE = ScriptCoverageTokens(
    verified=("Latn",),
    metadata_only=(),
    rtl="unsupported",
    font_stacks={
        "Latn": ScriptFontStack(
            body=("Libertinus Serif",),
            heading=("Libertinus Serif Display", "Libertinus Sans"),
            mono=("Libertinus Mono",),
        ),
    },
    verified_languages=("en",),
    metadata_only_languages=("vi",),
)

THEME = Theme(
    name="editorial",
    latex_colors={
        "Ink": INK,
        "Muted": MUTED,
        "Hairline": HAIRLINE,
        "LinkBlue": LINK,
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
    data_colors=(ACCENT, PRINCIPLE, OCHRE, TIP, MUTED, "#B9A58C"),
    benchmark="#A39C93",
    data_warm=OCHRE,
    data_positive=TIP,
    data_negative=RED_FLAG,
    text_width_in=TEXT_WIDTH_IN,
    # The shared paged size names every paged theme carries (full, wide,
    # dominant, compact, square, half, sidebar), plus the two feature-article
    # rhythm sizes: "inset" is a span=column exhibit in one-column prose and
    # "column" a span=column exhibit inside featurecolumns. "full" suits a
    # span=full exhibit or the opening visual.
    figure_sizes={
        "full": (TEXT_WIDTH_IN, 3.35),
        "wide": (TEXT_WIDTH_IN, 2.9),
        "dominant": (TEXT_WIDTH_IN, 2.9),
        "compact": (TEXT_WIDTH_IN, 2.45),
        "square": (4.6, 4.1),
        "half": (_COLUMN_WIDTH_MM / 25.4, 2.2),
        "sidebar": (1.95, 1.95),
        "inset": (_TEXT_WIDTH_MM * _INSET_FRACTION / 25.4, 2.6),
        "column": (_COLUMN_WIDTH_MM / 25.4, 2.2),
    },
    sans_candidates=("Libertinus Sans", "Linux Biolinum O", "Linux Biolinum", "DejaVu Sans"),
    serif_candidates=("Libertinus Serif", "Linux Libertine O", "Linux Libertine", "DejaVu Serif"),
    mono_candidates=("Libertinus Mono", "Linux Libertine Mono O", "DejaVu Sans Mono"),
    base_font_size=8.6,
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
