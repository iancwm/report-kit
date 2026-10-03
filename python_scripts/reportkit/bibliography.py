"""BibTeX bibliography support (bibliography-and-contents spec).

Dependency-free: the .bib file is scanned only for entry keys; BibTeX does
all formatting. Citation extraction mirrors what Pandoc ``--natbib`` and
natbib itself will treat as citations, so ``reportkit check`` and the build
agree on which keys must exist.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .config import resolve_bibliography_section
from .publications import PUBLICATION_TYPES

BIB_STYLES: tuple[str, ...] = ("numeric", "author-year")
SAFE_BIB_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.bib")
CONFIG_FILENAME = "reportkit-bibliography-config.tex"

_BIB_ENTRY = re.compile(r"@(?P<type>[A-Za-z]+)\s*[{(]\s*(?P<key>[^,\s{}()]+)\s*,")
_BIB_NON_ENTRIES = {"string", "comment", "preamble"}
_MD_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_MD_CODE_SPAN = re.compile(r"`+[^`]*`+")
# Pandoc citation: '@' not preceded by a word character (excludes e-mail),
# key starts with a letter/digit/underscore, may contain :.#$%&-+?<>~/ internally.
_MD_CITATION = re.compile(r"(?<![\w.@])-?@(?P<key>[A-Za-z0-9_][A-Za-z0-9_:.#$%&\-+?<>~/]*[A-Za-z0-9_])")
_TEX_CITE = re.compile(
    r"\\(?:cite|citep|citet|citealp|citealt|citeauthor|citeyear|citeyearpar|citenum|Citep|Citet|Citealp|Citealt|Citeauthor)\*?"
    r"(?:\s*\[[^\]]*\]){0,2}\s*\{(?P<keys>[^}]*)\}"
)


class BibliographyConfigError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class BibliographySettings:
    file: str
    path: Path
    stem: str
    style: str
    title: str
    include_uncited: bool


def resolve_bibliography(
    config: dict[str, Any], profile: str | None, publication_type: str, source_root: Path,
) -> BibliographySettings | None:
    section = resolve_bibliography_section(config, profile)
    if not section:
        return None
    record = PUBLICATION_TYPES.get(publication_type, PUBLICATION_TYPES["technical-report"])
    raw_file = section.get("file")
    if not raw_file:
        raise BibliographyConfigError("RK_BIBLIOGRAPHY_FILE_MISSING", "bibliography.file is required when a bibliography section is present")
    file = str(raw_file).replace("\\", "/")
    relative = Path(file)
    if relative.is_absolute() or ".." in relative.parts or not SAFE_BIB_PATH.fullmatch(file):
        raise BibliographyConfigError(
            "RK_BIBLIOGRAPHY_FILE_MISSING",
            f"bibliography.file must be a relative .bib path inside the project using letters, digits, '_', '-', '.', '/': {file!r}",
        )
    path = (source_root / relative).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError:
        raise BibliographyConfigError("RK_BIBLIOGRAPHY_FILE_MISSING", f"bibliography.file escapes the project: {file!r}") from None
    if not path.is_file():
        raise BibliographyConfigError("RK_BIBLIOGRAPHY_FILE_MISSING", f"bibliography.file not found: {file}")
    style = str(section.get("style") or record["bibliography_style"])
    if style not in BIB_STYLES:
        raise BibliographyConfigError(
            "RK_BIBLIOGRAPHY_STYLE_INVALID", f"bibliography.style must be one of {', '.join(BIB_STYLES)}; got {style!r}",
        )
    return BibliographySettings(
        file=file,
        path=path,
        stem=file[: -len(".bib")],
        style=style,
        title=str(section.get("title") or record["bibliography_title"]),
        include_uncited=bool(section.get("include_uncited", False)),
    )


def scan_bib_keys(text: str) -> list[tuple[str, int]]:
    keys: list[tuple[str, int]] = []
    for match in _BIB_ENTRY.finditer(text):
        if match.group("type").lower() in _BIB_NON_ENTRIES:
            continue
        keys.append((match.group("key"), text.count("\n", 0, match.start()) + 1))
    return keys


def markdown_citation_keys(text: str) -> list[tuple[str, int]]:
    keys: list[tuple[str, int]] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), 1):
        opener = _MD_FENCE.match(line)
        if opener:
            marker = opener.group(1)
            if fence is None:
                fence = marker[0] * 3
            elif marker.startswith(fence):
                fence = None
            continue
        if fence is not None:
            continue
        line = _MD_CODE_SPAN.sub("", line)
        keys.extend((match.group("key"), number) for match in _MD_CITATION.finditer(line))
    return keys


def tex_citation_keys(text: str) -> list[tuple[str, int]]:
    keys: list[tuple[str, int]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = re.sub(r"(?<!\\)%.*$", "", raw)
        for match in _TEX_CITE.finditer(line):
            for key in match.group("keys").split(","):
                key = key.strip()
                if key and key != "*":
                    keys.append((key, number))
    return keys
