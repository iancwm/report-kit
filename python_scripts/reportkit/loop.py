"""The reasoning loop restated in every command's output (spec §4.1).

Every command prints one TARGET line first and a ``next step`` last; JSON
payloads carry the same data as ``target`` and ``next_step``. Agents obey
local, repeated signals more reliably than one instruction read once.

Wave 0 stub: signatures and the step table are frozen; the rendering
functions return empty values until the loop-output lane fills them.
"""
from __future__ import annotations

from typing import Any, Mapping, NamedTuple

from .target import TargetState


class LoopStep(NamedTuple):
    name: str
    command: str
    artefact: str | None


LOOP_STEPS: tuple[LoopStep, ...] = (
    LoopStep("SELECT", "reportkit context --slice quickstart --json", None),
    LoopStep("LOCK", "reportkit target set --publication-type T --theme H --source-mode tex|markdown --request \"<verbatim user ask>\"", "publication.yaml document: + .reportkit/intent.json"),
    LoopStep("SCAFFOLD", "reportkit init <dir> --publication-type T --theme H", "target starter + composition brief stub"),
    LoopStep("AUTHOR", "reportkit context --slice primitives --json", "source files"),
    LoopStep("CHECK", "reportkit check --json", None),
    LoopStep("BUILD", "reportkit build --json", "build-report.json"),
    LoopStep("REVIEW", "reportkit review --json", "build/review.json"),
    LoopStep("DELIVER", "reportkit status --json", None),
)


def target_line(state: TargetState | None) -> str:
    """``TARGET <type>/<theme>/<renderer>  source=…  declared=…  intent=…``. Stub: ``""``."""
    return ""


def target_payload(state: TargetState | None) -> dict[str, Any]:
    """The TARGET line as JSON (``publication_type``, ``theme``, ``renderer``,
    ``source_mode``, ``declared_by``, ``intent_path``, ``line``). Stub: ``{}``."""
    return {}


def next_step(command: str, state: TargetState | None, outcome: Mapping[str, Any]) -> dict[str, Any]:
    """``{command, reason}`` after ``command`` finished with envelope ``outcome``.

    A failed gate returns its remediation command; success returns the next
    row of :data:`LOOP_STEPS`. Stub: ``{}``.
    """
    return {}
