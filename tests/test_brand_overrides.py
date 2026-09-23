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
    # Phase D: venture is the only theme whose registry record opts in.
    assert {name for name in THEMES if theme_supports_brand_overrides(name)} == {"venture"}


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


@pytest.mark.parametrize("theme", ["default", "technical", "institutional-research", "executive"])
def test_registry_capability_rejects_brand_for_every_non_opted_in_theme(theme: str) -> None:
    with pytest.raises(ThemeOverrideError, match="brand_overrides"):
        normalize_brand_overrides({"primary": "#abcdef"}, theme=theme)


def test_venture_accepts_brand_without_a_test_registry() -> None:
    brand = normalize_brand_overrides({"primary": "#abcdef"}, theme="venture")
    assert brand.primary == "#ABCDEF"


@pytest.mark.parametrize("value", ["#abc", "abcdef", "#abcdef0", "blue", 123])
def test_colors_require_six_digit_hex(value: object) -> None:
    with pytest.raises(ThemeOverrideError, match="six-digit"):
        normalize_brand_overrides({"primary": value}, theme="default", registry=_enabled_registry())


def test_normalization_is_canonical_and_immutable(tmp_path: Path) -> None:
    logo = tmp_path / "assets" / "logo.pdf"
    logo.parent.mkdir()
    logo.write_bytes(b"%PDF-1.4 fixture\n")
    brand = normalize_brand_overrides(
        {
            "primary": "#abcdef",
            "secondary": "#123456",
            "logo": "assets/logo.pdf",
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
            {"logo": "../outside.pdf"},
            theme="default",
            publication_root=tmp_path,
            registry=registry,
        )
    with pytest.raises(ThemeOverrideError, match="regular file"):
        normalize_brand_overrides(
            {"logo": "missing.pdf"},
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
    logo = tmp_path / "logo.pdf"
    logo.write_bytes(b"logo bytes\n")
    effective = build_effective_theme(
        "default",
        {
            "primary": "#abcdef",
            "secondary": "#123456",
            "logo": "logo.pdf",
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
    assert r"\newcommand{\RKBrandLogo}{logo.pdf}" in tex
    assert r"\RKBrandHasLogotrue" in tex
    assert validate_tex_overrides(tex, effective) == []

    no_logo = build_effective_theme(
        "default",
        {"primary": "#abcdef"},
        publication_root=tmp_path,
        font_policy="fallback",
        registry=_enabled_registry(),
    )
    assert r"\RKBrandHasLogofalse" in render_tex_overrides(no_logo)

    chart = materialize_chart_overrides(effective)
    assert chart["primary"] == "#ABCDEF"
    assert chart["secondary"] == "#123456"
    assert chart["data_colors"][:2] == ["#ABCDEF", "#123456"]
    assert chart["logo"] == "logo.pdf"
    assert chart["hashes"]["palette"] == effective.palette_hash
    assert chart["hashes"]["logo"] == effective.logo_hash

    output = tmp_path / "generated" / "reportkit-theme-overrides.tex"
    assert materialize_tex_overrides(effective, output) == output
    assert output.read_text(encoding="utf-8") == tex


def test_config_resolution_uses_profile_brand_and_selected_font_policy(tmp_path: Path) -> None:
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"png")
    config = {
        "document": {"theme": "default"},
        "theme": {"font_policy": "strict"},
        "profiles": {"release": {"brand": {"primary": "#abcdef", "logo": "logo.png"}}},
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


@pytest.mark.parametrize(
    ("name", "message"),
    [("logo.svg", "must be one of"), ("brand logo.pdf", "may contain only"), ("logo%.pdf", "may contain only")],
)
def test_logo_must_be_a_tex_includable_file(tmp_path: Path, name: str, message: str) -> None:
    (tmp_path / name).write_bytes(b"logo")
    with pytest.raises(ThemeOverrideError, match=message):
        normalize_brand_overrides({"logo": name}, theme="venture", publication_root=tmp_path)


def test_primary_drives_every_primary_role_and_secondary_the_secondary_role() -> None:
    effective = build_effective_theme("venture", {"primary": "#112233", "secondary": "#445566"})
    for role in ("LinkBlue", "Principle", "Accent", "MetricAccent"):
        assert effective.latex_colors[role] == "#112233"
    assert effective.latex_colors["Research"] == "#445566"
    assert effective.data_colors[:2] == ("#112233", "#445566")
    tex = render_tex_overrides(effective)
    assert "\\colorlet{Accent}{RKEffectiveAccent}" in tex
    assert validate_tex_overrides(tex, effective) == []


def test_logo_with_underscore_is_emitted_verbatim_for_includegraphics(tmp_path: Path) -> None:
    (tmp_path / "brand_mark.png").write_bytes(b"png")
    effective = build_effective_theme("venture", {"logo": "brand_mark.png"}, publication_root=tmp_path)
    assert r"\newcommand{\RKBrandLogo}{brand_mark.png}" in render_tex_overrides(effective)


def test_display_font_reaches_tex_and_chart_from_one_record() -> None:
    effective = build_effective_theme("venture", {"display_font": "Libertinus Sans"})
    tex = render_tex_overrides(effective)
    assert r"\newcommand{\RKBrandDisplayFont}{Libertinus Sans}" in tex
    assert r"\setreportkitfontfamily{\RKBrandDisplayFont}" in tex
    assert materialize_chart_overrides(effective)["display_font"] == "Libertinus Sans"
