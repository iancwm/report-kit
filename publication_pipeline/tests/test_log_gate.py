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


def test_a_genuine_missing_font_still_fails():
    result = inspect_diagnostics(
        'fontspec: Font "Google Sans" not found.\n',
        underfull_badness=4000,
        allowlist=[],
    )
    assert not result["passed"]
    assert result["counts"]["missing_font"] == 1


def test_luaotfload_resolution_chatter_under_font_policy_fallback_does_not_fail():
    # luaotfload logs a font-not-found *attempt* even when font_policy:
    # fallback recovers by substituting and finishes the compile; the
    # theme package's own (correctly non-blocking) warning already covers
    # this case, so this internal trace must not also gate the build.
    result = inspect_diagnostics(
        "\n".join(
            [
                'luaotfload | db : Reload initiated (formats: otf,ttf,ttc); reason: Font "Google Sans" not found.',
                "luaotfload | resolve : sequence of 3 lookups yielded nothing appropriate.",
                "Package reportkit-theme-institutional-research Warning: WARN Google Sans unavailable, using fallback.",
                "Output written on guide.pdf (1 page).",
            ]
        ),
        underfull_badness=4000,
        allowlist=[],
    )
    assert result["passed"]
    assert result["counts"]["missing_font"] == 0
