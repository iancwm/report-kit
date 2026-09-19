from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from reportkit.context import build_context
from reportkit.context_budget import ALWAYS_LOADED_TOKEN_CEILING, build_context_slice, estimate_tokens


REPO = Path(__file__).resolve().parents[1]


def test_context_publishes_deterministic_slice_costs_under_the_quickstart_ceiling() -> None:
    context = build_context(REPO)
    budget = context["context_budget"]
    assert budget["accounting"] == "ceil(utf8_bytes / 4)"
    assert budget["always_loaded"] == "quickstart"
    assert budget["always_loaded_ceiling"] == ALWAYS_LOADED_TOKEN_CEILING == 2_000
    for name, record in budget["slices"].items():
        assert record["estimated_tokens"] == estimate_tokens(
            build_context_slice(context, name)["content"]
        )
    assert budget["slices"]["quickstart"]["estimated_tokens"] <= ALWAYS_LOADED_TOKEN_CEILING


def test_context_slice_is_small_and_schema_validated() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    result = subprocess.run(
        [str(REPO / "reportkit"), "context", "--slice", "quickstart", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    schema = json.loads((REPO / "schemas" / "reportkit-context-slice.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(payload)
    assert payload["slice"] == "quickstart"
    assert payload["estimated_tokens"] < 2_000
    assert "primitives" not in payload["content"]


def test_unfiltered_context_retains_the_full_legacy_capability_surface() -> None:
    context = build_context(REPO)
    assert "primitives" in context["capabilities"]
    assert "command_contract" in context
    assert "context_budget" in context
