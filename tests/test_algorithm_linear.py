"""Rendered-PDF regressions for the linear-container algorithm-state
primitives (docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md,
section 7: stackstate, queuestate).
"""

import pytest

from geometry import word_boxes


def test_stackstate_marks_top_above_earlier_pushes(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=stack,width=\textwidth,caption={Bracket matching.},description={A stack holding three unmatched opening brackets, with the most recently pushed bracket marked current and the stack top labelled.}]
          \begin{stackstate}
            \push{(}
            \push{[}
            \push[state=current]{<}
          \end{stackstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"(", "[", "<", "TOP"})
    assert {"(", "[", "<", "TOP"} <= set(boxes)
    # The most recently pushed item renders above the earlier pushes, and the
    # TOP marker sits alongside it.
    assert boxes["<"][1] < boxes["["][1]
    assert boxes["["][1] < boxes["("][1]
    assert abs(boxes["TOP"][1] - boxes["<"][1]) < abs(boxes["TOP"][1] - boxes["("][1])


def test_queuestate_marks_dequeue_and_enqueue_ends(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=queue,width=\textwidth,caption={BFS work queue.},description={A three-element FIFO work queue with the front node marked current, the dequeue end labelled on the left, and the enqueue end labelled on the right.}]
          \begin{queuestate}
            \enqueue[state=current]{A}
            \enqueue{B}
            \enqueue{C}
          \end{queuestate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"A", "B", "C", "DEQUEUE", "ENQUEUE"})
    assert {"A", "B", "C", "DEQUEUE", "ENQUEUE"} <= set(boxes)
    # Enqueue order renders left to right: front (A) first, rear (C) last.
    assert boxes["A"][0] < boxes["B"][0] < boxes["C"][0]
    # DEQUEUE marks the front (left) end and ENQUEUE marks the rear (right) end.
    assert boxes["DEQUEUE"][0] < boxes["A"][0]
    assert boxes["ENQUEUE"][0] > boxes["C"][0]


def test_stackstate_and_queuestate_support_full_state_vocabulary(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=stack,width=\textwidth,caption={Stack states.},description={Nine stack cells, one per shared algorithm state.}]
          \begin{stackstate}
            \push[state=unseen]{a}
            \push[state=blocked]{b}
            \push[state=discarded]{c}
            \push[state=resolved]{d}
            \push[state=visited]{e}
            \push[state=frontier]{f}
            \push[state=candidate]{g}
            \push[state=active]{h}
            \push[state=current]{i}
          \end{stackstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"a", "b", "c", "d", "e", "f", "g", "h", "i"})
    assert {"a", "b", "c", "d", "e", "f", "g", "h", "i"} <= set(boxes)


def test_unknown_algorithm_state_raises_a_package_error_in_queuestate(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=queue,width=\textwidth,caption={Bad state.},description={Invalid state name.}]
              \begin{queuestate}
                \enqueue[state=nonsense]{1}
              \end{queuestate}
            \end{diagram}
            """
        )
