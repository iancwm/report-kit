"""Table-driven image-slot validation coverage."""
from __future__ import annotations

from pathlib import Path

import pytest

from publication_validation import validate_publication


def _publication(tmp_path: Path, *, declaration: str, manuscript: str = "[[REPORTKIT-IMAGE:img:sample]]\n") -> Path:
    root = tmp_path / "publication"
    (root / "manuscript").mkdir(parents=True)
    (root / "fragments").mkdir()
    (root / "assets" / "images").mkdir(parents=True)
    (root / "manuscript" / "order.txt").write_text("01.md\n", encoding="utf-8")
    (root / "manuscript" / "01.md").write_text(manuscript, encoding="utf-8")
    (root / "image-slots.yaml").write_text(declaration, encoding="utf-8")
    return root


VALID_DECLARATION = """images:
  sample:
    purpose: Show the sample object
    caption: A sample object.
    alt: A blue sample object.
    aspect_ratio: square
    path: assets/images/sample.png
    source: Created for the fixture.
    creator: ReportKit contributors
    license: CC0-1.0
    attribution: No external attribution required.
    restrictions: None.
"""


def test_draft_accepts_a_declared_missing_asset_and_release_blocks_it(tmp_path: Path) -> None:
    root = _publication(tmp_path, declaration=VALID_DECLARATION)

    draft = validate_publication(root, profile="draft")
    assert draft.ok
    assert draft.image_slots["sample"].state == "placeholder"
    assert [item["code"] for item in draft.diagnostics] == ["RK_VALIDATION_IMAGE_SLOT_MISSING_FILE"]
    assert draft.unresolved_image_slots[0].slug == "sample"

    release = validate_publication(root, profile="release")
    assert not release.ok
    assert any(item["code"] == "RK_VALIDATION_IMAGE_SLOT_MISSING_FILE" for item in release.diagnostics)

    (root / "assets" / "images" / "sample.png").write_bytes(b"image")
    supplied = validate_publication(root, profile="release")
    assert supplied.ok
    assert supplied.image_slots["sample"].state == "supplied"
    assert supplied.unresolved_image_slots == []


@pytest.mark.parametrize(
    "path",
    [
        "../sample.png",
        "/tmp/sample.png",
        "assets/sample.png",
        "assets/images/other.png",
        "assets/images/sample.svg",
        "assets\\images\\sample.png",
    ],
)
def test_unsafe_or_mismatched_paths_are_rejected(tmp_path: Path, path: str) -> None:
    declaration = VALID_DECLARATION.replace("assets/images/sample.png", path)
    result = validate_publication(_publication(tmp_path, declaration=declaration))
    assert not result.ok
    assert any(item["code"] == "RK_VALIDATION_IMAGE_SLOT_METADATA_OR_PATH" for item in result.diagnostics)


def test_malformed_image_sentinel_is_rejected_with_source_location(tmp_path: Path) -> None:
    result = validate_publication(
        _publication(tmp_path, declaration=VALID_DECLARATION, manuscript="[[REPORTKIT-IMAGE:img:Bad]]\n")
    )
    diagnostic = next(item for item in result.diagnostics if item["code"] == "RK_VALIDATION_INVALID_IMAGE_SENTINEL")
    assert diagnostic["file"] == "manuscript/01.md"
    assert diagnostic["line"] == 1


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root = _publication(tmp_path, declaration=VALID_DECLARATION)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    (root / "assets" / "images" / "sample.png").symlink_to(outside)

    result = validate_publication(root)
    assert not result.ok
    assert any("escapes the publication's assets/images directory" in item["message"] for item in result.diagnostics)


def test_unknown_ratio_missing_metadata_and_pending_rights_are_actionable(tmp_path: Path) -> None:
    declaration = VALID_DECLARATION.replace("aspect_ratio: square", "aspect_ratio: panoramic")
    declaration = declaration.replace("    creator: ReportKit contributors\n", "")
    declaration = declaration.replace("    source: Created for the fixture.\n", "    source: Pending selection.\n")
    result = validate_publication(_publication(tmp_path, declaration=declaration))
    assert not result.ok
    messages = "\n".join(item["message"] for item in result.diagnostics)
    assert "unknown aspect_ratio" in messages
    assert "required field 'creator'" in messages
    assert "pending rights or credit fields" in messages


def test_duplicate_use_missing_declaration_and_orphan_declaration_are_rejected(tmp_path: Path) -> None:
    declaration = VALID_DECLARATION + """  orphan:
    purpose: Orphan
    caption: Orphan.
    alt: Orphan.
    aspect_ratio: square
    path: assets/images/orphan.png
    source: Fixture
    creator: ReportKit
    license: CC0-1.0
    attribution: None.
    restrictions: None.
"""
    root = _publication(
        tmp_path,
        declaration=declaration,
        manuscript="[[REPORTKIT-IMAGE:img:sample]]\n[[REPORTKIT-IMAGE:img:sample]]\n[[REPORTKIT-IMAGE:img:missing]]\n",
    )
    result = validate_publication(root)
    assert not result.ok
    codes = {item["code"] for item in result.diagnostics}
    assert "RK_VALIDATION_DUPLICATE_IMAGE_SLOT_USE" in codes
    assert "RK_VALIDATION_MISSING_IMAGE_DECLARATION" in codes
    assert "RK_VALIDATION_ORPHAN_IMAGE_DECLARATION" in codes
