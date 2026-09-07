from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("check_build_log", Path(__file__).resolve().parents[1] / "scripts" / "check-build-log.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


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
