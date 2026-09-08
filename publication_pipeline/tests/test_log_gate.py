from pathlib import Path
import json
from publication_pipeline.scripts import check_build_log as module


def test_clean_log_passes():
    result = module.inspect_log("Output written on guide.pdf (1 page).\n", underfull_badness=4000, allowlist=[])
    assert result["passed"]


def test_actionable_diagnostics_fail():
    result = module.inspect_log(
        "\n".join(
            [
                "Overfull \\hbox (402.1pt too wide)",
                "Underfull \\hbox (badness 10000)",
                "ignored error: Infinite glue shrinkage",
                "LaTeX Warning: Reference `fig:x' undefined",
                "LaTeX Warning: Label `fig:y' multiply defined.",
            ]
        ),
        underfull_badness=1000,
        allowlist=[],
    )
    assert not result["passed"]
    assert result["counts"]["overfull"] == 1
    assert result["counts"]["underfull"] == 1
    assert result["counts"]["ignored_error"] == 1
    assert result["counts"]["undefined"] == 1
    assert result["counts"]["duplicate_label"] == 1


def test_source_mapping_and_wrapped_message(tmp_path: Path):
    (tmp_path / "body-00.map.json").write_text(json.dumps({
        "source": "manuscript/01-fixture.md",
        "fragments": [{"generated_start": 10, "generated_end": 12, "source_start": 1, "path": "fragments/fig-fixture-flow.tex"}],
    }), encoding="utf-8")
    result = module.inspect_log(
        "(./body-00.tex\nOverfull \\hbox (8.4pt too\nwide) in paragraph at lines 10--12\n)\n",
        underfull_badness=4000,
        allowlist=[],
        build_dir=tmp_path,
    )
    issue = result["issues"][0]
    assert issue["type"] == "overfull_hbox"
    assert issue["file"] == "fragments/fig-fixture-flow.tex"
    assert issue["line"] == 1
    assert issue["amount_pt"] == 8.4
