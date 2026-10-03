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
_MD_CITATION = re.compile(r"(?<![\w.@])-?@(?P<key>[A-Za-z0-9_](?:[A-Za-z0-9_:.#$%&\-+?<>~/]*[A-Za-z0-9_])?)")
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


from .diagnostics import make_diagnostic
from .latex import tex_escape

_PLACEMENT = re.compile(r"\\RKBibliography\b")
_MD_PLACEMENT = re.compile(r"^\s{0,3}(?:`{3,}|~{3,}|:::?)\s*reportkit[\s:/]+(?:references|RKBibliography)\b", re.MULTILINE)


def _citation_sources(source_root: Path, document: dict[str, Any]) -> list[tuple[str, list[tuple[str, int]], str]]:
    """Return (relative file, citations, text) for every authored source."""
    sources: list[tuple[str, list[tuple[str, int]], str]] = []
    if str(document.get("source_mode") or "markdown") == "tex":
        candidates = [source_root / str(document.get("main") or "report.tex")]
        fragments = source_root / "fragments"
        if fragments.is_dir():
            candidates.extend(sorted(fragments.glob("*.tex")))
        extract = tex_citation_keys
    else:
        manuscript = source_root / "manuscript"
        candidates = sorted(manuscript.glob("*.md")) if manuscript.is_dir() else []
        extract = markdown_citation_keys
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        sources.append((path.relative_to(source_root).as_posix(), extract(text), text))
    return sources


def bibliography_diagnostics(
    source_root: Path, config: dict[str, Any], profile: str | None, document: dict[str, Any],
) -> list[dict[str, Any]]:
    publication_type = str(document.get("publication_type") or "technical-report")
    sources = _citation_sources(source_root, document)
    cited = [(key, file, line) for file, keys, _ in sources for key, line in keys]
    try:
        settings = resolve_bibliography(config, profile, publication_type, source_root)
    except BibliographyConfigError as exc:
        return [make_diagnostic("configuration_error", str(exc), code=exc.code, source={"file": "publication.yaml"})]
    if settings is None:
        if not cited:
            return []
        key, file, line = cited[0]
        return [make_diagnostic(
            "configuration_error",
            f"{file}:{line}: citation @{key} but publication.yaml has no bibliography section",
            code="RK_CITATION_WITHOUT_BIBLIOGRAPHY", source={"file": file, "line": line},
        )]
    diagnostics: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key, line in scan_bib_keys(settings.path.read_text(encoding="utf-8")):
        if key in seen:
            diagnostics.append(make_diagnostic(
                "publication_validation", f"{settings.file}:{line}: duplicate .bib key {key!r}",
                code="RK_BIBLIOGRAPHY_DUPLICATE_KEY", source={"file": settings.file, "line": line},
            ))
        seen.add(key)
    for key, file, line in cited:
        if key not in seen:
            diagnostics.append(make_diagnostic(
                "publication_validation", f"{file}:{line}: citation key {key!r} is not in {settings.file}",
                code="RK_CITATION_UNDEFINED", source={"file": file, "line": line},
            ))
    if cited and str(document.get("source_mode") or "markdown") == "tex":
        if not any(_PLACEMENT.search(text) for _, _, text in sources):
            diagnostics.append(make_diagnostic(
                "publication_validation", "sources cite bibliography entries but never call \\RKBibliography",
                code="RK_BIBLIOGRAPHY_NOT_PLACED", source={"file": str(document.get("main") or "report.tex")},
            ))
    return diagnostics


_BLG_WARNING = re.compile(r"^(?:Warning--.*|I couldn't open .*)$", re.MULTILINE)


def write_bibliography_config(path: Path, settings: BibliographySettings) -> None:
    path.write_text(
        "% Generated by publication_build.py; do not edit.\n"
        f"\\renewcommand{{\\RKBibStyle}}{{{settings.style}}}\n"
        f"\\renewcommand{{\\RKBibFile}}{{{settings.stem}}}\n"
        f"\\renewcommand{{\\RKBibTitle}}{{{tex_escape(settings.title)}}}\n"
        + ("\\RKBibIncludeUncitedtrue\n" if settings.include_uncited else "\\RKBibIncludeUncitedfalse\n"),
        encoding="utf-8",
    )


def aux_has_citations(aux_text: str) -> bool:
    return "\\citation{" in aux_text


def blg_diagnostics(blg_text: str) -> list[dict[str, Any]]:
    return [
        make_diagnostic("bibliography_warning", match.group(0).strip(), code="RK_BIBLIOGRAPHY_WARNING")
        for match in _BLG_WARNING.finditer(blg_text)
    ]


def count_bbl_entries(bbl_text: str) -> int:
    return len(re.findall(r"^\\bibitem\b", bbl_text, flags=re.MULTILINE))
