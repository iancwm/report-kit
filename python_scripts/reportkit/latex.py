"""LaTeX escaping helpers shared by ReportKit's generators."""
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
    """Escape all ten LaTeX text-mode metacharacters in *value*."""
    return "".join(_TEXT_ESCAPES.get(char, char) for char in value)


def tex_escape_url(value: str) -> str:
    """Escape URL characters that remain special inside ``\\href`` braces.

    URLs have different rules from ordinary text: percent signs, fragments,
    and query-string ampersands must be escaped, while characters such as
    underscores are valid URL content and should not be treated as prose.
    Callers must still validate URL schemes and reject unsafe TeX controls.
    """
    return value.replace("%", r"\%").replace("#", r"\#").replace("&", r"\&")
