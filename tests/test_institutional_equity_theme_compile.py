"""Institutional-theme spec, Step 5: the actual lualatex compile every
prior step's plan flagged as "not performed" (Steps 1-3's ".sty changes
are unverified by compilation"; Step 4's "cannot be from this
environment"). Skips cleanly wherever lualatex is not on PATH (this
session's environment included, via the session-scoped `latex_engine`
fixture in tests/conftest.py) and actually compiles for real wherever it
is.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_institutional_equity_theme_compiles(compile_doc) -> None:
    """A minimal document combining both theme=institutional-research and
    publication-type=equity-research compiles under lualatex -- the exact
    combination spec section 28's Definition of Done names, and the one
    Step 3's implementation plan flagged as the primary "not performed"
    risk (researchfrontpage/researchmain/researchsidebar minipage
    adjacency in particular)."""
    body = r"""
\begin{researchfrontpage}
\researchkicker{Sector / Region}
\researchheadline{Headline text}
\researchdeck{Deck text.}
\begin{ratingstrip}
\ratingitem{Rating}{Overweight}
\ratingitem{Price Target}{\$100}
\end{ratingstrip}
\begin{researchmain}
Main column body text.
\end{researchmain}\begin{researchsidebar}
\begin{analystblock}
\sidebarvalue{Analyst Name}
\end{analystblock}
\end{researchsidebar}
\end{researchfrontpage}
\begin{exhibit}[title={A finding-led title}, source={Fixture data.}]
Exhibit body.
\end{exhibit}
"""
    doc = compile_doc(body, name="institutional_equity_smoke", class_options="theme=institutional-research,publication-type=equity-research")
    assert doc.page_count >= 1


def test_institutional_equity_acceptance_fixture_compiles(compile_doc, latex_engine: str, tmp_path: Path) -> None:
    """Compiles the checked-in acceptance fixture itself (not a re-typed
    excerpt), the same one scripts/acceptance_check.sh's lualatex block
    compiles -- so a regression here and a regression in that shell script
    are the same regression, not two independently-maintained copies of
    "does this fixture still compile"."""
    import shutil
    import subprocess

    fixture = REPO / "latex_templates" / "examples" / "institutional_equity_acceptance_test.tex"
    templates = REPO / "latex_templates"
    for src in (
        list(templates.glob("*.cls"))
        + list(templates.glob("*.def"))
        + list(templates.glob("reportkit-*.tex"))
        + list(templates.glob("*.sty"))
        + list((templates / "themes").glob("*.sty"))
        + list((templates / "publication_types").glob("*.sty"))
    ):
        shutil.copy(src, tmp_path / src.name)
    font_data = REPO / "font_data"
    staged_fonts = tmp_path / "font_data"
    staged_fonts.mkdir()
    for src in font_data.glob("GoogleSans-*.ttf"):
        shutil.copy(src, staged_fonts / src.name)
    shutil.copy(fixture, tmp_path / fixture.name)

    import os

    env = dict(os.environ, LC_ALL="C")
    proc = subprocess.run(
        [latex_engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", fixture.name],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    pdf = tmp_path / fixture.name.replace(".tex", ".pdf")
    if not pdf.exists():
        output = (proc.stdout + "\n" + proc.stderr)[-4000:]
        pytest.fail(f"lualatex produced no PDF for the acceptance fixture (exit {proc.returncode})\n{output}")
