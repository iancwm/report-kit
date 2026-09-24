"""Compatibility facade for the packaged ReportKit visualization layer."""
from __future__ import annotations

from reportkit import viz as _viz
from reportkit.viz.core import _cli

__version__ = _viz.__version__
__all__ = list(dict.fromkeys([*getattr(_viz, "__all__", ()), "__version__", "apply_theme"]))


def apply_theme(
    theme: str = "default",
    *,
    brand: object | None = None,
    effective_theme: object | None = None,
    publication_root: object | None = None,
    font_policy: str = "fallback",
    font_family: str | None = None,
    font_path: str = "",
) -> None:
    """Apply a base theme, optionally projected through one effective theme.

    The historical ``apply_theme("default")`` call remains a direct delegate.
    Build-layer callers can pass a normalized brand mapping or an
    ``EffectiveTheme`` record; both chart globals and Matplotlib settings then
    come from the same resolved record used by TeX materialization.
    """
    from reportkit.theme_overrides import (
        EffectiveTheme,
        apply_chart_overrides,
        build_effective_theme,
    )

    if effective_theme is not None and brand is not None:
        raise ValueError("pass either effective_theme or brand, not both")
    if effective_theme is not None:
        if not isinstance(effective_theme, EffectiveTheme):
            raise TypeError("effective_theme must be an EffectiveTheme")
        resolved = effective_theme
    elif brand is not None:
        resolved = build_effective_theme(
            theme,
            brand,
            publication_root=publication_root,
            font_policy=font_policy,
            font_family=font_family,
            font_path=font_path,
        )
    else:
        _viz.apply_theme(theme)
        return

    _viz.apply_theme(resolved.base_theme.name)
    if resolved.configured:
        apply_chart_overrides(resolved)


def apply_publication_theme(publication_root: object, *, profile: str | None = None) -> object:
    """Apply the effective theme a publication project's build will use.

    Reads ``publication.yaml`` from ``publication_root`` and resolves the same
    immutable ``EffectiveTheme`` record ``publication_build.py`` materializes
    into ``reportkit-theme-overrides.tex`` (document theme, profile, theme
    font settings and the D6 ``brand`` section). A project's ``figures.py``
    calls this instead of ``apply_theme(name)`` so its charts and its TeX
    share one brand palette and display font. Returns the record so callers
    can log or assert its hashes.
    """
    from pathlib import Path

    from reportkit.config import CONFIG_NAME, load_publication_config, resolve_effective_theme

    root = Path(str(publication_root)).resolve()
    config = load_publication_config(root / CONFIG_NAME)
    effective = resolve_effective_theme(config, source_root=root, profile=profile)
    apply_theme(effective.base_theme.name, effective_theme=effective)
    return effective


__all__.append("apply_publication_theme")


def __getattr__(name: str):
    """Resolve mutable theme globals from the canonical viz package."""
    return getattr(_viz, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_viz)))


if __name__ == "__main__":
    _cli()
