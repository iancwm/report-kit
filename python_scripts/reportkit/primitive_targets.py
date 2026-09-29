"""Per-target primitive roles (agent reasoning loop spec §4.5, decision 2).

``ROLE_TABLE`` is one central, reviewed table keyed by primitive family with
per-name overrides. ``native`` primitives define a target's grammar,
``allowed`` ones may appear, ``discouraged`` ones raise
``RK_PRIMITIVE_OFF_TARGET``, and ``absent`` ones are not offered at all.

Wave 0 stub: every primitive available today is ``allowed``.
"""
from __future__ import annotations

from typing import Any, Literal

Role = Literal["native", "allowed", "discouraged", "absent"]
ROLES: tuple[str, ...] = ("native", "allowed", "discouraged", "absent")
ROLE_TABLE: dict[str, Any] = {}


def role_for(primitive_name: str, kind: str, publication_type: str) -> Role:
    """Return the role of ``primitive_name`` in ``publication_type``. Stub: ``"allowed"``."""
    return "allowed"
