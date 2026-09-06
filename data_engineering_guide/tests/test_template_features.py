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


if __name__ == "__main__":
    unittest.main()
