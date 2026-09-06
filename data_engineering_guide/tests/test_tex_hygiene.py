from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tex_hygiene import wrap_long_literals


class TexHygieneTests(unittest.TestCase):
    def test_breaks_are_added_inside_texttt_and_url_literals(self) -> None:
        rendered = wrap_long_literals(r"\texttt{s3://bucket/raw/event\_date=2026} \url{https://example.com/a-b}")
        self.assertIn(r"s3:\allowbreak{}/\allowbreak{}/\allowbreak{}bucket/\allowbreak{}", rendered)
        self.assertIn(r"event\_\allowbreak{}date=\allowbreak{}", rendered)
        self.assertIn(r"https:\allowbreak{}/\allowbreak{}/\allowbreak{}example.\allowbreak{}com/\allowbreak{}", rendered)

    def test_long_s3_fixture_gets_multiple_break_opportunities(self) -> None:
        fixture = (Path(__file__).parent / "fixtures" / "long-s3-path.txt").read_text(encoding="utf-8").strip()
        latex_literal = fixture.replace("_", r"\_")
        rendered = wrap_long_literals(r"\texttt{" + latex_literal + "}")
        self.assertGreaterEqual(rendered.count(r"\allowbreak{}"), 10)


if __name__ == "__main__":
    unittest.main()
