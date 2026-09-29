"""Persisted publication-target state (agent reasoning loop spec §4.2).

The target is a *decision*, recorded in the consumer project's
``publication.yaml`` ``document:`` block and ``.reportkit/intent.json``.
Every CLI command reloads it from disk through :func:`load_target`; nothing
here caches state across invocations. The public signatures are frozen by the
implementation plan §3.3.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .config import CONFIG_NAME, _profile_section, load_publication_config, resolve_document, resolve_validation
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
    document = resolve_document(config)
    publication_type = str(document.get("publication_type"))
    try:
        require_declared = bool(resolve_validation(config).get("require_declared_target", False))
    except (AttributeError, TypeError):
        require_declared = False
    source_mode = str(document.get("source_mode") or "markdown")
    declared_by = str(document.get("declared_by", "default"))
    if declared_by == "default" and source_mode == "tex":
        # Direct-TeX class options are the legacy fallback only when the
        # consumer has not declared its publication structure in YAML.
        # Import locally because tex_target imports TargetState for its gate
        # signatures; keeping YAML resolution above pure avoids a cycle.
        from .tex_target import read_class_options

        try:
            class_options = read_class_options(root / str(document.get("main") or "report.tex"))
        except OSError:
            class_options = None
        if class_options:
            option_type = class_options.get("publication_type") or class_options.get("publication-type")
            if option_type:
                publication_type = str(option_type)
                publication = PUBLICATION_TYPES.get(publication_type) or {}
                theme = class_options.get("theme") or publication.get("default_target", {}).get("theme", document.get("theme"))
                if theme:
                    document["theme"] = str(theme)
                document["publication_type"] = publication_type
                declared_by = "tex-class-options"
    intent = _read_intent(root / INTENT_PATH)
    return TargetState(
        publication_type=publication_type,
        theme=str(document.get("theme")),
        renderer=str((PUBLICATION_TYPES.get(publication_type) or {}).get("renderer", "paged")),
        source_mode=source_mode,
        main=str(document.get("main")),
        declared_by=declared_by,
        intent=intent,
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

    Returns the reloaded state and any validation diagnostics. The request is
    copied byte-for-byte as a Python string into the JSON record.
    """
    root = Path(source_root).expanduser()
    config_path = root / CONFIG_NAME
    try:
        config = load_publication_config(config_path)
        existing = resolve_document(config)
    except (OSError, ValueError) as exc:
        diagnostic = make_diagnostic(
            "configuration_error", f"cannot read {config_path}: {exc}", code="RK_TARGET_CONFIG",
            docs="#/commands/target",
        )
        return load_target(root), [diagnostic]

    original_type = publication_type
    raw_type = publication_type.strip() if isinstance(publication_type, str) else publication_type
    raw_request = request
    alias_text: str | None = None
    alias_pair: tuple[str, str] | None = None
    if raw_type:
        if raw_type not in PUBLICATION_TYPES:
            alias_match = _matched_alias(str(raw_type))
            if alias_match is not None:
                alias_text, alias_pair = alias_match
    elif request:
        alias_match = _matched_alias(request)
        if alias_match is not None:
            alias_text, alias_pair = alias_match

    if alias_pair is not None:
        selected_type = alias_pair[0]
        default_theme = alias_pair[1]
        if raw_request is None and raw_type:
            raw_request = str(original_type)
    else:
        selected_type = str(raw_type or existing.get("publication_type") or "technical-report")
        current_type = str(existing.get("publication_type") or "technical-report")
        publication = PUBLICATION_TYPES.get(selected_type)
        if selected_type != current_type and publication:
            default_theme = str(publication.get("default_target", {}).get("theme", "default"))
        else:
            default_theme = str(existing.get("theme") or "default")

    selected_theme = str(theme).strip() if isinstance(theme, str) else None
    selected_theme = selected_theme or default_theme
    publication = PUBLICATION_TYPES.get(selected_type)

    selected_mode = source_mode.strip() if isinstance(source_mode, str) else None
    if not selected_mode:
        configured_mode = _profile_section(config, "document", None).get("source_mode")
        selected_mode = str(configured_mode).strip() if configured_mode not in (None, "", {}) else None
    if not selected_mode:
        selected_mode = _default_source_mode(publication)

    errors = _validate_target(selected_type, selected_theme, selected_mode)
    if errors:
        return load_target(root), errors

    if decided_by is not None and decided_by not in DECIDED_BY:
        diagnostic = _target_error(
            f"decided_by must be one of {', '.join(DECIDED_BY)}; received {decided_by!r}.",
            remediation="Use `--decided-by user-confirmed` or `--decided-by agent-inferred`.",
        )
        return load_target(root), [diagnostic]

    decision_source = decided_by or ("agent-inferred" if alias_pair is not None else "user-confirmed")
    intent: dict[str, Any] = {
        "schema_version": INTENT_SCHEMA_VERSION,
        "request": raw_request if raw_request is not None else "",
        "publication_type": selected_type,
        "theme": selected_theme,
        "source_mode": selected_mode,
        "visual_reference": reference,
        "composition_brief": "composition-brief.json",
        "decided_by": decision_source,
        "alias": alias_text,
        "locked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    try:
        try:
            _validate_intent(intent)
        except Exception as exc:
            diagnostic = make_diagnostic(
                "configuration_error", f"generated intent does not match its schema: {exc}",
                code="RK_TARGET_CONFIG", docs="#/commands/target",
            )
            return load_target(root), [diagnostic]
        current_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        values = {
            "publication_type": selected_type,
            "theme": selected_theme,
            "source_mode": selected_mode,
        }
        if selected_mode == "tex":
            values["main"] = "report.tex"
        updated_text = _update_document_block(current_text, values)
        if selected_mode == "markdown":
            updated_text = _remove_document_key(updated_text, "main")
        _write_target_files(config_path, updated_text, root / INTENT_PATH, intent)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        diagnostic = make_diagnostic(
            "configuration_error", f"cannot persist publication target: {exc}", code="RK_TARGET_CONFIG",
            docs="#/commands/target",
        )
        return load_target(root), [diagnostic]
    return load_target(root), []


def resolve_alias(text: str) -> tuple[str, str] | None:
    """Map an unambiguous publication alias such as ``magazine`` to type/theme."""
    match = _matched_alias(text)
    return match[1] if match else None


def target_gate(state: TargetState) -> list[dict[str, Any]]:
    """Block a missing required target or warn once for a legacy default."""
    if state.declared_by != "default":
        return []
    if state.require_declared:
        return [make_diagnostic(
            "target_contract",
            "No publication target has been declared in publication.yaml.",
            code="RK_TARGET_UNDECLARED",
        )]
    return [make_diagnostic(
        "target_contract",
        "No publication target was declared; ReportKit is using its legacy default.",
        code="RK_TARGET_IMPLICIT",
    )]


def _read_intent(path: Path) -> dict[str, Any] | None:
    """Read the project's persisted intent without retaining process state."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _default_source_mode(publication: dict[str, Any] | None) -> str:
    modes = (publication or {}).get("source_modes") or {}
    if modes.get("markdown") == "supported":
        return "markdown"
    if modes.get("tex") in {"supported", "required"}:
        return "tex"
    return "markdown"


def _validate_target(publication_type: str, theme: str, source_mode: str) -> list[dict[str, Any]]:
    publication = PUBLICATION_TYPES.get(publication_type)
    if publication is None:
        return [_target_error(
            f"unknown publication type {publication_type!r}; valid types: {', '.join(sorted(PUBLICATION_TYPES))}.",
            candidates=sorted(PUBLICATION_TYPES),
            remediation="Choose a publication type from `reportkit context --slice quickstart`, then rerun `reportkit target set`.",
        )]
    themes = [str(value) for value in publication.get("themes", [])]
    if theme not in themes:
        choices = [f"{publication_type}/{value}" for value in themes]
        return [_target_error(
            f"theme {theme!r} is not supported by publication type {publication_type!r}; choose one of {', '.join(themes)}.",
            candidates=choices,
            remediation=f"Choose one of {', '.join(choices)} and rerun `reportkit target set`.",
        )]
    if source_mode not in SOURCE_MODES:
        return [_source_mode_error(
            f"source mode {source_mode!r} is not recognized; choose 'tex' or 'markdown'.",
            remediation="Use `--source-mode tex` or `--source-mode markdown`.",
        )]
    mode_support = (publication.get("source_modes") or {}).get(source_mode)
    supported = mode_support in ({"supported", "required"} if source_mode == "tex" else {"supported"})
    if not supported:
        remediation = (
            "This publication type requires direct TeX. Run `reportkit target set --source-mode tex` "
            "and author the publication as direct TeX."
            if publication.get("source_modes", {}).get("tex") == "required"
            else f"Use `reportkit target set --source-mode tex` for {publication_type}."
        )
        return [_source_mode_error(
            f"publication type {publication_type!r} does not support source mode {source_mode!r}.",
            remediation=remediation,
        )]
    return []


def _target_error(message: str, *, candidates: tuple[str, ...] | list[str] = (), remediation: str | None = None) -> dict[str, Any]:
    """Use the frozen validation diagnostic code so target errors exit 3."""
    return make_diagnostic(
        "target_contract", message, code="RK_TARGET_MISMATCH", remediation=remediation,
        candidates=candidates,
    )


def _source_mode_error(message: str, *, remediation: str | None = None) -> dict[str, Any]:
    return make_diagnostic(
        "target_contract", message, code="RK_SOURCE_MODE_UNSUPPORTED", remediation=remediation,
    )


def _matched_alias(text: str) -> tuple[str, tuple[str, str]] | None:
    """Return the longest unambiguous registry alias contained in *text*."""
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    if not normalized:
        return None
    matches: list[tuple[int, str, tuple[str, str]]] = []
    for type_name, publication in PUBLICATION_TYPES.items():
        pair = (type_name, str(publication.get("default_target", {}).get("theme", "default")))
        for alias in publication.get("aliases", ()):
            alias_text = str(alias)
            alias_normalized = re.sub(r"[^a-z0-9]+", " ", alias_text.casefold()).strip()
            if not alias_normalized:
                continue
            alias_pattern = re.escape(alias_normalized).replace("\\ ", r"\s+")
            if re.search(rf"(?<![a-z0-9]){alias_pattern}(?![a-z0-9])", normalized):
                matches.append((len(alias_normalized), alias_text, pair))
    if not matches:
        return None
    exact = [
        (alias, pair)
        for _, alias, pair in matches
        if re.sub(r"[^a-z0-9]+", " ", alias.casefold()).strip() == normalized
    ]
    if exact:
        exact_pairs = {pair for _, pair in exact}
        if len(exact_pairs) != 1:
            return None
        alias, pair = sorted(exact, key=lambda item: item[0].casefold())[0]
        return alias, pair
    pairs = {pair for _, _, pair in matches}
    if len(pairs) != 1:
        return None
    longest = max(length for length, _, _ in matches)
    winners = [(alias, pair) for length, alias, pair in matches if length == longest]
    alias, pair = sorted(winners, key=lambda item: item[0].casefold())[0]
    return alias, pair


def _split_yaml_comment(value: str) -> tuple[str, str]:
    """Split a scalar tail from its YAML comment, respecting quoted hashes."""
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote:
            escaped = True
            continue
        if char in "'\"":
            quote = None if char == quote else (char if quote is None else quote)
        elif char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip(), value[index:]
    return value.rstrip(), ""


def _update_document_block(text: str, values: dict[str, str]) -> str:
    """Update target scalar keys while retaining unrelated YAML and comments."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    contents = [line.rstrip("\r\n") for line in lines]
    endings = [line[len(content):] for line, content in zip(lines, contents)]
    document_start = next((i for i, line in enumerate(contents) if re.match(r"^document\s*:\s*(?:#.*)?$", line)), None)
    if document_start is None:
        base = text
        if base and not base.endswith(("\n", "\r")):
            base += newline
        if base and not base.endswith(newline * 2):
            base += newline
        block = ["document:", *(f"  {key}: {value}" for key, value in values.items())]
        return base + newline.join(block) + newline

    document_end = len(contents)
    for index in range(document_start + 1, len(contents)):
        line = contents[index]
        if line and not line.startswith((" ", "\t", "#")):
            document_end = index
            break

    found: set[str] = set()
    for index in range(document_start + 1, document_end):
        match = re.match(r"^(?P<indent> {2})(?P<key>[A-Za-z0-9_-]+):(?P<tail>.*)$", contents[index])
        if not match:
            continue
        key = match.group("key")
        if key not in values:
            continue
        found.add(key)
        _, comment = _split_yaml_comment(match.group("tail"))
        if key == "publication_type" and "REQUIRED: run `reportkit target set`" in comment:
            comment = ""
        separator = " " if comment else ""
        prefix = f"{match.group('indent')}{key}:"
        contents[index] = f"{prefix} {values[key]}{separator}{comment}".rstrip()

    missing = [f"  {key}: {value}" for key, value in values.items() if key not in found]
    if missing:
        insert_at = document_end
        contents[insert_at:insert_at] = missing
        endings[insert_at:insert_at] = [newline] * len(missing)

    result: list[str] = []
    for index, content in enumerate(contents):
        ending = endings[index] if index < len(endings) else newline
        if not ending and (index < len(contents) - 1 or index == len(contents) - 1 and text.endswith(("\n", "\r"))):
            ending = newline
        result.append(content + ending)
    return "".join(result)


def _remove_document_key(text: str, key: str) -> str:
    """Remove a document scalar while keeping any attached comment line."""
    lines = text.splitlines(keepends=True)
    inside_document = False
    result: list[str] = []
    for line in lines:
        content = line.rstrip("\r\n")
        if re.match(r"^document\s*:", content):
            inside_document = True
            result.append(line)
            continue
        if content and not content.startswith((" ", "\t", "#")):
            inside_document = False
        if inside_document:
            match = re.match(rf"^(?P<indent>  ){re.escape(key)}:(?P<tail>.*)$", content)
            if match:
                _, comment = _split_yaml_comment(match.group("tail"))
                if comment:
                    ending = line[len(content):]
                    result.append(f"{match.group('indent')}{comment}{ending}")
                continue
        result.append(line)
    return "".join(result)


def _validate_intent(intent: dict[str, Any]) -> None:
    """Validate persisted intent against the checked-in JSON Schema."""
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "reportkit-intent.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        import jsonschema
    except ImportError:
        _validate_intent_subset(intent, schema)
        return
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(intent)


def _validate_intent_subset(intent: dict[str, Any], schema: dict[str, Any]) -> None:
    """Dependency-free enforcement of the intent schema's current keywords."""
    required = schema.get("required", ())
    missing = [key for key in required if key not in intent]
    if missing:
        raise ValueError(f"intent schema requires {', '.join(missing)}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(intent) - set(properties))
        if unexpected:
            raise ValueError(f"intent schema does not allow {', '.join(unexpected)}")
    for name, rules in properties.items():
        if name not in intent:
            continue
        value = intent[name]
        if "const" in rules and value != rules["const"]:
            raise ValueError(f"intent.{name} must equal {rules['const']!r}")
        if "enum" in rules and value not in rules["enum"]:
            raise ValueError(f"intent.{name} must be one of {rules['enum']!r}")
        types = rules.get("type")
        if types is not None:
            type_names = types if isinstance(types, list) else [types]
            checks = {
                "string": lambda item: isinstance(item, str),
                "null": lambda item: item is None,
            }
            if not any(checks.get(type_name, lambda _item: True)(value) for type_name in type_names):
                raise ValueError(f"intent.{name} has an invalid type")
        if isinstance(value, str) and len(value) < int(rules.get("minLength", 0)):
            raise ValueError(f"intent.{name} must not be empty")
        if rules.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (AttributeError, ValueError) as exc:
                raise ValueError(f"intent.{name} must be an ISO date-time") from exc


def _write_target_files(config_path: Path, config_text: str, intent_path: Path, intent: dict[str, Any]) -> None:
    """Write config and intent through sibling temp files to avoid truncation."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        for destination, contents in (
            (intent_path, json.dumps(intent, ensure_ascii=False, indent=2) + "\n"),
            (config_path, config_text),
        ):
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", dir=destination.parent,
                prefix=f".{destination.name}.", suffix=".tmp", delete=False,
            ) as stream:
                stream.write(contents)
                temporary = Path(stream.name)
            staged.append((temporary, destination))
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
