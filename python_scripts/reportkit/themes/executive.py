"""Python theme tokens for ReportKit's executive theme. EXPERIMENTAL -- see
latex_templates/themes/reportkit-theme-executive.sty's header for why: this
exists so the slides renderer and presentation composition API have a real
theme to render charts against, not as a finished visual design. Phase C's
design review retunes these values; only `apply_theme("executive")`
resolving at all, and its colors matching the LaTeX theme file, are meant to
hold up before then (both are covered by tests/test_reportkit_viz_themes.py
and this module's own use in reportkit_viz.py check-theme).

Colors mirror latex_templates/themes/reportkit-theme-executive.sty's
palette exactly -- reportkit_viz.py check-theme --theme executive validates
that stays true, the same contract every other theme's Python module keeps.
"""
from __future__ import annotations

from . import Theme

INK = "#1B1E24"
MUTED = "#5B6270"
HAIRLINE = "#D5D8DE"
SURFACE = "#F5F6F8"
ACCENT = "#3B5BDB"  # LinkBlue / Principle / Accent
DECISION = "#7048A8"
RESEARCH = "#1D8A7A"
TIP = "#2F7D4F"
RED_FLAG = "#B23A3A"
ASSUMPTION = "#9A6B1E"
EVIDENCE = "#3F5D75"
LIMITATION = "#6B6560"
METRIC = "#3B5BDB"
DELIVERABLE = "#22694A"
WHITE = "#FFFFFF"

# Phase B (decision D5): Beamer's aspectratio=169 produces a 160mm x 90mm
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
    data_colors=(ACCENT, RESEARCH, DECISION, EVIDENCE, "#7A8699", "#8D7FA8"),
    benchmark="#9198A5",
    data_warm="#8F6A4E",
    data_positive=TIP,
    data_negative=RED_FLAG,
    text_width_in=TEXT_WIDTH_IN,
    # Phase B (B3): slide visualization slots, not the seven paged size
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
    # D9 recommends Google Sans for executive; this experimental shell uses
    # Libertinus instead (reportkit-theme-executive.sty's header explains
    # why), so the chart font candidates match that, not the LaTeX theme's
    # eventual Phase C choice.
    sans_candidates=("Libertinus Sans", "Linux Biolinum O", "Linux Biolinum", "Arial", "DejaVu Sans"),
    serif_candidates=("Libertinus Serif", "Linux Libertine O", "Linux Libertine", "DejaVu Serif"),
    mono_candidates=("Libertinus Mono", "Linux Libertine Mono O", "DejaVu Sans Mono"),
    base_font_size=10.0,
    mathtext_fontset="stix",
)
