"""Persisted publication-target state (agent reasoning loop spec §4.2).

The target is a *decision*, recorded in the consumer project's
``publication.yaml`` ``document:`` block and ``.reportkit/intent.json``.
Every CLI command reloads it from disk through :func:`load_target`; nothing
here caches state across invocations.

Wave 0 stub: the public signatures are frozen. ``load_target`` wraps today's
``resolve_document`` and records whether the type was declared; the other
functions are no-ops until the target-lock lane fills them.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import CONFIG_NAME, load_publication_config, resolve_document, resolve_validation
from .diagnostics import make_diagnostic
from .publications import PUBLICATION_TYPES

INTENT_PATH = Path(".reportkit") / "intent.json"
INTENT_SCHEMA_VERSION = "1.0.0"
SOURCE_MODES = ("tex", "markdown")
DECLARED_BY = ("publication.yaml", "tex-class-options", "default")
DECIDED_BY = ("user-confirmed", "agent-inferred")


@dataclass(frozen=True)
class TargetState:
    """One project's resolved target, reloaded from disk on every command.

    ``declared_by`` is ``publication.yaml``, ``tex-class-options``, or
    ``default`` (nothing declared: the silent fallback the loop exists to
    remove). ``intent`` is the parsed ``.reportkit/intent.json`` or ``None``.
    ``require_declared`` mirrors ``validation.require_declared_target``.
    """

    publication_type: str
    theme: str
    renderer: str
    source_mode: str
    main: str
    declared_by: str
    intent: dict[str, Any] | None
    require_declared: bool
    source_root: Path | None = None

    @property
    def intent_path(self) -> Path | None:
        return self.source_root / INTENT_PATH if self.source_root is not None else None


def load_target(source_root: Path) -> TargetState:
    """Reload the declared (or defaulted) target of ``source_root`` from disk.

    Configuration errors are reported by ``check``/``build`` themselves; here
    an unreadable ``publication.yaml`` resolves as an undeclared default.
    """
    root = Path(source_root)
    try:
        config = load_publication_config(root / CONFIG_NAME)
    except (OSError, ValueError):
        config = {}
    declared = (config.get("document") or {}) if isinstance(config.get("document"), dict) else {}
    document = resolve_document(config)
    publication_type = str(document.get("publication_type"))
    try:
        require_declared = bool(resolve_validation(config).get("require_declared_target", False))
    except (AttributeError, TypeError):
        require_declared = False
    return TargetState(
        publication_type=publication_type,
        theme=str(document.get("theme")),
        renderer=str((PUBLICATION_TYPES.get(publication_type) or {}).get("renderer", "paged")),
        source_mode=str(document.get("source_mode") or "markdown"),
        main=str(document.get("main")),
        declared_by="publication.yaml" if declared.get("publication_type") else "default",
        intent=None,
        require_declared=require_declared,
        source_root=root,
    )


def set_target(
    source_root: Path,
    *,
    publication_type: str | None = None,
    theme: str | None = None,
    source_mode: str | None = None,
    request: str | None = None,
    reference: str | None = None,
    decided_by: str | None = None,
) -> tuple[TargetState, list[dict[str, Any]]]:
    """Validate and persist a target: the ``document:`` block plus intent.json.

    Returns the reloaded state and any diagnostics (``RK_SOURCE_MODE_UNSUPPORTED``
    or an incompatible type/theme pair). Stub: writes nothing yet.
    """
    diagnostic = make_diagnostic(
        "internal_error", "reportkit target set does not persist the target yet (agent reasoning loop lane A)",
        code="RK_NOT_IMPLEMENTED", severity="warning",
        remediation="Record document.publication_type and document.theme in publication.yaml by hand.",
    )
    return load_target(source_root), [diagnostic]


def resolve_alias(text: str) -> tuple[str, str] | None:
    """Map a natural-language request (``magazine``) to ``(type, theme)``. Stub: ``None``."""
    return None


def target_gate(state: TargetState) -> list[dict[str, Any]]:
    """``RK_TARGET_UNDECLARED`` (blocking) or ``RK_TARGET_IMPLICIT`` (warning). Stub: ``[]``."""
    return []
