"""Rendered-PDF regressions for the width-aware and positioned primitives."""

import pytest

from geometry import node_rects, word_boxes


def assert_on_page(page, boxes):
    for box in boxes.values():
        assert page.rect.contains(box)


def test_five_column_swimlane_stays_inside_its_declared_process_width(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[width=\textwidth,caption={Five columns.}]
          \begin{reportswimlane}[lanes={User,Frontend,Backend,Reviewer},width=12.2,columns=5,node width=18mm]
            \lanestep{a}{User}{Request}{1}
            \lanestep{b}{Frontend}{Validate}{2}
            \lanestep{c}{Backend}{Enrich}{3}
            \lanestep{d}{Reviewer}{Review}{4}
            \lanestep{e}{Backend}{Publish}{5}
          \end{reportswimlane}
        \end{diagram}
        """
    )[0]
    labels = ("Request", "Validate", "Enrich", "Review", "Publish")
    boxes = word_boxes(page, set(labels))
    assert set(boxes) == set(labels)
    assert [boxes[label][0] for label in labels] == sorted(box[0] for box in boxes.values())
    rails = [drawing["rect"] for drawing in page.get_drawings() if drawing["rect"].width > 200 and drawing["rect"].height < 2]
    assert rails
    process_left = max(rail.x0 for rail in rails)
    process_right = min(rail.x1 for rail in rails)
    nodes = sorted(node_rects(page, min_width=40), key=lambda node: node.x0)
    assert len(nodes) == 5
    edge_tolerance = 0.75
    assert all(
        process_left - edge_tolerance <= node.x0
        and node.x1 <= process_right + edge_tolerance
        for node in nodes
    )
    centers = [node.x0 + node.width / 2 for node in nodes]
    gaps = [right - left for left, right in zip(centers, centers[1:])]
    expected_pitch = (process_right - process_left - nodes[0].width) / 4
    assert gaps == pytest.approx([expected_pitch] * 4, rel=0.08)
    assert_on_page(page, boxes)


def test_positioned_state_branches_and_routed_labels_render(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[width=\textwidth,caption={Retry state.}]
          \begin{reportstate}
            \stateat{queued}{0}{0}{Queued}
            \stateat{running}{3.8}{0}{Running}
            \terminalstateat{done}{7.6}{1.8}{Succeeded}
            \terminalstateat{failed}{7.6}{-1.8}{Failed}
            \transition{queued}{running}{start}
            \transition[route={bend left=42},label-position=above]{running}{queued}{retry}
            \transition[route=orthogonal,label-position=above]{running}{done}{complete}
            \transition[route=orthogonal,label-position=below]{running}{failed}{give up}
          \end{reportstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"Queued", "Running", "Succeeded", "Failed"})
    assert set(boxes) == {"Queued", "Running", "Succeeded", "Failed"}
    assert boxes["Succeeded"][1] < boxes["Running"][1] < boxes["Failed"][1]
    assert all(label in page.get_text() for label in ("start", "retry", "complete", "give", "up"))
    assert_on_page(page, boxes)


def test_positioned_flow_dag_renders_validation_branch(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[width=\textwidth,caption={Validation DAG.}]
          \begin{reportflow}
            \stepat{extract}{0}{0}{Extract}
            \stepat{validate}{3.5}{0}{Validate}
            \stepat{load}{7}{0}{Load}
            \stepat{publish}{10.5}{0}{Publish}
            \stepat{error}{3.5}{-2}{Validation error}
            \stepat{blocked}{7}{-2}{Blocked}
            \flowedge[label=rows]{extract}{validate}
            \flowedge[label=valid]{validate}{load}
            \flowedge[label=ready]{load}{publish}
            \flowedge[route={bend right=24},label-position=left,label=invalid]{validate}{error}
            \flowedge[label=blocked]{error}{blocked}
          \end{reportflow}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"Extract", "Validate", "Load", "Publish", "Validation", "Blocked"})
    assert set(boxes) == {"Extract", "Validate", "Load", "Publish", "Validation", "Blocked"}
    assert boxes["Validation"][1] > boxes["Validate"][1]
    assert all(label in page.get_text() for label in ("rows", "valid", "ready", "invalid", "blocked"))
    assert_on_page(page, boxes)


def test_architecture_annotation_is_rendered_inside_the_diagram_bounds(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[width=\textwidth,caption={Annotated architecture.}]
          \begin{reportarchitecture}[width=15.2,annotation={One product may span layers; ownership and exit planning remain explicit.},annotation-position=top]
            \layer{Experience}{Reader application, Author workspace}
            \layer{Services}{Report service, Validation service}
            \layer{Data}{Source store, Publication archive}
          \end{reportarchitecture}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"ownership", "Experience", "Services", "Data"})
    assert set(boxes) == {"ownership", "Experience", "Services", "Data"}
    assert boxes["ownership"][1] < boxes["Experience"][1]
    assert_on_page(page, boxes)


def test_timeline_marker_labels_avoid_track_name_and_page_boundary(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[width=\textwidth,caption={Timeline labels.}]
          \begin{reporttimeline}[tracks={Event time},span=12]
            \event{Event time}{.18}{A}
            \event{Event time}{.84}{B}
            \watermark[label-position=above,label-width=24mm]{Event time}{.08}{allowed lateness begins}
            \watermark[label-position=left,label-width=20mm]{Event time}{.96}{window endpoint}
          \end{reporttimeline}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"Event", "allowed", "window", "endpoint"})
    assert set(boxes) == {"Event", "allowed", "window", "endpoint"}
    assert boxes["allowed"][1] < boxes["Event"][1]
    assert boxes["endpoint"][0] < page.rect.x1
    assert_on_page(page, boxes)


def test_dated_roadmap_below_arrow_starts_below_wrapped_period_label(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[width=\textwidth,caption={Dated roadmap.}]
          \begin{reportroadmap}[mode=dated]
            \period{2026 Q4 governance and controls}
            \period{2027 Q1}
            \milestone{2026 Q4 governance and controls}{Design}
          \end{reportroadmap}
        \end{diagram}
        """
    )[0]
    period_words = word_boxes(page, {"2026", "Q4", "gover-", "nance", "controls"})
    assert set(period_words) == {"2026", "Q4", "gover-", "nance", "controls"}
    period_bottom = max(box[3] for box in period_words.values())
    period_center = (min(box[0] for box in period_words.values()) + max(box[2] for box in period_words.values())) / 2
    arrows = [
        drawing["rect"]
        for drawing in page.get_drawings()
        if drawing["rect"].height > 10
        and drawing["rect"].width < 4
        and abs((drawing["rect"].x0 + drawing["rect"].x1) / 2 - period_center) < 8
    ]
    assert arrows
    assert all(arrow.y0 >= period_bottom for arrow in arrows)
