"""Gates for direct-TeX projects (agent reasoning loop spec §4.3)."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .config import theme_engine_conflict
from .diagnostics import make_diagnostic
from .target import TargetState


_DOCUMENTCLASS = re.compile(r"(?<!\\)\\documentclass\b")
_REQUIRED_OPTIONS = ("publication-type", "theme")


def _without_comments(source: str) -> str:
    """Remove TeX comments while preserving escaped percent signs and lines."""
    result: list[str] = []
    for line in source.splitlines(keepends=True):
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                content_end = len(line.rstrip("\r\n"))
                result.append(line[:index] + line[content_end:])
                break
        else:
            result.append(line)
    return "".join(result)


def _group(source: str, start: int, opening: str, closing: str) -> tuple[str, int] | None:
    """Read a balanced TeX option/class group beginning at ``start``."""
    if start >= len(source) or source[start] != opening:
        return None
    depth = 1
    cursor = start + 1
    value_start = cursor
    brace_depth = 0
    while cursor < len(source):
        char = source[cursor]
        if char == "\\":
            cursor += 2
            continue
        if opening == "[" and char == "{":
            brace_depth += 1
        elif opening == "[" and char == "}" and brace_depth:
            brace_depth -= 1
        elif char == opening and (opening != "[" or brace_depth == 0):
            depth += 1
        elif char == closing and (opening != "[" or brace_depth == 0):
            depth -= 1
            if depth == 0:
                return source[value_start:cursor], cursor + 1
        cursor += 1
    return None


def _split_options(value: str) -> list[str]:
    """Split comma-separated class options without splitting braced values."""
    parts: list[str] = []
    start = 0
    brace_depth = 0
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}" and brace_depth:
            brace_depth -= 1
        elif char == "," and brace_depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def read_class_options(tex: Path) -> dict[str, str] | None:
    """Parse ``publication-type=``/``theme=`` from ``\\documentclass[...]{reportkit}``.

    Returns ``None`` when the class, option list, or either required option is
    missing. Commented-out declarations are ignored.
    """
    try:
        source = _without_comments(tex.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None

    for match in _DOCUMENTCLASS.finditer(source):
        cursor = match.end()
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        option_group = _group(source, cursor, "[", "]")
        if option_group is None:
            continue
        option_text, cursor = option_group
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        class_group = _group(source, cursor, "{", "}")
        if class_group is None or class_group[0].strip() != "reportkit":
            continue

        options: dict[str, str] = {}
        for raw_option in _split_options(option_text):
            if "=" not in raw_option:
                continue
            key, value = raw_option.split("=", 1)
            normalized_key = key.strip()
            normalized_value = value.strip().strip("{}").strip()
            if normalized_key in options and options[normalized_key] != normalized_value:
                return None
            options[normalized_key] = normalized_value
        if all(options.get(key) for key in _REQUIRED_OPTIONS):
            return {key: options[key] for key in _REQUIRED_OPTIONS}
    return None


def tex_gates(state: TargetState, tex: Path) -> list[dict[str, Any]]:
    """``RK_TARGET_MISMATCH`` when class options are missing or disagree with
    ``publication.yaml``; runs before TeX (spec §4.3)."""
    options = read_class_options(tex)
    if options is None:
        diagnostic = make_diagnostic(
            "target_contract",
            "document.main must declare both publication-type and theme in "
            r"\documentclass[publication-type=...,theme=...]{reportkit}.",
            code="RK_TARGET_MISMATCH",
            source={"file": state.main or tex.name},
            details={
                "expected": {"publication-type": state.publication_type, "theme": state.theme},
                "actual": None,
            },
        )
        return [diagnostic]

    expected = {"publication-type": state.publication_type, "theme": state.theme}
    if all(options[key] == expected[key] for key in _REQUIRED_OPTIONS):
        return []
    diagnostic = make_diagnostic(
        "target_contract",
        "document.main class options do not match publication.yaml: "
        f"expected publication-type={state.publication_type}, theme={state.theme}; "
        f"found publication-type={options['publication-type']}, theme={options['theme']}.",
        code="RK_TARGET_MISMATCH",
        source={"file": state.main or tex.name},
        details={"expected": expected, "actual": options},
    )
    return [diagnostic]


def engine_gate(state: TargetState, requested_engine: str | None) -> list[dict[str, Any]]:
    """``RK_ENGINE_DOWNGRADE`` when the selected engine conflicts with the
    theme requirement (spec §4.3)."""
    if not requested_engine:
        return []
    conflict = theme_engine_conflict({"theme": state.theme, "engine": requested_engine})
    if conflict is None:
        return []
    return [make_diagnostic(
        "environment_error",
        conflict,
        code="RK_ENGINE_DOWNGRADE",
        source={"file": "publication.yaml"},
        details={"theme": state.theme, "requested_engine": requested_engine},
    )]
