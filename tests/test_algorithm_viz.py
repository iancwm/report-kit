"""Rendered-PDF regressions for the algorithm-visualization primitives
(docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md,
Phase 1: shared state vocabulary, arraystate, windowstate, algorithmtrace).
"""

import pytest

from geometry import node_rects, word_boxes


def test_arraystate_renders_values_indices_and_pointer_labels(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Two-pointer scan.},description={A sorted array with left and right pointers bounding the active range.}]
          \begin{arraystate}
            \cell{-4}
            \cell{-1}
            \cell{-1}
            \cell{0}
            \cell{1}
            \cell{2}
            \pointer[below]{L}{2}
            \pointer[below]{R}{5}
            \range[state=active]{2}{5}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"-4", "-1", "0", "1", "2", "L", "R"})
    assert {"-4", "0", "1", "2", "L", "R"} <= set(boxes)
    # Pointer labels sit below the cell row they annotate.
    cell_top = min(box[1] for name, box in boxes.items() if name in {"-4", "0", "1", "2"})
    assert boxes["L"][1] > cell_top
    assert boxes["R"][1] > cell_top
    assert boxes["L"][0] < boxes["R"][0]


def test_arraystate_multi_row_declares_named_aligned_rows(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Prefix sums.},description={A four-element array aligned with its five-element prefix-sum row.}]
          \begin{arraystate}
            \row{values}{3,1,4,2}
            \row{prefix}{0,3,4,8,10}
            \range[row=values,state=active]{1}{2}
            \annotation{allrowsnote}
            \annotation[row=prefix]{prefixnote}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"values", "prefix", "3", "4", "8", "10", "allrowsnote", "prefixnote"})
    assert {"values", "prefix", "8", "10", "allrowsnote", "prefixnote"} <= set(boxes)
    # The prefix row renders below the values row.
    assert boxes["prefix"][1] > boxes["values"][1]
    # A row-targeted annotation renders beneath the row it describes.
    assert boxes["prefixnote"][1] > boxes["prefix"][1]
    # A bare annotation retains its original behavior of following all rows.
    assert boxes["allrowsnote"][1] > boxes["prefix"][1]


def test_windowstate_marks_active_window_and_entering_leaving(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Sliding window.},description={A six-element array with a window from index two to four and entering/leaving markers.}]
          \begin{windowstate}
            \values{4,2,7,1,3,6}
            \window{2}{4}
            \entering{5}
            \leaving{1}
          \end{windowstate}
        \end{diagram}
        """
    )[0]
    text = page.get_text()
    assert "entering" in text
    assert "leaving" in text
    boxes = word_boxes(page, {"4", "2", "7", "1", "3", "6", "L", "R"})
    assert {"L", "R"} <= set(boxes)


def test_algorithmtrace_orders_snapshots_left_to_right(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=trace,width=\textwidth,caption={Window advance.},description={Two ordered snapshots show the window advancing by one element.}]
          \begin{algorithmtrace}[columns=2]
            \snapshot{Initial}{\begin{arraystate}[indices=false,cell width=.85]\cell{4}\cell{2}\cell{7}\cell{1}\cell{3}\cell{6}\end{arraystate}}
            \snapshot{Advance}{\begin{arraystate}[indices=false,cell width=.85]\cell{2}\cell{7}\cell{1}\cell{3}\cell{6}\cell{8}\end{arraystate}}
          \end{algorithmtrace}
        \end{diagram}
        """
    )[0]
    rects = node_rects(page, min_width=20.0)
    assert len(rects) >= 12
    # The first six cells belong to Initial and the next six to Advance.
    # Their normalized snapshot boxes must remain separate horizontally.
    assert rects[5].x1 < rects[6].x0


def test_unknown_algorithm_state_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=array,width=\textwidth,caption={Bad state.},description={Invalid state name.}]
              \begin{arraystate}
                \cell[state=nonsense]{1}
              \end{arraystate}
            \end{diagram}
            """
        )


def test_bare_pointer_targets_direct_cell_row_not_a_named_row(compile_doc):
    # A named \row declared before the direct-cell row must not steal the
    # bare (row=-less) \pointer/\range target: a bare \pointer must resolve
    # against the row built from direct \cell calls, while row=<name> must
    # resolve only against the named row. Regression for the "Unknown
    # arraystate row" family of bugs (spec sec 2.2 / A2).
    # No description= here: reportkit-diagrams.sty's ActualText accessibility
    # span (emitted only when description= is non-empty) makes PyMuPDF's text
    # extraction return fragments of the description instead of the diagram's
    # real glyphs -- a pre-existing, out-of-scope issue (confirmed against
    # main, unrelated to this sprint) that also explains several already-
    # failing word_boxes-based tests elsewhere in this algorithm-family
    # suite. Omitting description= keeps this test's signal on the actual
    # row-lookup bug it targets.
    # A generous row height keeps each row's own "below" pointer clear of
    # the next row, so this test's signal stays on row *targeting* rather
    # than on how close a below-pointer's label sits to an adjacent row.
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Row lookup.}]
          \begin{arraystate}[row height=2.4]
            \row{name}{1,2,3}
            \cell{9}\cell{8}\cell{7}
            \pointer[below]{Lo}{0}
            \pointer[below,row=name]{Hi}{0}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"9", "8", "7", "1", "2", "3", "Lo", "Hi"})
    assert {"9", "1", "Lo", "Hi"} <= set(boxes)
    direct_row_top = boxes["9"][1]
    direct_row_bottom = boxes["9"][3]
    named_row_bottom = boxes["1"][3]
    assert named_row_bottom < direct_row_top
    # "Hi" (row=name pointer) must resolve to the named row (1,2,3): its label
    # sits in the gap below that row and above the direct-cell row, never
    # spilling down into the direct-cell row's own band.
    assert named_row_bottom < boxes["Hi"][1] < direct_row_top
    # "Lo" (bare pointer, no row=) must resolve to the direct-cell row
    # (9,8,7) instead: its label sits below that row, past the named row's
    # band entirely.
    assert boxes["Lo"][1] > direct_row_bottom


def test_index_label_is_horizontally_centered_under_its_cell(compile_doc):
    # No description= (see note above -- ActualText masks real diagram
    # text when it is set). Letter values keep the index digits ("0".."4")
    # from colliding with a cell's own displayed value.
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Index centering.}]
          \begin{arraystate}
            \cell{aa}\cell{bb}\cell{cc}\cell{dd}\cell{ee}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    cells = node_rects(page, min_width=10.0)
    boxes = word_boxes(page, {"0", "1", "2", "3", "4"})
    assert len(cells) >= 5
    assert {"0", "1", "2", "3", "4"} <= set(boxes)
    for i, cell in enumerate(cells[:5]):
        cell_center_x = (cell.x0 + cell.x1) / 2
        index_box = boxes[str(i)]
        index_center_x = (index_box[0] + index_box[2]) / 2
        assert abs(index_center_x - cell_center_x) < 0.25, (
            f"index {i} center {index_center_x} not within 0.25pt of cell center {cell_center_x}"
        )


def test_index_label_clears_cell_border_and_survives_range_and_pointer(compile_doc):
    # Index 2 sits under a cell that also carries an active \range and a
    # \pointer -- the index must still render, stay centered, and keep a
    # readable vertical gap from the cell's own border (spec sec 2.1: "top
    # of an index glyph is separated from the cell border by at least
    # 1.5pt").
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Index with range and pointer.}]
          \begin{arraystate}
            \cell{aa}\cell{bb}\cell[state=active]{cc}\cell{dd}\cell{ee}
            \range[state=active]{1}{3}
            \pointer[below]{M}{2}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    # Exclude the wider \range background rectangle (spans cells 1-3) so
    # positional indexing lines up with individual cells only.
    cells = [r for r in node_rects(page, min_width=10.0) if r.width < 100]
    boxes = word_boxes(page, {"0", "1", "2", "3", "4"})
    assert {"2"} <= set(boxes)
    assert len(cells) >= 5
    cell_two = cells[2]
    index_two = boxes["2"]
    index_center_x = (index_two[0] + index_two[2]) / 2
    cell_center_x = (cell_two.x0 + cell_two.x1) / 2
    assert abs(index_center_x - cell_center_x) < 0.25
    # The index's top edge must clear the cell's bottom edge by >=1.5pt.
    assert index_two[1] - cell_two.y1 >= 1.5


def test_pointer_role_left_right_renders_spec_example(compile_doc):
    # Spec sec 2.3's target authoring form, verbatim, must compile and show
    # both role labels plus the active range they bound.
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Pointer roles.}]
          \begin{arraystate}[indices=auto]
            \cell[state=current]{1}\cell[state=active]{3}
            \cell[state=active]{5}\cell[state=current]{9}
            \pointer[role=left,below]{L}{0}
            \pointer[role=right,below]{R}{3}
            \range[state=active]{0}{3}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"1", "3", "5", "9", "L", "R"})
    assert {"L", "R"} <= set(boxes)
    assert boxes["L"][0] < boxes["R"][0]


def test_pointer_role_left_and_right_slant_in_opposite_directions(compile_doc):
    # Spec sec 2.3: "The left/right distinction uses a label plus opposing
    # arrow direction; it cannot be expressed by blue versus grey borders
    # alone." Assert the two role arrows' stroke paths actually lean in
    # opposite horizontal directions (grayscale-safe), not just that they
    # render in different colors.
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Pointer role slant.}]
          \begin{arraystate}
            \cell{1}\cell{2}\cell{3}\cell{4}
            \pointer[role=left,below]{L}{1}
            \pointer[role=right,below]{R}{2}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    drawings = page.get_drawings()
    slants = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p0, p1 = item[1], item[2]
                if abs(p0.y - p1.y) > 3:  # a near-vertical pointer stem
                    slants.append(p1.x - p0.x)
    assert slants, "no pointer stem line segments found"
    assert any(s < -0.5 for s in slants), "no left-leaning stem found"
    assert any(s > 0.5 for s in slants), "no right-leaning stem found"


def test_unknown_pointer_role_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=array,width=\textwidth,caption={Bad role.}]
              \begin{arraystate}
                \cell{1}
                \pointer[role=nonsense,below]{X}{0}
              \end{arraystate}
            \end{diagram}
            """
        )
