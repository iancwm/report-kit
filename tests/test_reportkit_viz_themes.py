"""Institutional-theme spec, Step 4: visualization integration.

Unlike Steps 1-3 (LaTeX .sty/.cls changes this session could not compile),
reportkit_viz.py and reportkit.themes are pure Python with matplotlib
available in this environment -- these tests actually execute the code
under test rather than pattern-matching its source text. See the
implementation plan's Step 4 section for what that buys and what it still
doesn't (real Google Sans, an actual rendered PDF page to eyeball).
"""
from __future__ import annotations

from pathlib import Path

import pytest

mpl = pytest.importorskip("matplotlib")
pytest.importorskip("numpy")
pytest.importorskip("pandas")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import reportkit_viz as rkv  # noqa: E402
from reportkit.context import month_end_freq  # noqa: E402
from reportkit.themes import Theme, available_themes, get_theme  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _restore_default_theme():
    """apply_theme() mutates process-wide matplotlib rcParams and this
    module's own globals -- reset to "default" after every test in this
    file so theme-switching tests can't leak state into whichever test
    (in this file or another) runs next."""
    yield
    rkv.apply_theme("default")


def test_available_themes_lists_declared_aliases() -> None:
    assert available_themes() == ("default", "institutional-research", "technical")


def test_get_theme_unknown_name_raises_with_known_themes_listed() -> None:
    with pytest.raises(ValueError, match="default.*institutional-research|institutional-research.*default"):
        get_theme("modern-minimal")


def test_apply_theme_default_matches_pre_step4_values() -> None:
    """apply_theme("default") -- also the module's own import-time default,
    no argument -- must reproduce every value reportkit_viz.py hardcoded
    before Step 4, exactly. This is this step's backward-compatibility
    guarantee, the chart-layer equivalent of spec §26 for the document
    theme."""
    rkv.apply_theme("default")
    assert rkv.INK == "#24272D"
    assert rkv.MUTED == "#687386"
    assert rkv.TEXT_WIDTH_IN == 156 / 25.4
    assert rkv.FIGURE_SIZES["full"] == (rkv.TEXT_WIDTH_IN, 3.55)
    assert rkv.FIGURE_SIZES["wide"] == (rkv.TEXT_WIDTH_IN, 3.05)
    assert rkv.FIGURE_SIZES["compact"] == (rkv.TEXT_WIDTH_IN, 2.55)
    assert rkv.FIGURE_SIZES["square"] == (4.85, 4.35)
    assert mpl.rcParams["mathtext.fontset"] == "stix"
    assert mpl.rcParams["font.size"] == 9.0
    assert mpl.rcParams["axes.titlesize"] == 10.0
    assert mpl.rcParams["xtick.labelsize"] == 8.1


def test_figure_sizes_keep_wide_and_add_dominant_and_half() -> None:
    """Open question 3's resolution: `wide` stays (public API, existing
    publications call new_figure("wide")); `dominant` is spec §15's
    proposed name for the same size, added as an alias rather than a
    replacement, for both themes."""
    for name in available_themes():
        sizes = get_theme(name).figure_sizes
        assert "wide" in sizes
        assert sizes["dominant"] == sizes["wide"]
        assert "half" in sizes
        assert "full" in sizes
        assert "compact" in sizes


def test_grouped_bubble_matrix_uses_shape_as_well_as_colour() -> None:
    data = pd.DataFrame({"x": [1, 2], "y": [2, 1], "group": ["Alpha", "Beta"]})
    figure, axis = rkv.bubble_matrix(
        data, x="x", y="y", xlabel="Impact", ylabel="Effort", group_column="group"
    )
    collections = [item for item in axis.collections if item.get_label() in {"Alpha", "Beta"}]
    assert len(collections) == 2
    assert len({len(item.get_paths()[0].vertices) for item in collections}) == 2
    plt.close(figure)


def test_apply_theme_institutional_research_switches_palette_and_geometry() -> None:
    rkv.apply_theme("institutional-research")
    assert rkv.INK == "#202124"
    assert rkv.MUTED == "#6B7075"
    assert rkv.METRIC == "#18A999"  # MetricAccent / Accent
    # US Letter minus 14mm/14mm margins (themes/reportkit-theme-institutional-research.sty's geometry).
    assert rkv.TEXT_WIDTH_IN == pytest.approx((215.9 - 14 - 14) / 25.4)
    assert rkv.FIGURE_SIZES["full"][0] == pytest.approx(rkv.TEXT_WIDTH_IN)
    assert rkv.FIGURE_SIZES["full"] != (156 / 25.4, 3.55)  # not the default theme's numbers
    assert mpl.rcParams["mathtext.fontset"] == "custom"


def test_institutional_theme_mathtext_matches_resolved_sans_font() -> None:
    """Spec §14's actual fix: under mathtext.fontset="custom", rm/it/bf all
    point at the same resolved sans font apply_theme() put in
    font.sans-serif -- the specific mechanism that prevents a numeric tick
    label rendered via mathtext from picking up a serif glyph (the bug spec
    §14 says was already observed under STIX)."""
    rkv.apply_theme("institutional-research")
    assert mpl.rcParams["mathtext.rm"] == rkv.SANS_FONT
    assert mpl.rcParams["mathtext.it"] == rkv.SANS_FONT
    assert mpl.rcParams["mathtext.bf"] == rkv.SANS_FONT


def test_default_theme_mathtext_untouched() -> None:
    """The default theme's mathtext.fontset stays "stix", unchanged --
    Step 4 fixes serif leakage for the institutional theme specifically
    (spec §14), not for the default theme's pre-existing behavior, which
    would be a silent restyle of every existing publication's charts.
    apply_theme() only sets mathtext.rm/it/bf when mathtext_fontset ==
    "custom" (institutional's) -- under "stix" it leaves them alone, so
    there is nothing meaningful to assert about their value here beyond
    the fontset itself staying "stix" even right after switching away from
    a theme that did set them."""
    rkv.apply_theme("institutional-research")
    rkv.apply_theme("default")
    assert mpl.rcParams["mathtext.fontset"] == "stix"


def test_font_consistency_regression_matches_spec_section_14_checklist() -> None:
    """Renders one figure containing every element spec §14's "Mandatory
    regression" list names -- numeric y ticks, categorical x ticks,
    percentages, negative values, legend, annotation, axis title -- under
    the institutional theme, then verifies the specific defect spec §14
    describes as already observed: numeric-axis tick labels resolving to a
    different font family than categorical-axis tick labels. This can only
    check matplotlib's *configured* font family per text element (get_
    fontfamily()), not the literal rendered glyph -- confirming the actual
    pixels needs Step 5's visual-regression fixture."""
    rkv.apply_theme("institutional-research")
    growth = pd.Series({"FY24A": -12.3, "FY25E": 45.6, "FY26E": 78.2, "FY27E": 100.4})
    fig, ax = rkv.bar_chart(
        growth,
        value_formatter=rkv.percent_formatter(1),
        axis_label="Revenue growth",
    )
    ax.set_title("Regression check")
    ax.legend(["Revenue growth"], loc="upper left")
    ax.annotate("callout", xy=(0, 0))
    fig.canvas.draw()

    xtick_families = {tuple(label.get_fontfamily()) for label in ax.get_xticklabels() if label.get_text()}
    ytick_families = {tuple(label.get_fontfamily()) for label in ax.get_yticklabels() if label.get_text()}
    assert xtick_families, "no categorical x-tick labels rendered"
    assert ytick_families, "no numeric y-tick labels rendered"
    # The regression spec §14 names directly: numeric ticks must not
    # resolve to a different font family than categorical ticks.
    assert xtick_families == ytick_families
    common_family = next(iter(xtick_families))
    assert tuple(ax.title.get_fontfamily()) == common_family
    legend = ax.get_legend()
    assert legend is not None
    for text in legend.get_texts():
        assert tuple(text.get_fontfamily()) == common_family


def test_check_theme_institutional_now_synchronized() -> None:
    """Closes the honest failure Step 1's plan predicted and Step 2/3 pinned
    (test_check_theme_institutional_honestly_fails_until_step4, deleted in
    this step): reportkit.themes.institutional_research.THEME.latex_colors
    now exists and matches
    themes/reportkit-theme-institutional-research.sty's palette exactly."""
    sty_path = REPO / "latex_templates" / "themes" / "reportkit-theme-institutional-research.sty"
    colors = get_theme("institutional-research").latex_colors
    assert rkv.validate_palette_against_latex(sty_path, colors) == []


def test_check_theme_default_still_synchronized() -> None:
    sty_path = REPO / "latex_templates" / "themes" / "reportkit-theme-default.sty"
    colors = get_theme("default").latex_colors
    assert rkv.validate_palette_against_latex(sty_path, colors) == []


def test_validate_palette_against_latex_default_arg_uses_currently_applied_theme() -> None:
    """Backward compatibility for the pre-Step-4 one-argument call shape:
    validate_palette_against_latex(path) with no `colors` still compares
    against whatever LATEX_THEME_COLORS currently is (the module-level
    global apply_theme() reassigns), not a theme this call has to know
    about."""
    rkv.apply_theme("default")
    sty_path = REPO / "latex_templates" / "themes" / "reportkit-theme-default.sty"
    assert rkv.validate_palette_against_latex(sty_path) == []


def test_theme_dataclass_frozen_and_typed() -> None:
    theme = get_theme("default")
    assert isinstance(theme, Theme)
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError is a subclass of AttributeError
        theme.name = "mutated"  # type: ignore[misc]


def test_annotate_point_and_shade_period_follow_theme_switches() -> None:
    """Regression for a latent bug found while making apply_theme() support
    runtime theme-switching: annotate_point's `accent` and shade_period's
    `color` used to be keyword defaults bound directly to the PRIMARY/
    EVIDENCE globals (`accent: str = PRIMARY`), which Python evaluates once
    at function-definition time -- so they silently kept whichever theme
    was active at import time, forever, no matter what apply_theme() did
    afterward. Fixed to resolve the default inside the function body
    instead. This test would have failed against the old signature."""
    rkv.apply_theme("institutional-research")
    institutional_primary = rkv.PRIMARY
    institutional_evidence = rkv.EVIDENCE
    assert institutional_primary != "#2C5E78"  # not the default theme's PRIMARY

    fig, ax = rkv.new_figure("compact")
    rkv.annotate_point(ax, 0, 0, "note")
    arrow_color = ax.texts[-1].arrowprops["color"] if ax.texts[-1].arrowprops else None
    assert arrow_color == institutional_primary

    rkv.shade_period(ax, 0, 1)
    patch = ax.patches[-1]
    assert mpl.colors.to_hex(patch.get_facecolor()) == institutional_evidence.lower()


def test_risk_reward_chart_renders_and_labels_bear_base_bull() -> None:
    """spec §18: the risk/reward chart is generated through reportkit_viz.py
    (this function), not drawn LaTeX-side -- reportkit-equity-research.sty's
    \\bullcase/\\basecase/\\bearcase primitives expect exactly this image to
    arrive as an ordinary \\includegraphics inside an exhibit."""
    rkv.apply_theme("institutional-research")
    dates = pd.date_range("2024-09-01", periods=12, freq=month_end_freq())
    price = pd.Series([150 + i * 3 for i in range(len(dates))], index=dates)
    fig, ax = rkv.risk_reward_chart(
        price, bear=135, base=245, bull=310, current=182.50,
        value_formatter=rkv.currency_formatter(),
    )
    fig.canvas.draw()
    labels = {text.get_text() for text in ax.texts}
    assert labels == {"Bear $135", "Base $245", "Bull $310"}
    # Three dashed reference lines, colored bear=negative/base=accent/
    # bull=warm (see the function's own docstring for why those theme
    # roles, not new bear/base/bull-specific fields).
    hlines = [line for line in ax.get_lines() if line.get_linestyle() == "--"]
    assert len(hlines) == 3
    line_colors = {mpl.colors.to_hex(line.get_color()) for line in hlines}
    assert line_colors == {rkv.DATA_NEGATIVE.lower(), rkv.METRIC.lower(), rkv.DATA_WARM.lower()}


def test_figure_sizes_add_sidebar_square_preset() -> None:
    """§29.3 post-implementation finding: a "sidebar" figure preset (~2in
    square) sized for proportional-data charts (pie/donut) in the ~28%-wide
    sidebar column, present on both themes with a 1:1 aspect ratio."""
    for name in available_themes():
        sizes = get_theme(name).figure_sizes
        assert "sidebar" in sizes
        width, height = sizes["sidebar"]
        assert width == pytest.approx(height)  # square


def test_donut_chart() -> None:
    """Test donut_chart renders without error and produces correct figure."""
    data = {
        "Consulting": 52,
        "Managed Services": 48,
    }
    fig, ax = rkv.donut_chart(
        data,
        title="Revenue Mix",
        size="sidebar",
    )
    assert fig is not None
    assert ax is not None
    # Verify the chart has pie wedges
    assert len(ax.patches) > 0
    plt.close(fig)


def test_donut_chart_with_custom_colors() -> None:
    """Test donut_chart accepts custom colors."""
    data = {"A": 30, "B": 40, "C": 30}
    colors = ["#FF0000", "#00FF00", "#0000FF"]
    fig, ax = rkv.donut_chart(data, colors=colors, size="sidebar")
    assert fig is not None
    assert len(ax.patches) == 3
    plt.close(fig)


def test_donut_chart_color_cycling() -> None:
    """Test donut_chart cycles colors when more slices than colors."""
    data = {f"Slice {i}": i + 1 for i in range(6)}  # 6 slices
    colors = ["#FF0000", "#00FF00"]  # Only 2 colors
    fig, ax = rkv.donut_chart(data, colors=colors, size="sidebar")
    assert len(ax.patches) == 6
    plt.close(fig)


def test_donut_chart_empty_data_raises() -> None:
    """Test donut_chart rejects empty data."""
    with pytest.raises(ValueError, match="data must be non-empty"):
        rkv.donut_chart({})
