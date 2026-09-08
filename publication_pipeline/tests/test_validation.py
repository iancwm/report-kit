from __future__ import annotations

from pathlib import Path
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publication_validation import validate_publication


def make_publication(manuscripts: dict[str, str], order: list[str], fragments: dict[str, str]) -> Path:
    root = Path(tempfile.mkdtemp())
    (root / "manuscript").mkdir()
    (root / "fragments").mkdir()
    (root / "manuscript" / "order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
    for name, text in manuscripts.items():
        (root / "manuscript" / name).write_text(text, encoding="utf-8")
    for slug, label in fragments.items():
        (root / "fragments" / f"fig-{slug}.tex").write_text(f"\\begin{{diagram}}[label={{{label}}}]\\end{{diagram}}\n", encoding="utf-8")
    return root


def test_valid_tree_passes() -> None:
    root = make_publication({"01-one.md": "[[REPORTKIT-VISUAL:fig:one]]\n"}, ["01-one.md"], {"one": "fig:one"})
    assert validate_publication(root).ok

def test_missing_and_orphan_fragments_fail() -> None:
    root = make_publication({"01-one.md": "[[REPORTKIT-VISUAL:fig:missing]]\n"}, ["01-one.md"], {"orphan": "fig:orphan"})
    result = validate_publication(root)
    assert any("missing fragment" in error for error in result.errors)
    assert any("orphan fragment" in error for error in result.errors)

def test_invalid_sentinel_and_unordered_manuscript_fail() -> None:
    root = make_publication({"01-one.md": "[[REPORTKIT-VISUAL:fig:Not-valid]]\n", "02-two.md": "# Two\n"}, ["01-one.md"], {})
    result = validate_publication(root)
    assert any("invalid visual sentinel" in error for error in result.errors)
    assert any("not listed in order.txt" in error for error in result.errors)
