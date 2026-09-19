"""Compact front-matter regressions
(docs/superpowers/specs/2026-09-18-algorithm-visuals-fix-sprint-spec.md,
Workstream D2: compact-guide template changes).

`\\RKContents` always clears to a dedicated contents-only page
(`\\clearpage...\\tableofcontents...\\clearpage`). `\\RKCompactContents` is a
condensed alternative meant to sit on the title page itself: it lists
whatever labels the caller gives it (no `\\tableofcontents`/aux-file
dependency, so it renders correctly on the very first compile) and never
forces a page break of its own.
"""

from geometry import word_boxes


def test_compact_contents_does_not_force_a_dedicated_page(compile_doc):
    doc = compile_doc(
        r"""
        Lead-in text before the panel.

        \RKCompactContents{Two pointers, Stack and queue, Topological sort}

        Trailing text after the panel.
        """,
        preamble=r"\usepackage{reportkit-longform}",
    )
    assert len(doc) == 1
    text = doc[0].get_text()
    assert "Lead-in" in text
    assert "POINTERS" in text.upper()
    assert "TOPOLOGICAL" in text.upper()
    assert "Trailing" in text


def test_compact_contents_lists_every_given_label_on_the_same_page(compile_doc):
    doc = compile_doc(
        r"""
        \RKCompactContents{Alpha, Bravo, Charlie, Delta}
        """,
        preamble=r"\usepackage{reportkit-longform}",
    )
    boxes = word_boxes(doc[0], {"ALPHA", "BRAVO", "CHARLIE", "DELTA"})
    assert {"ALPHA", "BRAVO", "CHARLIE", "DELTA"} <= set(boxes)
