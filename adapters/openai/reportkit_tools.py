"""Generate an OpenAI-style tool bundle from ReportKit's CLI contract.

The adapter deliberately has no ReportKit prose dependency.  Tool schemas are
derived from the live argparse contract and the command inventory; execution
uses only JSON-capable CLI commands and the published schemas.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTKIT = REPO_ROOT / "reportkit"
SCHEMA_ROOT = REPO_ROOT / "schemas"
PYTHON_ROOT = REPO_ROOT / "python_scripts"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


@dataclass(frozen=True)
class CLIResult:
    """One stable JSON CLI invocation."""

    command: str
    returncode: int
    payload: dict[str, Any]

    @property
    def passed(self) -> bool:
        return bool(self.payload.get("passed", True)) and self.returncode == 0


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    raise ValueError("ReportKit CLI has no subcommand parser")


def _json_type(action: argparse.Action) -> str:
    if isinstance(action, argparse._StoreTrueAction) or isinstance(action, argparse._StoreFalseAction):
        return "boolean"
    if action.type is int or "int" in getattr(action.type, "__name__", ""):
        return "integer"
    if action.type is float or "float" in getattr(action.type, "__name__", ""):
        return "number"
    return "string"


def _argument_schema(action: argparse.Action) -> tuple[str, dict[str, Any], bool]:
    """Translate one argparse action to an OpenAI function parameter."""
    if action.option_strings:
        name = action.dest
    else:
        name = action.dest
    schema: dict[str, Any] = {"type": _json_type(action), "description": action.help or action.dest}
    if action.choices:
        schema["enum"] = list(action.choices)
    if isinstance(action, argparse._AppendAction):
        schema = {
            "type": "array",
            "items": {"type": _json_type(action)},
            "description": action.help or action.dest,
        }
        if action.choices:
            schema["items"]["enum"] = list(action.choices)
    if action.default not in (None, argparse.SUPPRESS) and not isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        schema["default"] = action.default
    required = not action.option_strings and action.nargs not in ("?", "*", argparse.REMAINDER)
    return name, schema, required


def _tool_definition(command: str, parser: argparse.ArgumentParser, summary: str) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for action in parser._actions:
        if "--json" in action.option_strings or action.dest == "help":
            continue
        name, schema, is_required = _argument_schema(action)
        properties[name] = schema
        if is_required:
            required.append(name)
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        parameters["required"] = required
    return {
        "type": "function",
        "name": f"reportkit_{command.replace('-', '_')}",
        "description": summary,
        "parameters": parameters,
        "strict": True,
    }


def build_tool_bundle() -> dict[str, Any]:
    """Generate the Responses API-shaped bundle from the live CLI parser."""
    # Imports are intentionally local: the generated JSON can be regenerated
    # in a minimal Python process without importing chart dependencies.
    from reportkit.cli import build_parser
    from reportkit.registry import COMMAND_CONTRACT
    from reportkit.version import CONTRACT_VERSION

    parsers = _subparsers(build_parser())
    tools = [
        _tool_definition(command, parsers[command], record["summary"])
        for command, record in COMMAND_CONTRACT.items()
    ]
    return {
        "schema_version": "1.0.0",
        "contract_version": CONTRACT_VERSION,
        "source": "reportkit CLI argparse + COMMAND_CONTRACT",
        "tools": tools,
    }


def generate_tool_bundle(destination: Path | None = None) -> dict[str, Any]:
    """Write the generated bundle and return it."""
    destination = destination or Path(__file__).with_name("tools.json")
    bundle = build_tool_bundle()
    destination.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


def _schema_for(command: str, arguments: Mapping[str, Any]) -> Path | None:
    if command == "context" and arguments.get("schema"):
        # `context --schema` returns a JSON Schema document rather than the
        # ordinary context envelope; that document is itself the response.
        return None
    if command == "context":
        slice_name = arguments.get("context_slice", arguments.get("slice"))
        name = "reportkit-context-slice.schema.json" if slice_name else "reportkit-context.schema.json"
    else:
        name = "reportkit-diagnostic-envelope.schema.json"
    return SCHEMA_ROOT / name


def _validate_payload(payload: dict[str, Any], schema_path: Path) -> None:
    """Validate adapter responses against the checked-in schema when present."""
    try:
        import jsonschema
    except ImportError:
        required = {"passed", "schema_version", "diagnostics"}
        if not required.issubset(payload):
            raise ValueError(f"CLI response is missing required envelope fields: {sorted(required - set(payload))}")
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def _argument_tokens(command: str, parser: argparse.ArgumentParser, arguments: Mapping[str, Any]) -> list[str]:
    positionals = [action for action in parser._actions if not action.option_strings and action.dest != "help"]
    tokens: list[str] = []
    for action in positionals:
        value = arguments.get(action.dest)
        if value is not None:
            tokens.append(str(value))
    for action in parser._actions:
        if not action.option_strings or "--json" in action.option_strings or action.dest == "help":
            continue
        value = arguments.get(action.dest)
        if value is None or value is False:
            continue
        option = next((item for item in action.option_strings if item.startswith("--")), action.option_strings[0])
        if isinstance(value, list):
            for item in value:
                tokens.extend([option, str(item)])
        elif isinstance(value, bool):
            tokens.append(option)
        else:
            tokens.extend([option, str(value)])
    return tokens


def run_json(
    command: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    executable: Path | None = None,
    timeout: float = 120,
) -> CLIResult:
    """Invoke one stable CLI command and validate its JSON response."""
    from reportkit.cli import build_parser
    from reportkit.registry import COMMAND_CONTRACT

    arguments = dict(arguments or {})
    if command not in COMMAND_CONTRACT:
        raise ValueError(f"unknown ReportKit command {command!r}")
    parser = _subparsers(build_parser())[command]
    command_line = [str(executable or REPORTKIT), command, *_argument_tokens(command, parser, arguments), "--json"]
    process = subprocess.run(command_line, capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT)
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ReportKit {command} did not return JSON: {process.stdout or process.stderr}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"ReportKit {command} returned a non-object JSON payload")
    schema_path = _schema_for(command, arguments)
    if schema_path is not None:
        _validate_payload(payload, schema_path)
    return CLIResult(command, process.returncode, payload)


def write_minimal_publication(target: Path, *, executable: Path | None = None) -> dict[str, Any]:
    """Author and validate a minimal publication through the neutral contract.

    The content is intentionally assembled from a filtered ``context`` result,
    then checked through the public CLI.  No host skill or prose reference is
    read by this proof adapter.
    """
    target = target.resolve()
    (target / "manuscript").mkdir(parents=True, exist_ok=True)
    (target / "fragments").mkdir(parents=True, exist_ok=True)
    (target / "publication.yaml").write_text(
        "title: OpenAI adapter smoke\n"
        "subtitle: Minimal neutral-contract publication\n"
        "author: ReportKit\n",
        encoding="utf-8",
    )
    context = run_json(
        "context",
        {"publication_type": "technical-report", "theme": "default", "kind": ["callout"]},
        executable=executable,
    )
    callouts = context.payload["capabilities"]["primitives"]["callout"]
    primitive = "principle" if "principle" in callouts else sorted(callouts)[0]
    required = [item["name"] for item in callouts[primitive]["arguments"] if item["required"]]
    arguments = "\n".join(f"{name}: Neutral contract smoke" for name in required)
    (target / "manuscript" / "order.txt").write_text("01-smoke.md\n", encoding="utf-8")
    (target / "manuscript" / "01-smoke.md").write_text(
        "# Neutral contract smoke\n\n"
        "This publication was authored from the machine-readable contract.\n\n"
        f"```reportkit {primitive}\n{arguments}\n"
        "content: The CLI validates this directive before conversion.\n```\n",
        encoding="utf-8",
    )
    validation = run_json("check", {"source_root": str(target)}, executable=executable)
    return {
        "passed": validation.passed,
        "publication": str(target),
        "primitive": primitive,
        "validation": validation.payload,
    }


if __name__ == "__main__":
    generate_tool_bundle()
