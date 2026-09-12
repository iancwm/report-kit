"""LaTeX escaping helpers shared by ReportKit's text emitters."""
from __future__ import annotations


_TEXT_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex_escape(value: str) -> str:
    """Escape all ten LaTeX text-mode metacharacters in ``value``."""
    return "".join(_TEXT_ESCAPES.get(char, char) for char in value)


def tex_escape_url(value: str) -> str:
    """Escape a URL for ``href`` without applying text-mode escaping.

    URLs have different rules from ordinary text: percent escapes must remain
    intact, while the URL characters ``%``, ``#``, and ``&`` need protection
    in the generated macro. Callers validate the URL separately before using
    this helper; it is intentionally not a general-purpose URL sanitizer.
    """
    return value.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")
