"""Progressive-disclosure slices for the host-neutral ReportKit contract.

The full ``context`` payload is intentionally retained for v1.x callers.  This
module adds smaller, independently fetchable slices for hosts that need to
reserve context for the publication they are authoring.
"""
from __future__ import annotations

import json
import math
from typing import Any, Mapping


CONTEXT_SLICE_SCHEMA_VERSION = "1.0.0"
CONTEXT_SLICE_NAMES = ("quickstart", "selection", "primitives", "authoring", "commands", "toolchain")
ALWAYS_LOADED_SLICE = "quickstart"
ALWAYS_LOADED_TOKEN_CEILING = 2_000
TOKEN_ACCOUNTING = "ceil(utf8_bytes / 4)"

_SLICE_DESCRIPTIONS = {
    "quickstart": "Host-neutral selection, validation, build, and recovery loop.",
    "selection": "Publication types, compatible themes, renderers, language/script support, and the resolved target.",
    "primitives": "Primitive signatures and examples filtered for the requested target.",
    "authoring": "Authoring templates, chart setup, and trust-boundary details.",
    "commands": "Stable CLI commands and machine-readable command options.",
    "toolchain": "Resolved toolchain and reproducibility information.",
}


def estimate_tokens(value: Any) -> int:
    """Estimate tokens deterministically using UTF-8 bytes divided by four.

    This is deliberately an approximate accounting method rather than a model
    tokenizer.  It is stable across hosts and is suitable for enforcing the
    documented budget ceiling in CI.
    """
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return max(1, math.ceil(len(value.encode("utf-8")) / 4))


def _language_line(themes: Mapping[str, Any]) -> str:
    """Summarize theme language support in one line, grouped by declaration."""
    groups: dict[tuple[str, str, str], list[str]] = {}
    for name, record in sorted(themes.items()):
        support = record.get("language_support") or {}
        if "error" in support:
            continue
        key = (
            ", ".join(support.get("verified", [])) or "none",
            ", ".join(support.get("metadata_only", [])) or "none",
            ", ".join(support.get("scripts", {}).get("verified", [])) or "none",
        )
        groups.setdefault(key, []).append(name)
    parts = [
        f"{', '.join(names)}: verified {verified} ({scripts} script), metadata-only {metadata}"
        for (verified, metadata, scripts), names in groups.items()
    ]
    return (
        "Languages (set publication.yaml language:) -- " + "; ".join(parts)
        + ". RTL is unsupported. Scripts, font stacks, and locale typography are in the selection slice."
    )


def _target_text(context: Mapping[str, Any]) -> str:
    """The quickstart's durable target decision, never a silent default."""
    line = (context.get("target") or {}).get("line")
    if line:
        return str(line)
    return "TARGET NOT DECLARED — pick a row below and run `reportkit target set`; the build will refuse until then."


def _selection_text(context: Mapping[str, Any]) -> str:
    """Compact format × look selector with the source-mode contract."""
    publications = context["capabilities"]["publication_types"]
    themes = context["capabilities"]["themes"]
    rows = [
        "Format (structure) × look (theme): structure selects the page grammar and primitives; look sets typography, colour, and spacing.",
        "Format | Look | Source modes | Use for",
        "--- | --- | --- | ---",
    ]
    for name, record in publications.items():
        modes = record.get("source_modes") or {}
        mode_text = ", ".join(
            f"{mode}={value}" + (" (lock requires tex)" if mode == "markdown" and value == "opening-only" else "")
            for mode, value in modes.items()
        ) or "see target reference"
        engines = sorted({str(themes[theme].get("required_engine", "unknown")) for theme in record.get("themes", []) if theme in themes})
        rows.append(
            f"{name} | {', '.join(record.get('themes', []))} | {mode_text} | "
            f"{record.get('selection_criteria', '')} Engine: {', '.join(engines)}."
        )
    return "\n".join(rows)


def _quickstart_text(context: Mapping[str, Any]) -> str:
    commands = context["commands"]
    return "\n".join([
        "ReportKit host-neutral quickstart.",
        _selection_text(context),
        _target_text(context),
        _language_line(context["capabilities"]["themes"]),
        "Lock the selected format and look with `reportkit target set`, then scaffold and author in a consumer project.",
        f"Run `{commands['check']} --json` before conversion.",
        f"Build with `{commands['build']} --json`; on failure read its structured diagnostics and remediation.",
        f"Review with `{commands['render']} --pages 1 --json` and `reportkit review --json --visual-review done|unavailable`.",
        "After a context reset, or before delivery, run `reportkit status --json`.",
        "Use the selection, primitives, authoring, commands, and toolchain slices only when needed.",
    ])


def _compact_primitives(primitives: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Keep call signatures and examples while omitting full registry provenance."""
    result: dict[str, dict[str, Any]] = {}
    for kind, entries in primitives.items():
        result[str(kind)] = {}
        if not isinstance(entries, Mapping):
            continue
        for name, record in entries.items():
            if not isinstance(record, Mapping):
                continue
            filtered = {
                "name": record.get("name", name),
                "kind": record.get("kind", kind),
                "signature": record.get("signature", ""),
                "arguments": [
                    {
                        key: argument[key]
                        for key in ("name", "type", "required", "default")
                        if key in argument
                    }
                    for argument in record.get("arguments", [])
                    if isinstance(argument, Mapping)
                ],
                "example": record.get("example", ""),
            }
            for key in ("description", "constraints", "role", "targets"):
                if record.get(key):
                    filtered[key] = record[key]
            result[str(kind)][str(name)] = filtered
    return result


def slice_contents(context: Mapping[str, Any]) -> dict[str, Any]:
    """Return the content payload for every progressive-disclosure slice."""
    capabilities = context["capabilities"]
    return {
        "quickstart": {"text": _quickstart_text(context)},
        "selection": {
            "selection": context["selection"],
            "publication_types": capabilities["publication_types"],
            "themes": capabilities["themes"],
            "renderers": capabilities["renderers"],
        },
        "primitives": {
            "filters": context["filters"],
            "primitives": _compact_primitives(capabilities["primitives"]),
        },
        "authoring": {"authoring": capabilities["authoring"]},
        "commands": {
            "commands": context["commands"],
            "command_contract": context["command_contract"],
        },
        "toolchain": {"toolchain": context["toolchain"]},
    }


def build_budget_metadata(context: Mapping[str, Any]) -> dict[str, Any]:
    """Build deterministic cost metadata without duplicating slice payloads."""
    contents = slice_contents(context)
    metadata = {
        "accounting": TOKEN_ACCOUNTING,
        "always_loaded": ALWAYS_LOADED_SLICE,
        "always_loaded_ceiling": ALWAYS_LOADED_TOKEN_CEILING,
        "slices": {
            name: {
                "description": _SLICE_DESCRIPTIONS[name],
                "estimated_tokens": estimate_tokens(content),
                "loading": "always" if name == ALWAYS_LOADED_SLICE else "on-demand",
            }
            for name, content in contents.items()
        },
    }
    actual = metadata["slices"][ALWAYS_LOADED_SLICE]["estimated_tokens"]
    if actual > ALWAYS_LOADED_TOKEN_CEILING:
        raise ValueError(
            f"always-loaded context slice {ALWAYS_LOADED_SLICE!r} costs {actual} estimated tokens; "
            f"ceiling is {ALWAYS_LOADED_TOKEN_CEILING}"
        )
    return metadata


def build_context_slice(context: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Return one compact, schema-versioned context slice."""
    if name not in CONTEXT_SLICE_NAMES:
        raise ValueError(f"unknown context slice {name!r}; known values: {', '.join(CONTEXT_SLICE_NAMES)}")
    content = slice_contents(context)[name]
    return {
        "schema_version": CONTEXT_SLICE_SCHEMA_VERSION,
        "passed": context["passed"],
        "diagnostics": context["diagnostics"],
        "contract_version": context["contract_version"],
        "reportkit_version": context["reportkit_version"],
        "revision": context["revision"],
        "slice": name,
        "estimated_tokens": estimate_tokens(content),
        "context_budget": context["context_budget"],
        "content": content,
    }
