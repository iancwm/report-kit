"""Composition audits for every publication target (spec §4.7).

Generalises ``editorial_audit.py``: each target has a :class:`RoleRegistry`
(required roles, their source patterns, manual-review items, and forbidden
local styling), plus two universal checks, ``RK_PRIMITIVE_OFF_TARGET`` and
``RK_LOCAL_STYLE``.

Wave 0 stub: feature articles delegate to the existing editorial audit; other
targets return a passing, empty audit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .diagnostics import diagnostic_envelope
from .editorial_audit import audit_editorial_source
from .target import TargetState

BRIEF_NAMES = ("composition-brief.json", "editorial-brief.json")


@dataclass(frozen=True)
class RoleRegistry:
    required_roles: tuple[str, ...] = ()
    role_patterns: dict[str, str] = field(default_factory=dict)
    manual_review: tuple[str, ...] = ()
    local_style_forbidden: tuple[str, ...] = ()


ROLE_REGISTRIES: dict[str, RoleRegistry] = {}


def find_brief(source_root: Path, state: TargetState) -> Path | None:
    """Locate the brief: ``intent.composition_brief``, then :data:`BRIEF_NAMES`.

    Stub: ``None``, so ``check`` does not audit yet.
    """
    return None


def audit_source(tex: Path, brief: Path | None, state: TargetState) -> dict[str, Any]:
    """Audit ``tex`` (direct TeX or the generated ``publication.tex``) against ``brief``."""
    if state.publication_type == "feature-article" and brief is not None:
        return audit_editorial_source(tex, brief)
    return diagnostic_envelope(
        [], passed=True, source=str(tex), brief=str(brief) if brief else None,
        publication_type=state.publication_type, inventory={}, manual_review_required=True, manual_review=[],
    )
