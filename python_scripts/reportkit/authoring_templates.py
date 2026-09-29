"""Target-specific document skeletons derived from canonical examples (spec §4.5)."""
from __future__ import annotations

from pathlib import Path
import re

from .publications import PUBLICATION_TYPES


_OPENING_MARKERS = {
    "technical-report": r"\maketitle",
    "equity-research": r"\begin{researchfrontpage}",
    "executive-brief": r"\begin{briefheader}",
    "feature-article": r"\begin{featureopening}",
    "book": r"\begin{bookdetails}",
    "presentation": r"\begin{titleslide}",
}


def _example_source(publication_type: str) -> tuple[Path, str]:
    """Read the canonical example's main source plus TeX files it inputs."""
    repo_root = Path(__file__).resolve().parents[2]
    example_root = repo_root / PUBLICATION_TYPES[publication_type]["canonical_example"]
    main_path = example_root / "report.tex"
    if not main_path.is_file():
        raise FileNotFoundError(f"canonical example source is missing: {main_path}")
    main_text = main_path.read_text(encoding="utf-8")
    sources = [main_text]
    for relative in re.findall(r"\\input\{([^}]+)\}", main_text):
        candidate = (example_root / relative).with_suffix(".tex")
        if candidate.is_file():
            sources.append(candidate.read_text(encoding="utf-8"))
    return main_path, "\n".join(sources)


def _opening_example(publication_type: str, source: str) -> str:
    """Return a compact starter for the opening used by the canonical source."""
    marker = _OPENING_MARKERS[publication_type]
    if marker not in source:
        raise ValueError(
            f"canonical example for {publication_type!r} no longer contains its opening primitive {marker!r}"
        )
    if publication_type == "technical-report":
        return r"\maketitle" + "\n" + r"\begin{execsummary}" + "\n{{summary}}\n" + r"\end{execsummary}"
    if publication_type == "equity-research":
        return "\n".join([
            r"\begin{researchfrontpage}",
            r"\researchkicker{Sector / Region}",
            r"\researchheadline{Company and thesis}",
            r"\researchdeck{Summarize the update and evidence.}",
            r"\begin{ratingstrip}",
            r"\ratingitem{Rating}{Recommendation}",
            r"\end{ratingstrip}",
            r"{{research content}}",
            r"\end{researchfrontpage}",
        ])
    if publication_type == "executive-brief":
        return "\n".join([
            r"\begin{briefheader}{Decision owner \textperiodcentered\ Decision brief}{Decision in one sentence}",
            r"\briefmeta{Decision owner}{Role}",
            r"\briefmeta{Decision needed by}{Date}",
            r"{{summary and evidence}}",
            r"\end{briefheader}",
        ])
    if publication_type == "feature-article":
        return "\n".join([
            r"\begin{featureopening}",
            r"\featureheadline[Section]{Headline}",
            r"\featuredeck{A concise narrative introduction.}",
            r"\featurebyline{By Author}",
            r"\end{featureopening}",
            "",
            r"\featuresection{Section title}[A one-sentence deck.]",
        ])
    if publication_type == "book":
        return "\n".join([
            r"\begin{bookdetails}{Title and subtitle}",
            r"\bookdetail{Edition}{Edition and publication date.}",
            r"\bookdetail{Disclaimer}{Scope and limitations.}",
            r"\end{bookdetails}",
            "",
            r"\bookpart{Part title}",
        ])
    return "\n".join([
        r"\begin{frame}[plain]",
        r"  \begin{titleslide}",
        r"  \end{titleslide}",
        r"\end{frame}",
        "",
        r"\begin{frame}",
        r"  \begin{messageslide}{Decision statement}",
        r"  \end{messageslide}",
        r"\end{frame}",
    ])


def document_template(publication_type: str, theme: str) -> str:
    """Return the target's compact TeX skeleton based on its canonical example."""
    if publication_type not in PUBLICATION_TYPES:
        raise ValueError(f"unknown publication type {publication_type!r}")
    main_path, source = _example_source(publication_type)
    main_text = main_path.read_text(encoding="utf-8")
    class_match = re.search(r"\\documentclass(?:\[[^]]*\])?\{([^}]+)\}", main_text)
    if class_match is None:
        raise ValueError(f"canonical example for {publication_type!r} has no document class")
    class_name = class_match.group(1)
    opening = _opening_example(publication_type, source)
    preamble = (
        f"\\documentclass[theme={theme},publication-type={publication_type}]{{{class_name}}}\n"
        "\\title{Title}\n"
        "\\author{Author}\n"
        "\\date{}\n"
        "\\begin{document}\n"
    )
    return preamble + opening + "\n{{body}}\n\\end{document}\n"
