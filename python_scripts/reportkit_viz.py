"""Compatibility facade for the packaged ReportKit visualization layer."""
from __future__ import annotations

from reportkit import viz as _viz
from reportkit.viz.core import _cli

__version__ = _viz.__version__
__all__ = list(dict.fromkeys([*getattr(_viz, "__all__", ()), "__version__"]))


def __getattr__(name: str):
    """Resolve mutable theme globals from the canonical viz package."""
    return getattr(_viz, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_viz)))


if __name__ == "__main__":
    _cli()
