from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from guide_validation import validate_guide


def make_guide(*, manuscripts: dict[str, str], order: list[str], fragments: dict[str, str]) -> Path:
    temp = Path(tempfile.mkdtemp())
    (temp / "manuscript").mkdir()
    (temp / "fragments").mkdir()
    (temp / "manuscript" / "order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
    for name, content in manuscripts.items():
        (temp / "manuscript" / name).write_text(content, encoding="utf-8")
    for slug, label in fragments.items():
        (temp / "fragments" / f"fig-{slug}.tex").write_text(
            f"\\begin{{diagram}}[label={{{label}}}]\\end{{diagram}}\n", encoding="utf-8"
        )
    return temp


class GuideValidationTests(unittest.TestCase):
    def test_valid_inputs_pass(self) -> None:
        root = make_guide(
            manuscripts={"01-one.md": "# One\n\n[[REPORTKIT-VISUAL:fig:one]]\n"},
            order=["01-one.md"],
            fragments={"one": "fig:one"},
        )
        self.assertTrue(validate_guide(root).ok)

    def test_missing_fragment_is_reported(self) -> None:
        root = make_guide(
            manuscripts={"01-one.md": "[[REPORTKIT-VISUAL:fig:missing]]\n"},
            order=["01-one.md"],
            fragments={},
        )
        result = validate_guide(root)
        self.assertFalse(result.ok)
        self.assertTrue(any("missing fragment" in error for error in result.errors))

    def test_orphan_fragment_is_reported(self) -> None:
        root = make_guide(
            manuscripts={"01-one.md": "# One\n"},
            order=["01-one.md"],
            fragments={"orphan": "fig:orphan"},
        )
        result = validate_guide(root)
        self.assertTrue(any("orphan fragment" in error for error in result.errors))

    def test_duplicate_slug_and_label_are_reported(self) -> None:
        root = make_guide(
            manuscripts={
                "01-one.md": "[[REPORTKIT-VISUAL:fig:one]]\n",
                "02-two.md": "[[REPORTKIT-VISUAL:fig:one]]\n[[REPORTKIT-VISUAL:fig:two]]\n",
            },
            order=["01-one.md", "02-two.md"],
            fragments={"one": "fig:one", "two": "fig:one"},
        )
        result = validate_guide(root)
        self.assertTrue(any("duplicate visual slug" in error for error in result.errors))
        self.assertTrue(any("does not match sentinel slug" in error for error in result.errors))

    def test_invalid_sentinel_case_is_reported(self) -> None:
        root = make_guide(
            manuscripts={"01-one.md": "[[REPORTKIT-VISUAL:fig:Not-valid]]\n"},
            order=["01-one.md"],
            fragments={},
        )
        result = validate_guide(root)
        self.assertTrue(any("invalid visual sentinel" in error for error in result.errors))

    def test_manuscript_missing_from_order_is_reported(self) -> None:
        root = make_guide(
            manuscripts={"01-one.md": "# One\n", "02-two.md": "# Two\n"},
            order=["01-one.md"],
            fragments={},
        )
        result = validate_guide(root)
        self.assertTrue(any("not listed in order.txt" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
