from geometry import word_boxes

MACHINE = r"""
\begin{diagram}[width=\textwidth,caption={Task recovery states.}]
  \begin{reportstate}
    \state{sched}{Scheduled}
    \state{run}{Running}
    \terminalstate{ok}{Succeeded}
    \terminalstate{fail}{Failed}
    \transition{sched}{run}{start}
    \transition{run}{ok}{complete}
    \transition{run}{fail}{give up}
    \selfloop{run}{retry}
  \end{reportstate}
\end{diagram}
"""


def test_states_and_transitions_render(compile_doc):
    page = compile_doc(MACHINE)[0]
    boxes = word_boxes(page, {"Scheduled", "Running", "Succeeded", "Failed"})
    assert set(boxes) == {"Scheduled", "Running", "Succeeded", "Failed"}
    assert [boxes[label][0] for label in ("Scheduled", "Running", "Succeeded", "Failed")] == sorted(box[0] for box in boxes.values())
    text = page.get_text()
    assert all(label in text for label in ("start", "complete", "give up", "retry"))
