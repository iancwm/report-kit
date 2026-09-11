from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from reportkit.config import theme_engine_conflict
from reportkit.publications import (
    PUBLICATION_TYPES,
    THEMES,
    PublicationRegistryError,
    check_publication_registry,
    resolve_build_target,
)


REPO = Path(__file__).resolve().parents[1]


def test_catalog_is_referentially_complete() -> None:
    assert check_publication_registry(REPO) == []
    assert PUBLICATION_TYPES["technical-report"]["themes"] == ["default", "technical"]
    assert THEMES["technical"]["alias_of"] == "default"


def test_technical_alias_resolves_to_the_default_target() -> None:
    default = resolve_build_target("technical-report", "default", repo_root=REPO)
    technical = resolve_build_target("technical-report", "technical", repo_root=REPO)

    assert technical.requested_theme == "technical"
    assert technical.requested_name == "technical"
    assert technical.canonical_theme == "default"
    assert technical.theme == "default"
    assert technical.alias_of == "default"
    assert technical.as_dict() | {"requested_theme": "default", "requested_name": "default", "alias_of": None} == default.as_dict()
    assert technical.common_package == default.common_package


def test_target_is_immutable() -> None:
    target = resolve_build_target("technical-report", "default", repo_root=REPO)
    with pytest.raises(FrozenInstanceError):
        target.engine = "lualatex"  # type: ignore[misc]
    with pytest.raises(TypeError):
        target.geometry["paper"] = "letter"  # type: ignore[index]


def test_unknown_names_have_sorted_candidates() -> None:
    with pytest.raises(PublicationRegistryError) as error:
        resolve_build_target("not-a-publication", "default", repo_root=REPO)
    assert error.value.diagnostic["candidates"] == sorted(PUBLICATION_TYPES)
    assert "not-a-publication" in str(error.value)

    with pytest.raises(PublicationRegistryError) as error:
        resolve_build_target("technical-report", "not-a-theme", repo_root=REPO)
    assert error.value.diagnostic["candidates"] == sorted(THEMES)


def test_unsupported_pair_names_compatible_themes() -> None:
    with pytest.raises(PublicationRegistryError) as error:
        resolve_build_target("equity-research", "default", repo_root=REPO)
    assert error.value.diagnostic["candidates"] == ["institutional-research"]
    assert "compatible themes: institutional-research" in str(error.value)


def test_engine_mismatch_uses_the_same_message_as_legacy_facade() -> None:
    expected = theme_engine_conflict({"theme": "institutional-research", "engine": "pdflatex"})
    assert expected is not None
    with pytest.raises(PublicationRegistryError, match="requires engine 'lualatex'") as error:
        resolve_build_target("equity-research", "institutional-research", engine="pdflatex", repo_root=REPO)
    assert str(error.value) == expected


def test_class_is_derived_from_renderer_not_document_class() -> None:
    target = resolve_build_target("technical-report", "default", repo_root=REPO)
    assert target.class_name == "reportkit"
    assert target.renderer == "paged"
