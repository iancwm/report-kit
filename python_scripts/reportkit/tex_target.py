"""Gates for direct-TeX projects (agent reasoning loop spec §4.3).

Wave 0 stub: signatures are frozen; the direct-TeX lane fills the bodies.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .target import TargetState


def read_class_options(tex: Path) -> dict[str, str] | None:
    """Parse ``publication-type=``/``theme=`` from ``\\documentclass[...]{reportkit}``.

    Returns ``None`` when the options are missing. Stub: ``None``.
    """
    return None


def tex_gates(state: TargetState, tex: Path) -> list[dict[str, Any]]:
    """``RK_TARGET_MISMATCH`` when class options are missing or disagree with
    ``publication.yaml``; runs before TeX. Stub: ``[]``."""
    return []


def engine_gate(state: TargetState, requested_engine: str | None) -> list[dict[str, Any]]:
    """``RK_ENGINE_DOWNGRADE`` when a LuaLaTeX theme is forced onto pdflatex. Stub: ``[]``."""
    return []
