#!/usr/bin/env python3
"""Add explicit break opportunities to long code and URL literals."""
from __future__ import annotations

from pathlib import Path
import sys


COMMANDS = (r"\texttt{", r"\url{", r"\nolinkurl{")
BREAK_CHARS = set("/-=:.")


def _find_closing_brace(text: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _add_breaks(body: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(body):
        if body.startswith(r"\_", index):
            output.extend((r"\_", r"\allowbreak{}"))
            index += 2
            continue
        char = body[index]
        output.append(char)
        if char in BREAK_CHARS:
            output.append(r"\allowbreak{}")
        index += 1
    return "".join(output)


def wrap_long_literals(text: str) -> str:
    """Insert breakpoints without changing the visible literal text."""
    output: list[str] = []
    cursor = 0
    while cursor < len(text):
        starts = [(text.find(command, cursor), command) for command in COMMANDS]
        starts = [(position, command) for position, command in starts if position >= 0]
        if not starts:
            output.append(text[cursor:])
            break
        position, command = min(starts)
        output.append(text[cursor:position])
        opening = position + len(command) - 1
        closing = _find_closing_brace(text, opening)
        if closing < 0:
            output.append(text[position:])
            break
        output.append(text[position:opening + 1])
        output.append(_add_breaks(text[opening + 1:closing]))
        output.append("}")
        cursor = closing + 1
    return "".join(output)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: tex_hygiene.py <tex-file>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    path.write_text(wrap_long_literals(text), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
