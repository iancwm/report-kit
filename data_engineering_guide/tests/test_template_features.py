from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import importlib.util

spec = importlib.util.spec_from_file_location("guide_build", Path(__file__).resolve().parents[1] / "scripts" / "guide-build.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TemplateFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = (Path(__file__).parent / "fixtures" / "markdown-features.md").read_text(encoding="utf-8")

    def test_table_fixture_enables_table_compatibility(self) -> None:
        self.assertTrue(module.has_table(self.fixture))

    def test_code_fixture_enables_highlighting_compatibility(self) -> None:
        self.assertTrue(module.has_code(self.fixture))

    def test_combined_body_plan_has_linked_contents_boundary(self) -> None:
        plan = module.body_plan("combined", ["00-frontmatter.tex", "01-introduction.tex"])
        self.assertEqual(plan[0], r"\input{00-frontmatter.tex}")
        self.assertIn(r"\pdfbookmark[1]{Contents}{guide-contents}", plan)
        self.assertIn(r"\tableofcontents", plan)
        self.assertIn(r"\pagenumbering{arabic}", plan)
        self.assertEqual(plan[-1], r"\input{01-introduction.tex}")

    def test_section_body_plan_does_not_add_book_contents(self) -> None:
        plan = module.body_plan("section", ["09-learning-path.tex"])
        self.assertEqual(plan, [r"\input{09-learning-path.tex}"])

    def test_failed_build_diagnostics_name_the_retained_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guide_root = root / "guide"
            manuscript_dir = guide_root / "manuscript"
            fragment_dir = guide_root / "fragments"
            manuscript_dir.mkdir(parents=True)
            fragment_dir.mkdir()
            manuscript = manuscript_dir / "01-one.md"
            manuscript.write_text("# One\n", encoding="utf-8")
            (manuscript_dir / "order.txt").write_text("01-one.md\n", encoding="utf-8")
            output = guide_root / "build" / "isolated" / "01-one"

            def fake_copy_templates(_repo_root: Path, staging: Path) -> None:
                (staging / "guide-template.tex").write_text("\\documentclass{article}\n", encoding="utf-8")

            def fake_render_body(_root: Path, _manuscript: Path, staging_body: Path) -> None:
                staging_body.write_text("body\n", encoding="utf-8")

            def fake_run_logged(_command: list[str], *, cwd: Path, log_path: Path) -> int:
                log_path.write_text("simulated TeX failure\n", encoding="utf-8")
                return 1

            def fake_build_report_base(*_args: object, **_kwargs: object) -> dict[str, object]:
                return {"commands": [], "diagnostics": {}, "status": "running"}

            with (
                mock.patch.object(module, "copy_templates", fake_copy_templates),
                mock.patch.object(module, "render_body", fake_render_body),
                mock.patch.object(module, "run_logged", fake_run_logged),
                mock.patch.object(module, "build_report_base", fake_build_report_base),
            ):
                with self.assertRaises(module.BuildFailure) as raised:
                    module.build_one(
                        guide_root,
                        mode="section",
                        manuscripts=[manuscript],
                        labels=[],
                        output_dir=output,
                    )

            message = str(raised.exception)
            report = json.loads((output / "build-report.json").read_text(encoding="utf-8"))
            self.assertTrue((output / "pass-1.log").is_file())
            self.assertIn(str(output / "pass-1.log"), message)
            self.assertIn(str(output / "pass-1.log"), report["error"])
            self.assertNotIn(".01-one.run-", message)
            self.assertNotIn(".01-one.run-", report["error"])


if __name__ == "__main__":
    unittest.main()
