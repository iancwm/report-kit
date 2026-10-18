"""Safety gate for pytest tests that make real-model calls."""
from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Require both explicit selection and an env opt-in for model tests."""
    skip = pytest.mark.skip(reason="real-model evals require REPORTKIT_AGENT_EVAL=1")
    enabled = os.environ.get("REPORTKIT_AGENT_EVAL") == "1"
    for item in items:
        real_model = item.get_closest_marker("real_agent_eval") is not None
        selected_as_eval = item.get_closest_marker("agent_eval") is not None
        if real_model and (not enabled or not selected_as_eval):
            item.add_marker(skip)
