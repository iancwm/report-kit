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
    "selection": "Publication types, compatible themes, renderers, and the resolved target.",
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


def _quickstart_text(context: Mapping[str, Any]) -> str:
    selection = context["selection"]
    publications = context["capabilities"]["publication_types"]
    publication_lines = "; ".join(
        f"{name}: {record['selection_criteria']} Themes: {', '.join(record['themes'])}."
        for name, record in publications.items()
    )
    commands = context["commands"]
    return "\n".join([
        "ReportKit host-neutral quickstart.",
        f"Choose a publication type by intent: {publication_lines}",
        f"The current target is {selection['publication_type']}/{selection['requested_theme']}/{selection['renderer']}.",
        f"Author in a consumer project, then run `{commands['check']} --json` before conversion.",
        f"Build with `{commands['build']} --json`; on failure read its structured diagnostics and remediation.",
        f"For visual feedback run `{commands['render']} --pages 1 --json`, then `{commands['inspect']} --json`.",
        "Use the selection, primitives, authoring, commands, and toolchain slices only when needed.",
    ])


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
            "primitives": capabilities["primitives"],
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
