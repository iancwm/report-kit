"""Publication-level gate for a designed editorial article."""
from __future__ import annotations

import json
from pathlib import Path

from reportkit.cli import main
from reportkit.editorial_audit import audit_editorial_source

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "latex_templates" / "examples" / "editorial-feature"


def test_canonical_feature_meets_its_declared_composition_brief() -> None:
    result = audit_editorial_source(EXAMPLE / "report.tex", EXAMPLE / "editorial-brief.json")
    assert result["passed"]
    assert result["manual_review_required"] is True
    assert result["inventory"]["graphic-exhibit"] >= 2
    assert result["inventory"]["featurecolumns"] >= 2


def test_valid_latex_theme_alone_cannot_pass_a_rich_editorial_brief(tmp_path: Path) -> None:
    tex = tmp_path / "report.tex"
    tex.write_text(
        r"\documentclass[theme=editorial,publication-type=feature-article]{reportkit}" + "\n"
        r"\begin{document}" + "\n"
        r"\begin{featureopening}\featureheadline{Plain report}\featuredeck{Summary}\featurebyline{Desk}\end{featureopening}" + "\n"
        r"\featuresection{Argument}Plain prose." + "\n"
        r"\begin{featureexhibit}[span=full]{One table}\begin{featuretable}Table\end{featuretable}\imagecredit{Source}\end{featureexhibit}" + "\n"
        r"\end{document}" + "\n",
        encoding="utf-8",
    )
    result = audit_editorial_source(tex, EXAMPLE / "editorial-brief.json")
    assert not result["passed"]
    assert {item["code"] for item in result["diagnostics"]} == {"RK_EDITORIAL_COMPOSITION", "RK_EDITORIAL_EXHIBITS"}
    assert result["inventory"]["featureexhibit"] == 1
    assert result["inventory"]["graphic-exhibit"] == 0


def test_comments_do_not_satisfy_brief_and_local_styling_is_rejected(tmp_path: Path) -> None:
    tex = tmp_path / "report.tex"
    tex.write_text(
        r"\documentclass[theme=editorial,publication-type=feature-article]{reportkit}" + "\n"
        r"% \begin{openingvisual}{fake}" + "\n"
        r"\begin{document}\vspace{2mm}Text\end{document}" + "\n",
        encoding="utf-8",
    )
    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps({"visual_reference": "user QA PDF", "required": ["openingvisual"], "minimum_exhibits": 0}), encoding="utf-8")
    result = audit_editorial_source(tex, brief)
    assert not result["passed"]
    assert result["inventory"]["openingvisual"] == 0
    assert {item["code"] for item in result["diagnostics"]} == {"RK_EDITORIAL_COMPOSITION", "RK_EDITORIAL_LOCAL_STYLE"}


def test_cli_reports_static_pass_without_claiming_visual_approval(capsys) -> None:
    code = main(["audit-editorial", str(EXAMPLE / "report.tex"), "--brief", str(EXAMPLE / "editorial-brief.json"), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["passed"] is True
    assert payload["manual_review_required"] is True
    assert len(payload["manual_review"]) == 3
