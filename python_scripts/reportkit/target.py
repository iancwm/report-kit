"""Persisted publication-target state (agent reasoning loop spec §4.2).

The target is a *decision*, recorded in the consumer project's
``publication.yaml`` ``document:`` block and ``.reportkit/intent.json``.
Every CLI command reloads it from disk through :func:`load_target`; nothing
here caches state across invocations.

The public signatures were frozen in Wave 0. Target state is always reloaded
from the consumer project's files; no CLI invocation depends on process-local
memory.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
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
    source_mode_declared: bool = False

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
    try:
        intent_value = json.loads((root / INTENT_PATH).read_text(encoding="utf-8"))
        intent = intent_value if isinstance(intent_value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        intent = None
    return TargetState(
        publication_type=publication_type,
        theme=str(document.get("theme")),
        renderer=str((PUBLICATION_TYPES.get(publication_type) or {}).get("renderer", "paged")),
        source_mode=str(document.get("source_mode") or "markdown"),
        main=str(document.get("main")),
        declared_by=str(document.get("declared_by", "default")),
        intent=intent,
        require_declared=require_declared,
        source_root=root,
        source_mode_declared=has_declared_source_mode(config),
    )


def has_declared_source_mode(config: dict[str, Any], profile: str | None = None) -> bool:
    """Whether the effective config explicitly chose a source mode.

    This distinction preserves legacy feature projects that predate
    ``document.source_mode`` while still rejecting an explicit Markdown
    choice for a target whose editorial grammar requires TeX.
    """
    document = config.get("document") if isinstance(config.get("document"), dict) else {}
    value = document.get("source_mode")
    publication_type = document.get("publication_type")
    profile_target_declared = False
    profiles = config.get("profiles") if isinstance(config.get("profiles"), dict) else {}
    selected = profiles.get(profile or "draft", {})
    if isinstance(selected, dict):
        nested = selected.get("document")
        if isinstance(nested, dict) and "source_mode" in nested:
            value = nested.get("source_mode")
        if isinstance(nested, dict) and "publication_type" in nested:
            publication_type = nested.get("publication_type")
            profile_target_declared = publication_type not in (None, "")
        if "source_mode" in selected:
            value = selected.get("source_mode")
        if "publication_type" in selected:
            publication_type = selected.get("publication_type")
            profile_target_declared = publication_type not in (None, "")
    if value not in (None, ""):
        return True
    # A profile that introduces a TeX-required target is a new decision, not a
    # legacy target whose source mode predates this field.
    return (
        isinstance(publication_type, str)
        and publication_type in PUBLICATION_TYPES
        and PUBLICATION_TYPES[publication_type].get("source_modes", {}).get("tex") == "required"
        and profile_target_declared
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
    or an incompatible type/theme pair).
    """
    root = Path(source_root)
    config_path = root / CONFIG_NAME
    try:
        config = load_publication_config(config_path)
    except (OSError, ValueError) as exc:
        diagnostic = make_diagnostic(
            "configuration_error", f"cannot update {CONFIG_NAME}: {exc}", code="RK_TARGET_CONFIG_INVALID",
        )
        return load_target(root), [diagnostic]

    current_doc = config.get("document") if isinstance(config.get("document"), dict) else {}
    current_resolved = resolve_document(config)
    alias: str | None = None

    if publication_type:
        if publication_type not in PUBLICATION_TYPES:
            resolved_alias = resolve_alias(publication_type)
            if resolved_alias is None:
                diagnostic = make_diagnostic(
                    "configuration_error",
                    f"unknown publication type or target alias {publication_type!r}",
                    code="RK_TARGET_TYPE_INVALID",
                    candidates=sorted(PUBLICATION_TYPES),
                )
                return load_target(root), [diagnostic]
            mapped_type, mapped_theme = resolved_alias
            alias = publication_type
            selected_type = mapped_type
        else:
            mapped_theme = None
            selected_type = publication_type
    else:
        selected_type = str(current_resolved["publication_type"])
        mapped_theme = None

    if selected_type not in PUBLICATION_TYPES:
        diagnostic = make_diagnostic(
            "configuration_error", f"unknown publication type {selected_type!r}", code="RK_TARGET_TYPE_INVALID",
            candidates=sorted(PUBLICATION_TYPES),
        )
        return load_target(root), [diagnostic]

    selected_record = PUBLICATION_TYPES[selected_type]
    if theme is not None:
        selected_theme = theme
    elif mapped_theme is not None:
        selected_theme = mapped_theme
    elif publication_type and selected_type != current_resolved["publication_type"]:
        selected_theme = str(selected_record.get("default_target", {}).get("theme", "default"))
    else:
        selected_theme = str(current_resolved.get("theme", "default"))

    if selected_theme not in selected_record.get("themes", []):
        themes = ", ".join(selected_record.get("themes", [])) or "none"
        diagnostic = make_diagnostic(
            "configuration_error",
            f"invalid target pair: structure={selected_type} look={selected_theme}; allowed looks: {themes}",
            code="RK_TARGET_PAIR_INVALID",
            candidates=selected_record.get("themes", []),
            details={"publication_type": selected_type, "theme": selected_theme},
        )
        return load_target(root), [diagnostic]

    source_modes = selected_record.get("source_modes", {})
    if source_mode is not None:
        selected_mode = source_mode
    elif source_modes.get("tex") == "required":
        selected_mode = "tex"
    elif current_doc.get("source_mode") and (
        not publication_type or selected_type == current_resolved["publication_type"]
    ):
        selected_mode = str(current_doc["source_mode"])
    else:
        selected_mode = "markdown"

    mode_support = source_modes.get(selected_mode)
    if selected_mode not in SOURCE_MODES or mode_support in (None, "unsupported") or (
        source_mode is not None
        and selected_mode == "markdown"
        and source_modes.get("tex") == "required"
    ):
        diagnostic = make_diagnostic(
            "target_contract",
            f"structure={selected_type} look={selected_theme} does not support source_mode={selected_mode}",
            code="RK_SOURCE_MODE_UNSUPPORTED",
            details={"publication_type": selected_type, "theme": selected_theme, "source_mode": selected_mode},
        )
        return load_target(root), [diagnostic]

    decided = decided_by or "agent-inferred"
    if decided not in DECIDED_BY:
        diagnostic = make_diagnostic(
            "configuration_error", f"invalid decided_by value {decided!r}", code="RK_TARGET_DECIDER_INVALID",
            candidates=DECIDED_BY,
        )
        return load_target(root), [diagnostic]

    # Keep the user's supplied request byte-for-byte as a Python string. An
    # omitted request (as in `init --publication-type ...`) is represented by
    # the empty string because the intent schema requires a request string.
    intent: dict[str, Any] = {
        "schema_version": INTENT_SCHEMA_VERSION,
        "request": request if request is not None else "",
        "publication_type": selected_type,
        "theme": selected_theme,
        "source_mode": selected_mode,
        "visual_reference": reference,
        "composition_brief": "composition-brief.json",
        "decided_by": decided,
        "locked_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    if alias is not None:
        intent["alias"] = alias

    document_values = {
        "publication_type": selected_type,
        "theme": selected_theme,
        "source_mode": selected_mode,
    }
    if selected_mode == "tex":
        document_values["main"] = str(current_doc.get("main") or current_resolved.get("main") or "report.tex")

    try:
        original_yaml = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
        updated_yaml = _update_document_block(original_yaml, document_values)
        _write_pair(root, config_path, updated_yaml, root / INTENT_PATH, intent)
    except OSError as exc:
        diagnostic = make_diagnostic(
            "configuration_error", f"cannot persist publication target: {exc}", code="RK_TARGET_WRITE_FAILED",
        )
        return load_target(root), [diagnostic]
    except ValueError as exc:
        diagnostic = make_diagnostic(
            "configuration_error", f"cannot update {CONFIG_NAME}: {exc}", code="RK_TARGET_CONFIG_INVALID",
        )
        return load_target(root), [diagnostic]

    return load_target(root), []


def resolve_alias(text: str) -> tuple[str, str] | None:
    """Map a registered natural-language alias to ``(type, default theme)``.

    Exact aliases win. For a longer request, a unique alias bounded by word
    boundaries is accepted; ambiguous requests are left for the caller/user.
    """
    normalized = _normalize_alias(text)
    if not normalized:
        return None
    matches: list[tuple[str, str, str]] = []
    for publication_type, record in PUBLICATION_TYPES.items():
        aliases = record.get("aliases", [])
        for alias in aliases if isinstance(aliases, list) else []:
            candidate = _normalize_alias(str(alias))
            if candidate and (normalized == candidate or re.search(rf"(?<!\w){re.escape(candidate)}(?!\w)", normalized)):
                theme = str(record.get("default_target", {}).get("theme", "default"))
                matches.append((publication_type, theme, candidate))
    exact = [match for match in matches if normalized == match[2]]
    selected = exact or matches
    distinct = {(publication_type, theme) for publication_type, theme, _ in selected}
    if len(distinct) != 1:
        return None
    return next(iter(distinct))


def target_gate(state: TargetState) -> list[dict[str, Any]]:
    """Require explicit target lock for opted-in projects; warn for legacy ones."""
    record = PUBLICATION_TYPES.get(state.publication_type, {})
    modes = record.get("source_modes", {})
    mode_support = modes.get(state.source_mode)
    if mode_support in (None, "unsupported") or (
        state.source_mode_declared
        and state.source_mode == "markdown"
        and modes.get("tex") == "required"
    ):
        return [make_diagnostic(
            "target_contract",
            f"structure={state.publication_type} look={state.theme} does not support source_mode={state.source_mode}",
            code="RK_SOURCE_MODE_UNSUPPORTED",
            details={
                "publication_type": state.publication_type,
                "theme": state.theme,
                "source_mode": state.source_mode,
            },
        )]
    if state.declared_by != "default":
        return []
    if state.require_declared:
        code = "RK_TARGET_UNDECLARED"
        message = (
            "The publication target is undeclared; the resolved values are defaults. "
            "Choose a structure and look before checking or building."
        )
    else:
        code = "RK_TARGET_IMPLICIT"
        message = (
            "The publication target was defaulted to structure="
            f"{state.publication_type} look={state.theme}; declare the decision to persist intent."
        )
    return [make_diagnostic("target_contract", message, code=code)]


def _normalize_alias(value: str) -> str:
    normalized = re.sub(r"[-_]+", " ", str(value).casefold())
    return " ".join(normalized.split())


def _yaml_scalar(value: str) -> str:
    """Use JSON's quoted string form, which is also a YAML scalar."""
    return json.dumps(value, ensure_ascii=False)


def _split_inline_comment(value: str) -> tuple[str, str]:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in "'\"":
            quote = None if quote == char else (char if quote is None else quote)
        elif char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip(), value[index:]
    return value.rstrip(), ""


def _update_document_block(text: str, values: dict[str, str]) -> str:
    """Update target scalars while preserving unrelated YAML and comments."""
    lines = text.splitlines(keepends=True)
    start: int | None = None
    end: int | None = None
    for index, line in enumerate(lines):
        body = line.rstrip("\r\n")
        if start is None:
            if re.match(r"^document\s*:\s*(?:#.*)?$", body):
                start = index
            continue
        # A new unindented mapping key ends this block. Blank lines and
        # comments stay attached to the existing document section.
        if body and not body[0].isspace() and not body.lstrip().startswith("#"):
            end = index
            break
    if start is None:
        separator = "" if not text or text.endswith(("\n", "\r")) else "\n"
        block = "document:\n" + "".join(f"  {key}: {_yaml_scalar(value)}\n" for key, value in values.items())
        return text + separator + block
    if end is None:
        end = len(lines)

    mapping_key = re.compile(r"^( +)([A-Za-z_][A-Za-z0-9_-]*)\s*:")
    child_indents: list[int] = []
    for line in lines[start + 1:end]:
        body = line.rstrip("\r\n")
        if not body.strip() or body.lstrip().startswith("#"):
            continue
        match = mapping_key.match(body)
        if match:
            child_indents.append(len(match.group(1)))
    # YAML permits any positive indentation width. Preserve the existing
    # document block's direct-child indentation instead of assuming two spaces.
    child_indent = min(child_indents, default=2)
    indent_text = " " * child_indent
    found: set[str] = set()
    child_pattern = re.compile(
        rf"^({re.escape(indent_text)})([A-Za-z_][A-Za-z0-9_-]*)(\s*:\s*)(.*?)(\r?\n)?$"
    )
    for index in range(start + 1, end):
        line = lines[index]
        match = child_pattern.match(line)
        if not match:
            continue
        indent, key, delimiter, tail, newline = match.groups()
        if key not in values:
            continue
        _, comment = _split_inline_comment(tail)
        lines[index] = f"{indent}{key}{delimiter}{_yaml_scalar(values[key])}"
        if comment:
            lines[index] += " " + comment
        lines[index] += newline or ""
        found.add(key)

    missing = [(key, value) for key, value in values.items() if key not in found]
    if missing:
        if not lines[start].endswith(("\n", "\r")):
            lines[start] += "\n"
        insertion = start + 1
        added = [f"{indent_text}{key}: {_yaml_scalar(value)}\n" for key, value in missing]
        lines[insertion:insertion] = added
    updated = "".join(lines)
    # Reject malformed section structure rather than write a config the
    # ReportKit parser cannot reload.
    return updated


def _write_pair(root: Path, config_path: Path, yaml_text: str, intent_path: Path, intent: dict[str, Any]) -> None:
    """Stage both files then replace them, minimizing partial lock writes."""
    root.mkdir(parents=True, exist_ok=True)
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_text = json.dumps(intent, ensure_ascii=False, indent=2) + "\n"
    config_temp = config_path.with_name(config_path.name + ".reportkit-tmp")
    intent_temp = intent_path.with_name(intent_path.name + ".reportkit-tmp")
    try:
        config_temp.write_text(yaml_text, encoding="utf-8")
        intent_temp.write_text(intent_text, encoding="utf-8")
        config_temp.replace(config_path)
        intent_temp.replace(intent_path)
    finally:
        config_temp.unlink(missing_ok=True)
        intent_temp.unlink(missing_ok=True)
