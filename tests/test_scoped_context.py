from __future__ import annotations

from pathlib import Path

import pytest

from reportkit.authoring_templates import document_template
from reportkit.context import build_context
from reportkit.context_budget import build_context_slice
from reportkit.documentation import check_documentation
from reportkit.documentation import END as CONTRACT_END, START as CONTRACT_START
from reportkit.primitive_targets import ROLE_TABLE, ROLES, role_for
from reportkit.publications import PUBLICATION_TYPES
from reportkit.registry import generate_registry


REPO = Path(__file__).resolve().parents[1]
PUBLICATION_TYPES_IN_ORDER = tuple(PUBLICATION_TYPES)
OPENING_MARKERS = {
    "technical-report": r"\maketitle",
    "equity-research": r"\begin{researchfrontpage}",
    "executive-brief": r"\begin{briefheader}",
    "feature-article": r"\begin{featureopening}",
    "book": r"\begin{bookdetails}",
    "presentation": r"\begin{titleslide}",
}


@pytest.mark.parametrize("publication_type", PUBLICATION_TYPES_IN_ORDER)
def test_every_target_gets_a_small_scoped_primitive_slice_and_template(publication_type: str) -> None:
    publication = PUBLICATION_TYPES[publication_type]
    theme = publication["themes"][0]
    context = build_context(REPO, publication_type=publication_type, theme=theme)
    registry = generate_registry(REPO, strict=True)
    primitive_slice = build_context_slice(context, "primitives")
    assert primitive_slice["estimated_tokens"] <= 8_000

    for kind, records in context["capabilities"]["primitives"].items():
        expected = {
            name
            for name, record in registry["primitives"][kind].items()
            if record["targets"][publication_type] in {"native", "allowed"}
            and publication_type in record["available_in"]["publication_types"]
            and theme in record["available_in"]["themes"]
        }
        assert set(records) == expected
        for record in records.values():
            assert record["targets"][publication_type] in {"native", "allowed"}
            assert record["available_in"]["publication_types"] == [publication_type]

    template = document_template(publication_type, theme)
    assert OPENING_MARKERS[publication_type] in template
    assert r"\maketitle" in template if publication_type == "technical-report" else r"\maketitle" not in template
    assert f"publication-type={publication_type}" in template
    assert context["capabilities"]["authoring"]["document_template"] == template


def test_feature_article_roles_keep_report_callouts_and_algorithm_primitives_out() -> None:
    registry = generate_registry(REPO, strict=True)
    assert role_for("featuretable", "composition", "feature-article") == "allowed"
    for record in registry["primitives"]["callout"].values():
        assert record["targets"]["feature-article"] == "discouraged"
    for kind, records in registry["primitives"].items():
        for record in records.values():
            source = record["source"]["file"]
            if "reportkit-algorithm" in source or source.endswith("reportkit-algorithms.sty"):
                assert record["targets"]["feature-article"] == "absent"
    assert role_for("maketitle", "command", "feature-article") == "absent"
    assert role_for("maketitle", "command", "technical-report") == "native"
    assert role_for("evidencenote", "callout", "book") == "allowed"


def test_role_table_covers_every_primitive_and_target_without_a_default_allowed() -> None:
    registry = generate_registry(REPO, strict=True)
    target_names = set(PUBLICATION_TYPES)
    for family in ROLE_TABLE.values():
        assert set(family["roles"]) == target_names
        assert set(family["members"])
        assert set(family["roles"].values()) <= set(ROLES)
        for override in family["overrides"].values():
            assert set(override) == target_names
            assert set(override.values()) <= set(ROLES)

    for kind, records in registry["primitives"].items():
        for name, record in records.items():
            expected = {
                publication_type: role_for(name, kind, publication_type)
                for publication_type in PUBLICATION_TYPES
            }
            assert record["targets"] == expected
            assert set(record["targets"]) == target_names
            assert set(record["targets"].values()) <= set(ROLES)

    with pytest.raises(KeyError, match="no explicit source-family role"):
        role_for("unregistered-example", "command", "technical-report")


def test_target_references_are_native_only_and_within_the_byte_budget() -> None:
    registry = generate_registry(REPO, strict=True)
    assert check_documentation(REPO, registry=registry) == []
    for filename in (
        "feature-article-authoring.md",
        "institutional-research-theme.md",
        "presentation-authoring.md",
    ):
        assert (REPO / "references" / filename).stat().st_size <= 20_000

    for publication_type, filename in (
        ("feature-article", "feature-article-authoring.md"),
        ("equity-research", "institutional-research-theme.md"),
        ("presentation", "presentation-authoring.md"),
    ):
        expected = {
            record["name"]
            for records in registry["primitives"].values()
            for record in records.values()
            if record["targets"][publication_type] == "native"
        }
        text = (REPO / "references" / filename).read_text(encoding="utf-8")
        generated = text.split(CONTRACT_START, 1)[1].split(CONTRACT_END, 1)[0]
        for name in expected:
            assert f"`{name}`" in generated
        for kind, records in registry["primitives"].items():
            for name, record in records.items():
                if record["targets"][publication_type] != "native":
                    assert f"`{name}`" not in generated
