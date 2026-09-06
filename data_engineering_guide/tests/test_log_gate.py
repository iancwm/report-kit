from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import importlib.util

spec = importlib.util.spec_from_file_location("check_build_log", Path(__file__).resolve().parents[1] / "scripts" / "check-build-log.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuildLogGateTests(unittest.TestCase):
    def test_clean_final_pass_passes(self) -> None:
        result = module.inspect_log("Output written on guide.pdf (1 page).\n", underfull_badness=4000, allowlist=[])
        self.assertTrue(result["passed"])

    def test_actionable_diagnostics_fail(self) -> None:
        log = "\n".join(
            [
                "Overfull \\hbox (402.1pt too wide) in paragraph",
                "Underfull \\hbox (badness 10000) in paragraph",
                "ignored error: Infinite glue shrinkage",
                "LaTeX Warning: Reference `fig:x' undefined",
                "LaTeX Warning: Label `fig:y' multiply defined.",
            ]
        )
        result = module.inspect_log(log, underfull_badness=1000, allowlist=[])
        self.assertFalse(result["passed"])
        self.assertEqual(result["counts"]["overfull"], 1)
        self.assertEqual(result["counts"]["underfull"], 1)
        self.assertEqual(result["counts"]["ignored_error"], 1)
        self.assertEqual(result["counts"]["undefined"], 1)
        self.assertEqual(result["counts"]["duplicate_label"], 1)

    def test_small_underfull_box_is_below_the_threshold(self) -> None:
        result = module.inspect_log("Underfull \\hbox (badness 500) in paragraph", underfull_badness=1000, allowlist=[])
        self.assertTrue(result["passed"])

    def test_expired_allowlist_is_a_failure(self) -> None:
        allowlist = [{"pattern": "known benign", "reason": "temporary", "expires": "2020-01-01"}]
        result = module.inspect_log("known benign warning", underfull_badness=1000, allowlist=allowlist)
        self.assertFalse(result["passed"])
        self.assertEqual(result["counts"]["allowlist"], 1)

    def test_reviewed_allowlist_can_temporarily_suppress_a_known_benign_line(self) -> None:
        allowlist = [{"pattern": "known benign", "reason": "toolchain issue", "expires": "2099-01-01"}]
        result = module.inspect_log("known benign warning", underfull_badness=1000, allowlist=allowlist)
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
