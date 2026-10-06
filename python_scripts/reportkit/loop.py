"""The reasoning loop restated in every command's output (spec §4.1).

Every command prints one TARGET line first and a ``next step`` last; JSON
payloads carry the same data as ``target`` and ``next_step``. Agents obey
local, repeated signals more reliably than one instruction read once.
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
    """Render the compact, repeatable target decision line (spec §4.1)."""
    if state is None:
        return "TARGET NOT DECLARED — choose a structure and look, then run `reportkit target set`."
    if state.declared_by == "default":
        if state.require_declared:
            return (
                "TARGET NOT DECLARED — the build will refuse. Pick a row below and run "
                "`reportkit target set`."
            )
        return (
            f"TARGET NOT DECLARED — legacy config resolves to {state.publication_type}/{state.theme}/{state.renderer}; "
            "the build warns. Record the decision with `reportkit target set`."
        )
    intent = ".reportkit/intent.json" if state.source_root is not None else "—"
    return (
        f"TARGET {state.publication_type}/{state.theme}/{state.renderer}  "
        f"source={state.source_mode}  declared={state.declared_by}  intent={intent}"
    )


def target_payload(state: TargetState | None) -> dict[str, Any]:
    """The TARGET line as JSON (``publication_type``, ``theme``, ``renderer``,
    ``source_mode``, ``declared_by``, ``intent_path``, and its human form)."""
    if state is None:
        return {
            "declared_by": "default",
            "intent_path": None,
            "line": target_line(None),
        }
    return {
        "publication_type": state.publication_type,
        "theme": state.theme,
        "renderer": state.renderer,
        "source_mode": state.source_mode,
        "declared_by": state.declared_by,
        "intent_path": ".reportkit/intent.json" if state.source_root is not None else None,
        "line": target_line(state),
    }


def next_step(command: str, state: TargetState | None, outcome: Mapping[str, Any]) -> dict[str, Any]:
    """``{command, reason}`` after ``command`` finished with envelope ``outcome``.

    A failed gate returns its remediation command; success returns the next
    row of :data:`LOOP_STEPS`.
    """
    diagnostics = outcome.get("diagnostics") or []
    blocking = next(
        (item for item in diagnostics if isinstance(item, Mapping) and item.get("severity") == "error"),
        None,
    )
    if outcome.get("passed") is False or blocking is not None:
        code = str(blocking.get("code", "")) if blocking else ""
        if code == "RK_TARGET_UNDECLARED":
            return {
                "command": "reportkit target set --publication-type <type> --theme <theme> --source-mode <tex|markdown> --request \"<verbatim user ask>\"",
                "reason": "Declare the publication target before checking or building.",
            }
        if code in {"RK_TARGET_MISMATCH", "RK_SOURCE_MODE_UNSUPPORTED", "RK_INTENT_MISMATCH"}:
            return {
                "command": "reportkit target set --publication-type <type> --theme <theme> --source-mode <tex|markdown>",
                "reason": str(blocking.get("message", "Correct the declared target.")),
            }
        if code == "RK_ENGINE_DOWNGRADE":
            return {
                "command": "scripts/setup_tex.sh --check && reportkit build --json",
                "reason": "Install the required TeX engine and keep the declared theme.",
            }
        remediation = str(blocking.get("remediation", "")) if blocking else ""
        return {
            "command": "Fix the reported diagnostics, then rerun `reportkit check --json`.",
            "reason": remediation or "The previous step did not pass.",
        }

    root = state.source_root if state is not None else None
    declared = state is not None and state.declared_by != "default"
    has_intent = state is not None and state.intent is not None
    command_name = command.split()[0].strip()
    if command_name in {"doctor", "docs", "analyse-history", "diagnose", "package"}:
        destination = "reportkit context --slice quickstart --json"
        reason = "Select the publication format and look."
    elif command_name == "context":
        if not declared:
            destination, reason = "reportkit target set --publication-type <type> --theme <theme> --source-mode <tex|markdown> --request \"<verbatim user ask>\"", "Lock the selected target and preserve the request."
        elif not has_intent:
            destination, reason = "reportkit target set --publication-type <type> --theme <theme> --source-mode <tex|markdown> --request \"<verbatim user ask>\"", "Persist the target and the user's request."
        else:
            destination, reason = "reportkit context --slice primitives --json", "Load the grammar scoped to this target."
    elif command_name == "materialize":
        destination, reason = "reportkit check --json", "Author the source from .reportkit/references/ and .reportkit/context.json, then run check."
    elif command_name == "target":
        destination, reason = "reportkit init <project-dir> --publication-type <type> --theme <theme> --source-mode <tex|markdown>", "Scaffold a starter and composition brief for the locked target."
    elif command_name == "init":
        if not declared or not has_intent:
            destination, reason = "reportkit target set --publication-type <type> --theme <theme> --source-mode <tex|markdown> --request \"<verbatim user ask>\"", "Lock the selected target and preserve the request before authoring."
        else:
            destination, reason = "reportkit context --slice primitives --json", "Load the target grammar, then author the source."
    elif command_name == "check":
        destination, reason = "reportkit build --json", "The target and source checks passed."
    elif command_name in {"audit", "audit-editorial"}:
        destination, reason = "reportkit check --json", "The composition brief audit completed; run the full project gates."
    elif command_name == "build":
        destination, reason = "reportkit render --pages 1 --json, then reportkit review --json --visual-review done|unavailable", "Build passed; render and record the visual review."
    elif command_name in {"render", "inspect"}:
        destination, reason = "reportkit review --json --visual-review done|unavailable", "Record whether the rendered pages were reviewed."
    elif command_name == "review":
        destination, reason = "reportkit status --json", "Recover the complete delivery state from disk."
    elif command_name == "status":
        last = outcome.get("last_step") or {}
        last_name = last.get("step") if isinstance(last, Mapping) else None
        visual_review = outcome.get("visual_review")
        if last_name == "BUILD" and not visual_review:
            destination, reason = "reportkit render --pages 1 --json, then reportkit review --json --visual-review done|unavailable", "The build passed; render and record the visual review."
        elif last_name == "REVIEW" and not visual_review:
            destination, reason = "reportkit review --json --visual-review done|unavailable", "Record whether rendered pages were viewed."
        elif visual_review in {"done", "unavailable"}:
            destination = "Deliver the publication and quote the TARGET line from this status output."
            reason = "The loop state is ready for the delivery message."
            if outcome.get("unresolved_images"):
                reason += " Include image_caveat: the build still has unresolved image slots."
        elif last_name == "CHECK":
            destination, reason = "reportkit build --json", "The target and source checks passed."
        elif last_name in {"LOCK", "SCAFFOLD"}:
            destination, reason = "reportkit context --slice primitives --json", "Load the target grammar and author the source."
        elif last_name == "AUTHOR":
            destination, reason = "reportkit check --json", "The project has a declared target and authored source."
        elif declared:
            destination, reason = "reportkit context --slice primitives --json", "Load the grammar scoped to this target, then author the source."
        else:
            destination, reason = "reportkit target set --publication-type <type> --theme <theme> --source-mode <tex|markdown> --request \"<verbatim user ask>\"", "Lock the selected target and preserve the request."
    else:
        destination, reason = "reportkit status --json", "Re-hydrate the publication state from disk."

    # Keep the output state-aware without making this function depend on CLI
    # arguments. The initialized project can still be in AUTHOR after context.
    if command_name == "init" and root is not None and not (root / "publication.yaml").is_file():
        destination = "reportkit init <project-dir> --publication-type <type> --theme <theme>"
        reason = "Create the consumer project before authoring."
    return {"command": destination, "reason": reason}
