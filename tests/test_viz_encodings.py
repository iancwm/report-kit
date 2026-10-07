"""Operator-theme chart encodings: AC5 and AC6 (machine-checkable part).

These tests inspect Matplotlib artist geometry, so they need neither the
pinned TeX toolchain nor a human. They do not replace the Wave 3 visual
review of the rendered figures.
"""
from __future__ import annotations

import matplotlib as mpl
import pytest

mpl.use("Agg")
pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

import reportkit_viz as rkv  # noqa: E402
from reportkit.themes import get_theme  # noqa: E402
from reportkit.themes.operator import THEME  # noqa: E402

MM_PER_INCH = 25.4


@pytest.fixture(autouse=True)
def _operator_theme():
    rkv.apply_theme("operator")
    yield
    plt.close("all")
    rkv.apply_theme("default")


def _bars(ax) -> list[Rectangle]:
    return [p for p in ax.patches if isinstance(p, Rectangle) and p.get_width() and p.get_height()]


def _luminance(color) -> float:
    r, g, b = mpl.colors.to_rgb(color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------------------------------------------------------------- theme tokens


def test_operator_chart_tokens_declare_non_color_encodings() -> None:
    charts = get_theme("operator").charts
    assert charts is THEME.charts
    assert len(charts.hatches) >= 2 and len(charts.dashes) >= 2
    # One solid fill (the inference layer) and at least one real hatch.
    assert "" in charts.hatches
    assert any(h for h in charts.hatches)
    # Dashes must be mutually distinguishable beyond the first two entries,
    # otherwise series are separated by colour alone.
    assert len(set(charts.dashes[1:])) >= 2


def test_apply_theme_publishes_encodings_and_default_leaves_them_empty() -> None:
    from reportkit.viz import core

    assert core.CHART_HATCHES == tuple(THEME.charts.hatches)
    assert core.CHART_DASHES == tuple(THEME.charts.dashes)
    rkv.apply_theme("default")
    assert core.CHART_HATCHES == ()
    assert core.CHART_DASHES == ()


def test_existing_theme_stacked_bar_has_no_hatch() -> None:
    rkv.apply_theme("default")
    frame = pd.DataFrame({"A": [1.0, 2.0], "B": [2.0, 1.0]}, index=["x", "y"])
    _fig, ax = rkv.stacked_bar_chart(frame)
    assert all(not bar.get_hatch() for bar in _bars(ax))


# ----------------------------------------------------------------------- AC5


def _evidence_chart(horizontal: bool = True):
    evidence = pd.Series({"Kestrel Loom": 9, "Morrow Dock": 6, "Cinder Relay": 7})
    return rkv.bar_chart(
        evidence,
        horizontal=horizontal,
        value_formatter="integer",
        value_labels="outside",
        size="full",
    )


@pytest.mark.parametrize("horizontal", [True, False])
def test_ac5_outside_labels_clear_bars_and_stay_in_figure(horizontal: bool) -> None:
    fig, ax = _evidence_chart(horizontal)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    labels = [t for t in ax.texts if t.get_text().strip()]
    bars = _bars(ax)
    assert len(labels) == len(bars) == 3

    figure_box = fig.bbox
    axes_box = ax.get_window_extent(renderer)
    for label, bar in zip(labels, bars):
        extent = label.get_window_extent(renderer)
        bar_box = bar.get_window_extent(renderer)
        assert not extent.overlaps(bar_box), f"label {label.get_text()!r} touches its bar"
        # The label starts past the bar end (right of it, or above it).
        if horizontal:
            assert extent.x0 >= bar_box.x1 - 0.5
        else:
            assert extent.y0 >= bar_box.y1 - 0.5
        # Entirely inside the figure and inside the axes box (axis limits
        # were expanded to make room).
        assert figure_box.x0 <= extent.x0 and extent.x1 <= figure_box.x1
        assert figure_box.y0 <= extent.y0 and extent.y1 <= figure_box.y1
        assert axes_box.x0 - 0.5 <= extent.x0 and extent.x1 <= axes_box.x1 + 0.5
        assert axes_box.y0 - 0.5 <= extent.y0 and extent.y1 <= axes_box.y1 + 0.5


def test_ac5_labels_carry_formatted_values_in_input_order() -> None:
    _fig, ax = _evidence_chart(True)
    assert [t.get_text() for t in ax.texts] == ["9", "6", "7"]


def test_ac5_invalid_label_placement_is_rejected() -> None:
    with pytest.raises(ValueError, match="value_labels"):
        rkv.bar_chart({"a": 1}, value_labels="inside")


def test_ac5_non_finite_values_cannot_be_labelled() -> None:
    with pytest.raises(ValueError, match="finite"):
        rkv.bar_chart({"a": float("nan"), "b": 1.0}, value_labels="outside")


# ----------------------------------------------------------------------- AC6


def _cost_frame() -> pd.DataFrame:
    # Mirrors the fictional Figure 5 data in the operator fixture.
    return pd.DataFrame(
        {
            "Review": [7.2, 9.6, 10.8, 12.0],
            "Inference": [1.8, 2.6, 3.4, 4.1],
        },
        index=["Small pilot", "Routine month", "Busy month", "Cap month"],
    )


def test_ac6_review_hatched_inference_solid() -> None:
    _fig, ax = rkv.stacked_bar_chart(_cost_frame(), value_formatter=rkv.currency_formatter())
    bars = _bars(ax)
    assert len(bars) == 8
    review, inference = bars[:4], bars[4:]
    assert all(bar.get_hatch() == THEME.charts.hatches[0] and bar.get_hatch() for bar in review)
    assert all(not bar.get_hatch() for bar in inference)
    # Inference is a different fill to the hatched layer, not just a hatch.
    assert review[0].get_facecolor() != inference[0].get_facecolor()


def test_ac6_hatched_segment_survives_greyscale() -> None:
    """The two layers must stay separable without colour: hatch ink on a
    surface fill versus a solid dark fill."""
    _fig, ax = rkv.stacked_bar_chart(_cost_frame())
    bars = _bars(ax)
    review_fill = _luminance(bars[0].get_facecolor())
    inference_fill = _luminance(bars[4].get_facecolor())
    assert review_fill - inference_fill > 0.3
    assert bars[0].get_hatch() and not bars[4].get_hatch()


def test_ac6_stack_order_is_bottom_to_top_as_given() -> None:
    _fig, ax = rkv.stacked_bar_chart(_cost_frame())
    bars = _bars(ax)
    for review, inference in zip(bars[:4], bars[4:]):
        assert review.get_y() == 0
        assert inference.get_y() == pytest.approx(review.get_height())


def test_ac6_smallest_inference_segment_is_at_least_2mm_tall() -> None:
    fig, ax = rkv.stacked_bar_chart(_cost_frame(), value_formatter=rkv.currency_formatter())
    fig.canvas.draw()
    inference = _bars(ax)[4:]
    heights_mm = [
        bar.get_window_extent().height / fig.dpi * MM_PER_INCH for bar in inference
    ]
    assert min(heights_mm) >= 2.0, f"smallest inference segment is {min(heights_mm):.2f} mm"


def test_ac6_nothing_clipped_by_axes_or_figure() -> None:
    fig, ax = rkv.stacked_bar_chart(_cost_frame(), value_formatter=rkv.currency_formatter())
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    axes_box = ax.get_window_extent(renderer)
    for bar in _bars(ax):
        box = bar.get_window_extent(renderer)
        assert axes_box.x0 - 0.5 <= box.x0 and box.x1 <= axes_box.x1 + 0.5
        assert axes_box.y0 - 0.5 <= box.y0 and box.y1 <= axes_box.y1 + 0.5
    assert fig.bbox.x0 <= axes_box.x0 and axes_box.x1 <= fig.bbox.x1


def test_ac6_horizontal_stack_keeps_encodings() -> None:
    _fig, ax = rkv.stacked_bar_chart(_cost_frame(), horizontal=True)
    bars = _bars(ax)
    assert all(b.get_hatch() for b in bars[:4])
    assert all(not b.get_hatch() for b in bars[4:])


def test_stacked_bar_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        rkv.stacked_bar_chart(pd.DataFrame())
    with pytest.raises(ValueError, match="finite"):
        rkv.stacked_bar_chart(pd.DataFrame({"A": [float("inf")]}, index=["x"]))
    with pytest.raises(ValueError, match="numeric"):
        rkv.stacked_bar_chart(pd.DataFrame({"A": ["a"]}, index=["x"]))


def test_stacked_bar_sort_orders_by_total() -> None:
    frame = pd.DataFrame({"A": [5.0, 1.0, 3.0]}, index=["big", "small", "mid"])
    _fig, ax = rkv.stacked_bar_chart(frame, sort=True)
    assert [t.get_text() for t in ax.get_xticklabels()] == ["small", "mid", "big"]


# ------------------------------------------------------------------ line chart


def _policy_frame() -> pd.DataFrame:
    attempts = [0, 16, 32, 48, 64, 80, 96]
    return pd.DataFrame(
        {
            "Local ledger": [18.0 + 0.12 * n for n in attempts],
            "Managed credits": [24.0 + 0.12 * max(n - 64, 0) for n in attempts],
            "Hosted queue + review": [31.0 + 0.10 * n for n in attempts],
        },
        index=attempts,
    )


def test_line_chart_series_have_distinct_dash_styles() -> None:
    _fig, ax = rkv.line_chart(_policy_frame())
    lines = [ln for ln in ax.get_lines() if len(ln.get_xdata()) == 7]
    assert len(lines) == 3
    styles = [ln.get_linestyle() for ln in lines]
    # Grayscale safety: each series must have its own line pattern.
    keys = {(mpl.colors.to_hex(ln.get_color()), ln.get_linestyle()) for ln in lines}
    assert len(keys) == 3
    assert len(set(styles)) == 3


def test_line_chart_dash_styles_follow_theme_tokens() -> None:
    _fig, ax = rkv.line_chart(_policy_frame())
    lines = [ln for ln in ax.get_lines() if len(ln.get_xdata()) == 7]
    expected = [mpl.lines.Line2D([], [], linestyle=d).get_linestyle() for d in THEME.charts.dashes[:3]]
    assert [ln.get_linestyle() for ln in lines] == expected


def test_line_chart_marker_is_labelled_and_inside_data_range() -> None:
    fig, ax = rkv.line_chart(
        _policy_frame(), vertical_marker=64, vertical_marker_label="64-credit allowance"
    )
    vertical = [ln for ln in ax.get_lines() if len(ln.get_xdata()) == 2 and ln.get_xdata()[0] == 64]
    assert len(vertical) == 1
    assert ax.get_xlim()[0] <= 64 <= ax.get_xlim()[1]
    assert [t.get_text() for t in ax.texts] == ["64-credit allowance"]


def test_line_chart_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="numeric data index"):
        rkv.line_chart(pd.DataFrame({"A": [1.0, 2.0]}, index=["a", "b"]))
    with pytest.raises(ValueError, match="requires vertical_marker"):
        rkv.line_chart(_policy_frame(), vertical_marker_label="x")
    with pytest.raises(ValueError, match="finite"):
        rkv.line_chart(_policy_frame(), vertical_marker=float("nan"))
    wide = pd.DataFrame({f"s{i}": [1.0, 2.0] for i in range(7)}, index=[0, 1])
    with pytest.raises(ValueError, match="at most six"):
        rkv.line_chart(wide)


def test_stacked_bar_contract_example_runs() -> None:
    from reportkit.registry import generate_registry

    example = generate_registry()["primitives"]["chart"]["stacked_bar_chart"]["example"]
    exec(example, {"rkv": rkv, "pd": pd})  # noqa: S102 - repository-owned example, self-contained


def test_line_chart_accepts_series() -> None:
    _fig, ax = rkv.line_chart(pd.Series([1.0, 2.0, 3.0], index=[0, 1, 2], name="Cost"))
    assert len(ax.get_lines()) == 1
