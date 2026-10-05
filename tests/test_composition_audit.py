"""Regression coverage for Pandoc table furniture in composition audits."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from reportkit.composition_audit import audit_source
from reportkit.target import TargetState


TABLE = r"""\begin{longtable}[]{@{}p{0.4\linewidth}p{0.6\linewidth}@{}}
\begin{minipage}[b]{\linewidth}\raggedright
Owner
\end{minipage} & \begin{minipage}[b]{\linewidth}\raggedright
Action
\end{minipage} \\
\endhead
\begin{minipage}[t]{\linewidth}\raggedright
Team
\end{minipage} & \begin{minipage}[t]{\linewidth}\raggedright
Review evidence
\end{minipage} \\
\end{longtable}
"""
MINIPAGE = r"\begin{minipage}{\linewidth}Author layout\end{minipage}"


def _audit(tmp_path: Path, theme: str, source_mode: str, body: str) -> dict:
    tex = tmp_path / "publication.tex"
    tex.write_text("\\begin{document}\n" + body + "\n\\end{document}\n", encoding="utf-8")
    brief = tmp_path / "composition-brief.json"
    brief.write_text(json.dumps({"visual_reference": "Regression fixture"}), encoding="utf-8")
    state = TargetState(
        publication_type="technical-report", theme=theme, renderer="paged",
        source_mode=source_mode, main=tex.name, declared_by="publication.yaml",
        intent=None, require_declared=True, source_root=tmp_path,
    )
    return audit_source(tex, brief, state)


@pytest.mark.parametrize("theme", ["default", "operator"])
def test_pandoc_table_minipages_pass_composition_audit(tmp_path: Path, theme: str) -> None:
    # Multiple tables must each be excluded without hiding text between them.
    result = _audit(tmp_path, theme, "markdown", TABLE + "Prose\n" + TABLE)
    assert result["passed"] is True
    assert not any(item["code"] == "RK_LOCAL_STYLE" for item in result["diagnostics"])


@pytest.mark.parametrize("theme", ["default", "operator"])
@pytest.mark.parametrize("source_mode", ["tex", "markdown"])
@pytest.mark.parametrize("position", ["before", "between", "after", "fragment"])
def test_author_minipage_outside_tables_is_still_blocking(
    tmp_path: Path, theme: str, source_mode: str, position: str,
) -> None:
    if position == "fragment":
        (tmp_path / "layout.tex").write_text(MINIPAGE, encoding="utf-8")
        body = TABLE + r"\input{layout}" + TABLE
    else:
        body = {
            "before": MINIPAGE + TABLE,
            "between": TABLE + MINIPAGE + TABLE,
            "after": TABLE + MINIPAGE,
        }[position]
    result = _audit(tmp_path, theme, source_mode, body)
    assert result["passed"] is False
    error = next(item for item in result["diagnostics"] if item["code"] == "RK_LOCAL_STYLE")
    assert error["severity"] == "error"
    assert r"\begin{minipage}" in error["message"]


def test_local_style_diagnostic_uses_the_filtered_body(tmp_path: Path) -> None:
    # The reported match must be outside the table, even when the same
    # forbidden pattern first occurs in a discarded table body.
    table = TABLE.replace("Owner", r"\vspace{1mm}Owner")
    result = _audit(tmp_path, "default", "markdown", table + r"\hspace{1mm}Text")
    error = next(item for item in result["diagnostics"] if item["code"] == "RK_LOCAL_STYLE")
    assert r"\hspace" in error["message"]
    assert r"\vspace" not in error["message"]
