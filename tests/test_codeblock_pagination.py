"""Pagination regressions for the `codeblock` environment
(docs/superpowers/specs/2026-09-18-algorithm-visuals-fix-sprint-spec.md,
Workstream D: `keep=auto` pagination guard).

`codeblock`'s fixed `\\RKReserveSpace{8\\baselineskip}` guess only checks
that *some* space remains before starting the box. When a code block is
taller than that fixed guess but still shorter than a fresh page, the box
starts on the current page and then splits mid-listing, leaving its title
on one page and trailing lines on the next (spec S1.2, Page 9/heap row).

`keep=auto` measures the block's actual rendered height and reserves
exactly that much space, so the whole unit either fits or moves to a
fresh page together. A block that is genuinely taller than one full page
still splits (that is the correct outcome per the spec), repeating a
small "(continued)" label at the top of the next part.
"""

import pymupdf
import pytest

from geometry import word_boxes

# One paragraph is one full body-text line at the default reportkit theme's
# text width; 44 repetitions leaves a boundary where a 15-line codeblock's
# title and first lines land on one page while its last lines spill onto
# the next -- calibrated against the default theme by direct compilation
# (see task-3-report.md for the calibration sweep across 40/44/46/48/50
# repetitions).
_FILLER_PARAGRAPH = (
    "Filler line with enough characters to occupy roughly one full text "
    "line at normal body width in this document class.\n\n"
)
_FILLER = _FILLER_PARAGRAPH * 44

_CODE_BODY = "\n".join(f"    step_{i} = {i}" for i in range(1, 16))


def _near_boundary_doc(codeblock_open: str) -> str:
    return (
        "\\setlength{\\parindent}{0pt}\n"
        + _FILLER
        + f"\\begin{{{codeblock_open}\n"
        + "def near_boundary():\n"
        + _CODE_BODY
        + "\n    return None\n"
        + "\\end{codeblock}\n"
    )


def test_codeblock_without_keep_auto_can_split_mid_listing(compile_doc):
    """Diagnostic (Step 1): confirms today's fixed-guess reservation lets a
    code block start on a page it cannot finish, splitting its title away
    from its trailing lines. This documents the pre-existing defect; the
    default (keep omitted) contract is otherwise left unchanged by this
    sprint, so this test asserts the split still happens today.
    """
    doc = compile_doc(_near_boundary_doc("codeblock}{Python}"))
    assert len(doc) >= 2
    pages_text = [doc[i].get_text() for i in range(len(doc))]
    title_pages = {i for i, t in enumerate(pages_text) if "PYTHON" in t}
    last_line_pages = {i for i, t in enumerate(pages_text) if "step_15 = 15" in t}
    assert title_pages and last_line_pages
    # The known defect: the title's page is strictly earlier than the last
    # code line's page, i.e. the block is split mid-listing.
    assert min(title_pages) < max(last_line_pages)


def test_codeblock_keep_auto_keeps_whole_unit_on_one_page(compile_doc):
    """Step 2 (the fix): with `keep=auto`, the same near-boundary scenario
    must move the whole unit (title through last code line) onto a single,
    fresh page instead of splitting mid-listing.
    """
    doc = compile_doc(_near_boundary_doc("codeblock}[][keep=auto]{Python}"))
    pages_text = [doc[i].get_text() for i in range(len(doc))]
    title_pages = {i for i, t in enumerate(pages_text) if "PYTHON" in t}
    last_line_pages = {i for i, t in enumerate(pages_text) if "step_15 = 15" in t}
    assert title_pages and last_line_pages
    assert title_pages == last_line_pages, (
        "keep=auto must move the whole codeblock unit to one page, not split it"
    )


def test_codeblock_keep_auto_oversize_still_splits_with_continuation_label(compile_doc):
    """Step 3: a `keep=auto` block taller than a full fresh page must still
    be allowed to split (the spec's correct outcome for genuinely oversize
    content), and must not hang/error. The continuation must carry a
    minimal "(continued)" label at the top of the next part.
    """
    oversize_body = "\n".join(f"    line_{i} = {i}  # padding" for i in range(1, 90))
    doc = compile_doc(
        "\\begin{codeblock}[][keep=auto]{Python}\n"
        "def oversize():\n" + oversize_body + "\n    return None\n"
        "\\end{codeblock}\n"
    )
    assert len(doc) >= 2
    pages_text = [doc[i].get_text() for i in range(len(doc))]
    assert "line_1 = 1" in pages_text[0]
    assert not all("line_88 = 88" in t for t in [pages_text[0]])
    later_pages = "".join(pages_text[1:])
    assert "line_88 = 88" in later_pages or "line_89 = 89" in later_pages
    assert "(continued)" in later_pages


def test_codeblock_keep_omitted_matches_fixed_reservation_call_sites(compile_doc):
    """Backward compatibility: existing call conventions (`{lang}` and
    `[title]{lang}`, no second bracket) must keep compiling unchanged.
    """
    doc = compile_doc(
        "\\begin{codeblock}{Python}\n"
        "print('a')\n"
        "\\end{codeblock}\n"
        "\\begin{codeblock}[Two-pointer scan]{Python}\n"
        "print('b')\n"
        "\\end{codeblock}\n"
    )
    page = doc[0]
    boxes = word_boxes(page, {"PYTHON"})
    assert "PYTHON" in boxes
