from __future__ import annotations

from pathlib import Path
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
