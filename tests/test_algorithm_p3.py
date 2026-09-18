"""Static and contract regressions for the P3 algorithm-state extensions."""
from __future__ import annotations

from pathlib import Path

from geometry import node_rects
from reportkit.registry import generate_registry


REPO = Path(__file__).resolve().parents[1]
P3 = REPO / "latex_templates" / "reportkit-algorithm-p3.sty"


def test_p3_primitives_compile_and_render_geometry(compile_doc) -> None:
    document = compile_doc(
        r"""
        \begin{diagram}[type=join,width=\textwidth,caption={Hash join.},description={Two inputs feed a hash join, producing one matched output and discarding one unmatched key.}]
          \begin{joinstate}
            \joininput{left}{Orders}
            \joininput{right}{Customers}
            \hashbucket[state=active]{customer\_id}{C42}
            \joinmatch{customer\_id}{C42}
            \joinunmatched{right}{C99}
            \joinoutput{Joined rows}
          \end{joinstate}
        \end{diagram}
        \begin{diagram}[type=union-find,width=\textwidth,caption={Union/find.},description={A disjoint-set forest with a parent edge, a union operation, and a find path.}]
          \begin{unionfindstate}[columns=3]
            \ufnode{A}{A}
            \ufnode{B}{B}
            \ufnode{C}{C}
            \parent{B}{A}
            \union{A}{C}
            \findpath{B}{A}
          \end{unionfindstate}
        \end{diagram}
        \begin{diagram}[type=linked-list,width=\textwidth,caption={Linked list.},description={A linked list with explicit head and tail markers.}]
          \begin{linkedliststate}
            \listnode{a}{A}
            \listnode[state=current]{b}{B}
            \listnode{c}{C}
            \nextlink{a}{b}
            \nextlink{b}{c}
            \head{a}
            \tail{c}
          \end{linkedliststate}
        \end{diagram}
        \begin{diagram}[type=recursion,width=\textwidth,caption={Recursion.},description={A memoized recursive call tree with arguments and return values.}]
          \begin{recursiontree}[columns=2]
            \recursionnode[arguments={n=2},state=current,memoized]{f2}{fib}{1}
            \recursionnode[arguments={n=1}]{f1}{fib}{1}
            \recursionedge{f2}{f1}
          \end{recursiontree}
        \end{diagram}
        """
    )
    # The four environments span multiple diagrams and may paginate. Their
    # node rectangles are the stable rendered-PDF signal; text extraction can
    # split transformed TikZ labels into individual glyphs.
    rendered_rects = sum(len(node_rects(page, min_width=20.0)) for page in document)
    assert rendered_rects >= 10


def test_algorithm_viz_loads_the_p3_extension_module() -> None:
    viz = (REPO / "latex_templates" / "reportkit-algorithm-viz.sty").read_text(encoding="utf-8")
    assert r"\RequirePackage{reportkit-algorithm-p3}" in viz


def test_p3_module_declares_all_figure_families_and_public_aliases() -> None:
    text = P3.read_text(encoding="utf-8")
    for environment in ("joinstate", "unionfindstate", "linkedliststate", "recursiontree"):
        assert rf"\NewDocumentEnvironment{{{environment}}}" in text
    for command in (
        "joininput", "hashbucket", "joinmatch", "joinunmatched", "joinoutput",
        "ufnode", "parent", "union", "findpath",
        "listnode", "nextlink", "head", "tail",
        "recursionnode", "recursionedge",
    ):
        assert rf"\NewDocumentCommand{{\{command}}}" in text
    for alias in (
        "hashindex", "joinpair", "joinresult", "findoperation",
        "linkednode", "listitem", "listlink", "nextpointer",
        "recursioncall", "recursionroot", "recursionlink", "recursionbranch",
    ):
        assert rf"\let\{alias}" in text


def test_p3_registry_has_four_figures_and_fifteen_commands() -> None:
    registry = generate_registry(REPO, strict=True)
    assert {
        name for name in registry["primitives"]["figure"]
        if name in {"joinstate", "unionfindstate", "linkedliststate", "recursiontree"}
    } == {"joinstate", "unionfindstate", "linkedliststate", "recursiontree"}
    assert {
        name for name in registry["primitives"]["command"]
        if registry["primitives"]["command"][name]["source"]["file"] == "latex_templates/reportkit-algorithm-p3.sty"
    } == {
        "joininput", "hashbucket", "joinmatch", "joinunmatched", "joinoutput",
        "ufnode", "parent", "union", "findpath",
        "listnode", "nextlink", "head", "tail",
        "recursionnode", "recursionedge",
    }
