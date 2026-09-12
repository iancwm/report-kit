"""Packaged ReportKit visualization API.

The implementation is grouped under this package while the top-level
``reportkit_viz`` module remains a compatibility facade for existing reports.
Theme globals are resolved dynamically so ``apply_theme`` keeps its documented
process-wide behaviour through both import paths.
"""
from __future__ import annotations

from . import core as _core

__version__ = _core.__version__
__all__ = list(dict.fromkeys([*getattr(_core, "__all__", ()), "__version__"]))


def __getattr__(name: str):
    """Forward public API and mutable theme state to the implementation."""
    return getattr(_core, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_core)))
