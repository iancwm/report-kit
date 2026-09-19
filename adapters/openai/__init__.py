"""OpenAI-style tool definitions and a neutral CLI authoring smoke adapter."""

from .reportkit_tools import (
    CLIResult,
    build_tool_bundle,
    generate_tool_bundle,
    run_json,
    write_minimal_publication,
)

__all__ = [
    "CLIResult",
    "build_tool_bundle",
    "generate_tool_bundle",
    "run_json",
    "write_minimal_publication",
]
