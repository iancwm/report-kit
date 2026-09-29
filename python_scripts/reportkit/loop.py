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
    """Render the stable target declaration used by the loop (spec §4.1).

    ``publication_type`` names the publication structure and ``theme`` names
    its visual look. The same spelling is used in human output and in the
    quickstart slice so the two axes stay explicit after a context reset.
    """
    if state is None:
        return ""
    intent = ".reportkit/intent.json" if state.source_root is not None else "none"
    return (
        f"TARGET structure={state.publication_type} look={state.theme} "
        f"renderer={state.renderer}  source={state.source_mode}  "
        f"declared={state.declared_by}  intent={intent}"
    )


def target_payload(state: TargetState | None) -> dict[str, Any]:
    """The TARGET line as JSON (``publication_type``, ``theme``, ``renderer``,
    ``source_mode``, ``declared_by``, ``intent_path``, ``line``)."""
    if state is None:
        return {}
    return {
        "publication_type": state.publication_type,
        "theme": state.theme,
        "renderer": state.renderer,
        "source_mode": state.source_mode,
        "declared_by": state.declared_by,
        "intent_path": ".reportkit/intent.json" if state.source_root is not None else None,
        "structure": state.publication_type,
        "look": state.theme,
        "line": target_line(state),
    }


def next_step(command: str, state: TargetState | None, outcome: Mapping[str, Any]) -> dict[str, Any]:
    """``{command, reason}`` after ``command`` finished with envelope ``outcome``.

    A failed gate returns its remediation command; success returns the next
    row of :data:`LOOP_STEPS`. Stub: ``{}``.
    """
    diagnostics = _diagnostic_records(outcome)
    errors = [item for item in diagnostics if item.get("severity") == "error"]
    failed = (
        outcome.get("passed") is False
        or outcome.get("returncode") not in (None, 0)
        or outcome.get("status") in {"failed", "error"}
        or bool(errors)
    )
    if failed:
        diagnostic = errors[0] if errors else (diagnostics[0] if diagnostics else {})
        code = str(diagnostic.get("code", ""))
        remediation = _remediation_command(code, state)
        if remediation is None:
            if command in {"review", "render", "inspect"}:
                remediation = "reportkit build --json"
            elif command in {"target", "target set", "target show"}:
                remediation = "reportkit target set"
            else:
                remediation = "reportkit check --json"
        reason = str(diagnostic.get("remediation") or diagnostic.get("message") or "Resolve the reported diagnostics.")
        return {"command": remediation, "reason": reason}

    normalized = command.strip().casefold()
    if normalized.startswith("target "):
        action = normalized.split(maxsplit=1)[1]
        if action == "show" and state is not None and state.declared_by == "default":
            return _loop_next("LOCK", reason="Choose and record the publication structure and look.")
        normalized = "target"
    aliases = {
        "scaffold": "init",
        "render": "review-artifact",
        "inspect": "review-artifact",
        "package": "deliver",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized == "context":
        requested_slice = str(outcome.get("slice") or "quickstart")
        normalized = "quickstart" if requested_slice == "quickstart" else "primitives"

    step_by_command = {
        "quickstart": "SELECT",
        "target": "LOCK",
        "init": "SCAFFOLD",
        "primitives": "AUTHOR",
        "check": "CHECK",
        "build": "BUILD",
        "review": "REVIEW",
        "review-artifact": "REVIEW",
        "status": "DELIVER",
    }
    step_name = step_by_command.get(normalized)
    if step_name is None:
        # Non-loop commands (doctor, docs, diagnostics) do not advance the
        # publication. Point the agent back to the first durable decision.
        return _loop_next("SELECT", reason="Start or resume the publication loop.")
    if step_name == "DELIVER":
        return {
            "command": "deliver",
            "reason": "Quote this status TARGET line in the delivery message.",
        }
    index = next(index for index, step in enumerate(LOOP_STEPS) if step.name == step_name)
    next_index = min(index + 1, len(LOOP_STEPS) - 1)
    next_item = LOOP_STEPS[next_index]
    if step_name == "LOCK":
        return _loop_next("SCAFFOLD", reason="The target is recorded; create its starter files.")
    return {"command": next_item.command, "reason": f"Next loop step: {next_item.name}."}


def _loop_next(step_name: str, *, reason: str) -> dict[str, Any]:
    step = next(step for step in LOOP_STEPS if step.name == step_name)
    return {"command": step.command, "reason": reason}


def _diagnostic_records(outcome: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Accept diagnostic envelopes and the nested build-report form."""
    value: Any = outcome.get("diagnostics", outcome.get("issues", []))
    if isinstance(value, Mapping):
        value = value.get("diagnostics", value.get("issues", []))
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _remediation_command(code: str, state: TargetState | None) -> str | None:
    if code in {"RK_TARGET_UNDECLARED", "RK_TARGET_MISMATCH", "RK_INTENT_MISMATCH"}:
        publication_type = state.publication_type if state else "<type>"
        theme = state.theme if state else "<theme>"
        source_mode = state.source_mode if state else "<tex|markdown>"
        return (
            "reportkit target set --publication-type " + publication_type
            + " --theme " + theme + " --source-mode " + source_mode
            + ' --request "<verbatim user ask>"'
        )
    if code == "RK_SOURCE_MODE_UNSUPPORTED":
        return "reportkit target set --source-mode tex"
    if code == "RK_ENGINE_DOWNGRADE":
        return "scripts/setup_tex.sh"
    if code == "RK_PRIMITIVE_OFF_TARGET":
        return "reportkit context --slice primitives --json"
    return None
