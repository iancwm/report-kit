"""Target-specific TeX starters (agent reasoning loop spec §4.5).

The canonical example chooses each target's opening grammar. The returned
starter is intentionally short, keeps its preamble aligned with the registered
renderer, and leaves the rest of the manuscript to the target's primitive
slice.
"""
from __future__ import annotations

from pathlib import Path
import re

from .publications import PUBLICATION_TYPES, RENDERERS


_CANONICAL_OPENINGS = {
    "technical-report": ("report.tex", "\\maketitle"),
    "equity-research": ("report.tex", "researchfrontpage"),
    "executive-brief": ("brief.tex", "briefheader"),
    "feature-article": ("report.tex", "featureopening"),
    "book": ("book-body.tex", "bookdetails"),
    "presentation": ("report.tex", "titleslide"),
}
_CANONICAL_DOCUMENTS = {
    "technical-report": "report.tex",
    "equity-research": "report.tex",
    "executive-brief": "report.tex",
    "feature-article": "report.tex",
    "book": "report.tex",
    "presentation": "report.tex",
}
_PREAMBLE_VALUES = {
    "setreportkitleftheader": "Publication / Department",
    "setreportkitfooter": "Organization",
    "setreportkitversion": "Draft",
    "setreportkitsubject": "Publication subject",
    "setreportkitkeywords": "ReportKit, publication, draft",
    "setreportkitlanguage": "en-US",
    "setreportkitfontpolicy": "fallback",
    "title": "Title",
    "subtitle": "Subtitle",
    "author": "Author or organization",
    "date": r"\today",
}


def _canonical_source(publication_type: str) -> tuple[Path, str]:
    record = PUBLICATION_TYPES[publication_type]
    filename, marker = _CANONICAL_OPENINGS[publication_type]
    root = Path(__file__).resolve().parents[2]
    source = root / record["canonical_example"] / filename
    if not source.is_file():
        raise FileNotFoundError(f"canonical example for {publication_type!r} is missing: {source}")
    text = source.read_text(encoding="utf-8")
    if marker not in text:
        raise ValueError(
            f"canonical example for {publication_type!r} no longer contains its opening marker {marker!r}"
        )
    return source, text


def _canonical_preamble(publication_type: str, theme: str) -> list[str]:
    """Adapt the metadata commands used by the target's canonical preamble."""
    record = PUBLICATION_TYPES[publication_type]
    root = Path(__file__).resolve().parents[2]
    source = root / record["canonical_example"] / _CANONICAL_DOCUMENTS[publication_type]
    if not source.is_file():
        raise FileNotFoundError(f"canonical preamble for {publication_type!r} is missing: {source}")
    text = source.read_text(encoding="utf-8")
    preamble = text.split(r"\begin{document}", 1)[0]
    command_names = {
        match.group(1)
        for match in re.finditer(r"(?m)^\s*\\([A-Za-z@]+)", preamble)
    }
    renderer = record["renderer"]
    class_name = RENDERERS[renderer]["class_adapter"]
    result = [f"\\documentclass[theme={theme},publication-type={publication_type}]{{{class_name}}}"]
    result.extend(
        f"\\{name}{{{_PREAMBLE_VALUES[name]}}}"
        for name in _PREAMBLE_VALUES
        if name in command_names
    )
    return result


def _opening(publication_type: str) -> str:
    """Return a compact opening scaffold whose construct is in the canonical example."""
    _source, _text = _canonical_source(publication_type)
    if publication_type == "technical-report":
        return "\\maketitle"
    if publication_type == "feature-article":
        return "\n".join([
            "\\begin{featureopening}",
            "  \\featureheadline[Section]{Article title}",
            "  \\featuredeck{A short deck that states the article's central turn.}",
            "  \\featurebyline{By Author}[Reading time]",
            "\\end{featureopening}",
        ])
    if publication_type == "equity-research":
        return "\n".join([
            "\\begin{researchfrontpage}",
            "  \\researchkicker{Sector / Region}",
            "  \\researchheadline{Company analysis headline}",
            "  \\researchdeck{State the estimate change, evidence, and investment implication.}",
            "  \\begin{ratingstrip}[itemcount=2]",
            "    \\ratingitem{Rating}{Rating}",
            "    \\ratingitem{Price target}{Value}",
            "  \\end{ratingstrip}",
            "\\end{researchfrontpage}",
        ])
    if publication_type == "executive-brief":
        return "\n".join([
            "\\begin{briefheader}{Organization \\textperiodcentered\\ Decision brief}{Decision headline}",
            "  One-sentence recommendation with the decision, value, and timing.",
            "  \\briefmeta{Decision owner}{Role}",
            "  \\briefmeta{Decision needed by}{Date}",
            "\\end{briefheader}",
        ])
    if publication_type == "book":
        return "\n".join([
            "\\RKFrontMatterBegin",
            "\\RKTitlePage[Short subtitle]{Book title}",
            "\\begin{bookdetails}{Book title: subtitle}",
            "  \\bookdetail{Edition}{Edition and publication date}",
            "\\end{bookdetails}",
            "\\RKContents",
            "\\RKMainMatterBegin",
        ])
    if publication_type == "presentation":
        return "\n".join([
            "\\begin{frame}[plain]",
            "  \\begin{titleslide}",
            "  \\end{titleslide}",
            "\\end{frame}",
        ])
    raise ValueError(f"no authoring opening is registered for {publication_type!r}")


_NATIVE_EXAMPLES = {
    "technical-report": "\n".join([
        "\\begin{principle}{Measure before choosing the intervention}",
        "Use the evidence to state one reusable rule.",
        "\\end{principle}",
        "",
        "\\begin{reportflow}",
        "  \\step{observe}{Observe the change}",
        "  \\step{decide}{Choose the response}",
        "  \\flowedge{observe}{decide}",
        "\\end{reportflow}",
        "",
        "\\begin{algorithmblock}{Running total}",
        "  \\AlgorithmInput{Input data}",
        "  \\AlgorithmOutput{Result}",
        "\\end{algorithmblock}",
    ]),
    "equity-research": "\n".join([
        "\\begin{researchproblem}{What would change the rating?}",
        "State the decision-relevant uncertainty and the evidence that resolves it.",
        "\\end{researchproblem}",
        "",
        "\\begin{reportflow}",
        "  \\step{estimate}{Update estimates}",
        "  \\step{value}{Reassess valuation}",
        "  \\flowedge{estimate}{value}",
        "\\end{reportflow}",
        "",
        "\\begin{exhibit}[title={Revenue mix supports the estimate change}, source={Company filings}]",
        "  \\begin{financialtable}",
        "    \\begin{tabular}{lr}Measure & Estimate \\\\ Revenue growth & 18\\% \\\\ \\end{tabular}",
        "  \\end{financialtable}",
        "\\end{exhibit}",
    ]),
    "executive-brief": "\n".join([
        "\\begin{decisionpoint}{Approve the staged migration}",
        "Approve the funded plan, subject to the stated service and timing gates.",
        "\\end{decisionpoint}",
        "",
        "\\begin{reportflow}",
        "  \\step{pilot}{Run the pilot}",
        "  \\step{scale}{Scale after the gate}",
        "  \\flowedge{pilot}{scale}",
        "\\end{reportflow}",
        "",
        "\\begin{exhibit}[title={Expected annual savings}, source={Planning model}]",
        "  \\begin{financialtable}",
        "    \\begin{tabular}{lr}Measure & Value \\\\ Annual savings & 7.9 \\\\ \\end{tabular}",
        "  \\end{financialtable}",
        "\\end{exhibit}",
    ]),
    "feature-article": "\n".join([
        "\\begin{featurecolumns}",
        "Article prose goes in this editorial column layout.",
        "\\end{featurecolumns}",
        "",
        "\\pullquote{One short line that carries the article's central tension.}[Source]",
    ]),
    "book": "\n".join([
        "\\begin{principle}{Keep the operating record current}",
        "A handbook should leave the reader with a repeatable practice.",
        "\\end{principle}",
        "",
        "\\begin{reportflow}",
        "  \\step{inspect}{Inspect the system}",
        "  \\step{record}{Record the finding}",
        "  \\flowedge{inspect}{record}",
        "\\end{reportflow}",
        "",
        "\\bookpart{Practice}",
        "\\section{A repeatable method}",
    ]),
    "presentation": "\n".join([
        "\\begin{frame}",
        "  \\begin{assertionslide}{Governance makes reuse safe}",
        "    \\begin{cardgrid}[columns=2]",
        "      \\carditem{Owner}{Name the decision owner.}",
        "      \\carditem{Gate}{State the evidence required.}",
        "    \\end{cardgrid}",
        "  \\end{assertionslide}",
        "\\end{frame}",
        "% Native charts are authored in Python with reportkit_viz and included as assets.",
    ]),
}

_CHART_EXAMPLE = "\n".join([
    "% Chart asset in figures.py:",
    "% import reportkit_viz as rkv",
    "% rkv.apply_theme('{theme}')",
    "% fig, ax = rkv.bar_chart({'A': 2, 'B': 1})",
    "% rkv.save_figure(fig, 'figures/chart.pdf')",
])


def document_template(publication_type: str, theme: str) -> str:
    """Return a TeX starter using ``publication_type``'s canonical opening."""
    publication = PUBLICATION_TYPES[publication_type]
    opening = _opening(publication_type)
    native_examples = "\n".join([
        _NATIVE_EXAMPLES[publication_type],
        _CHART_EXAMPLE.replace("{theme}", theme),
    ])
    return "\n".join([
        *_canonical_preamble(publication_type, theme),
        "",
        "\\begin{document}",
        opening,
        native_examples,
        "{{body}}",
        "\\end{document}",
        "",
    ])
