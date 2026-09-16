"""Pure-Python coverage for D6's constrained brand override surface."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from reportkit.config import (
    BRAND_KEYS,
    load_publication_config,
    resolve_brand,
    resolve_effective_theme,
)
from reportkit.publications import THEMES
from reportkit.theme_overrides import (
    BrandOverrides,
    ThemeOverrideError,
    build_effective_theme,
    materialize_chart_overrides,
    materialize_tex_overrides,
    normalize_brand_overrides,
    render_tex_overrides,
    validate_tex_overrides,
)
from reportkit.themes import get_theme, theme_supports_brand_overrides


def _enabled_registry(theme: str = "default") -> dict[str, dict[str, object]]:
    registry = {name: dict(record) for name, record in THEMES.items()}
    registry[theme]["brand_overrides"] = True
    return registry


def test_brand_surface_is_exact_and_current_registry_is_opt_in_only() -> None:
    assert BRAND_KEYS == ("primary", "secondary", "logo", "display_font")
    assert not any(theme_supports_brand_overrides(name) for name in THEMES)


def test_no_brand_section_is_a_no_op_and_preserves_base_palette() -> None:
    base = get_theme("default")
    effective = resolve_effective_theme({})

    assert effective.brand == BrandOverrides()
    assert dict(effective.latex_colors) == base.latex_colors
    assert effective.data_colors == base.data_colors
    assert render_tex_overrides(effective) == "% ReportKit theme overrides: none.\n"


def test_config_parser_accepts_brand_and_unknown_keys_fail(tmp_path: Path) -> None:
    config_path = tmp_path / "publication.yaml"
    config_path.write_text(
        "publication:\n  title: Test\n"
        'brand:\n  primary: "#abcdef"\n  display_font: "Source Sans 3"\n',
        encoding="utf-8",
    )
    config = load_publication_config(config_path)
    assert config["brand"] == {"primary": "#abcdef", "display_font": "Source Sans 3"}

    config_path.write_text(
        "publication:\n  title: Test\nbrand:\n  tertiary: \"#abcdef\"\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"brand\.tertiary"):
        load_publication_config(config_path)


def test_registry_capability_rejects_brand_for_every_current_theme() -> None:
    with pytest.raises(ThemeOverrideError, match="brand_overrides"):
        normalize_brand_overrides({"primary": "#abcdef"}, theme="default")


@pytest.mark.parametrize("value", ["#abc", "abcdef", "#abcdef0", "blue", 123])
def test_colors_require_six_digit_hex(value: object) -> None:
    with pytest.raises(ThemeOverrideError, match="six-digit"):
        normalize_brand_overrides({"primary": value}, theme="default", registry=_enabled_registry())


def test_normalization_is_canonical_and_immutable(tmp_path: Path) -> None:
    logo = tmp_path / "assets" / "logo.svg"
    logo.parent.mkdir()
    logo.write_text("<svg />\n", encoding="utf-8")
    brand = normalize_brand_overrides(
        {
            "primary": "#abcdef",
            "secondary": "#123456",
            "logo": "assets/logo.svg",
            "display_font": "  Source   Sans 3 ",
        },
        theme="default",
        publication_root=tmp_path,
        registry=_enabled_registry(),
    )

    assert brand.primary == "#ABCDEF"
    assert brand.secondary == "#123456"
    assert brand.logo == logo.resolve()
    assert brand.display_font == "Source Sans 3"
    with pytest.raises(FrozenInstanceError):
        brand.primary = "#000000"  # type: ignore[misc]


def test_logo_must_be_a_contained_existing_file(tmp_path: Path) -> None:
    registry = _enabled_registry()
    with pytest.raises(ThemeOverrideError, match="inside the publication root"):
        normalize_brand_overrides(
            {"logo": "../outside.svg"},
            theme="default",
            publication_root=tmp_path,
            registry=registry,
        )
    with pytest.raises(ThemeOverrideError, match="regular file"):
        normalize_brand_overrides(
            {"logo": "missing.svg"},
            theme="default",
            publication_root=tmp_path,
            registry=registry,
        )


def test_font_policy_is_validated_with_brand_values() -> None:
    with pytest.raises(ThemeOverrideError, match="strict.*fallback"):
        normalize_brand_overrides(
            {"display_font": "Source Sans 3"},
            theme="default",
            font_policy="system",
            registry=_enabled_registry(),
        )


def test_effective_theme_drives_deterministic_tex_and_chart_projections(tmp_path: Path) -> None:
    logo = tmp_path / "logo.svg"
    logo.write_bytes(b"logo bytes\n")
    effective = build_effective_theme(
        "default",
        {
            "primary": "#abcdef",
            "secondary": "#123456",
            "logo": "logo.svg",
            "display_font": "Source Sans 3",
        },
        publication_root=tmp_path,
        font_policy="fallback",
        registry=_enabled_registry(),
    )

    tex = render_tex_overrides(effective)
    assert tex == render_tex_overrides(effective)
    assert "\\definecolor{RKEffectiveLinkBlue}{HTML}{ABCDEF}" in tex
    assert "\\definecolor{RKEffectiveResearch}{HTML}{123456}" in tex
    assert r"\newcommand{\RKBrandLogo}{logo.svg}" in tex
    assert validate_tex_overrides(tex, effective) == []

    chart = materialize_chart_overrides(effective)
    assert chart["primary"] == "#ABCDEF"
    assert chart["secondary"] == "#123456"
    assert chart["data_colors"][:2] == ["#ABCDEF", "#123456"]
    assert chart["logo"] == "logo.svg"
    assert chart["hashes"]["palette"] == effective.palette_hash
    assert chart["hashes"]["logo"] == effective.logo_hash

    output = tmp_path / "generated" / "reportkit-theme-overrides.tex"
    assert materialize_tex_overrides(effective, output) == output
    assert output.read_text(encoding="utf-8") == tex


def test_no_logo_branch_emits_a_valid_newif_falsy_macro_name(tmp_path: Path) -> None:
    # \newif\ifRKBrandHasLogo only ever defines the lowercase-suffixed
    # \RKBrandHasLogotrue/\RKBrandHasLogofalse control sequences; a
    # differently-cased falsy macro name is an undefined control sequence
    # that halts compilation the moment a publication configures brand
    # overrides (any theme.brand_overrides theme) without a logo.
    effective = build_effective_theme(
        "default",
        {"primary": "#abcdef"},
        publication_root=tmp_path,
        font_policy="fallback",
        registry=_enabled_registry(),
    )
    tex = render_tex_overrides(effective)
    assert r"\RKBrandHasLogofalse" in tex
    assert r"\RKBrandHasLogoFalse" not in tex


def test_config_resolution_uses_profile_brand_and_selected_font_policy(tmp_path: Path) -> None:
    logo = tmp_path / "logo.svg"
    logo.write_text("svg", encoding="utf-8")
    config = {
        "document": {"theme": "default"},
        "theme": {"font_policy": "strict"},
        "profiles": {"release": {"brand": {"primary": "#abcdef", "logo": "logo.svg"}}},
    }
    with pytest.raises(ThemeOverrideError, match="brand_overrides"):
        resolve_brand(config, source_root=tmp_path, profile="release")

    effective = resolve_effective_theme(
        config,
        source_root=tmp_path,
        profile="release",
        registry=_enabled_registry(),
    )
    assert effective.font_policy == "strict"
    assert effective.primary == "#ABCDEF"
    assert effective.brand.logo == logo.resolve()
