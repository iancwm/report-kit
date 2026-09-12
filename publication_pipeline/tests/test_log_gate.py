from pathlib import Path
from reportkit.diagnostics import inspect_log as inspect_diagnostics


def test_clean_log_passes():
    result = inspect_diagnostics("Output written on guide.pdf (1 page).\n", underfull_badness=4000, allowlist=[])
    assert result["passed"]


def test_actionable_diagnostics_fail():
    result = inspect_diagnostics(
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
