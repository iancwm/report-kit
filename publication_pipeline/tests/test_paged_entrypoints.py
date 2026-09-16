"""D7 contract tests for the split paged publication entrypoints."""
from __future__ import annotations

from pathlib import Path
import re

from publication_pipeline.scripts.publication_build import stage_entrypoint
from reportkit.publications import PUBLICATION_TYPES, resolve_build_target


REPO = Path(__file__).resolve().parents[2]
TEMPLATES = REPO / "publication_pipeline" / "templates"
PAGED_PUBLICATIONS = {
    "technical-report": ("technical-report.tex", "default"),
    "equity-research": ("equity-research.tex", "institutional-research"),
}
PLACEHOLDERS = (
    "%%REPORTKIT_THEME%%",
    "%%REPORTKIT_PUBLICATION_TYPE%%",
    "%%REPORTKIT_CLASS%%",
)


def test_paged_publications_select_dedicated_entrypoints() -> None:
    for publication_type, (entrypoint_name, theme) in PAGED_PUBLICATIONS.items():
        record = PUBLICATION_TYPES[publication_type]
        assert record["template"] == entrypoint_name
        target = resolve_build_target(publication_type, theme, repo_root=REPO)
        assert target.template == entrypoint_name
        assert (TEMPLATES / entrypoint_name).is_file()


def test_paged_entrypoints_have_only_safe_target_slots_and_shared_base() -> None:
    base = (TEMPLATES / "paged-base.tex").read_text(encoding="utf-8")
    assert all(placeholder not in base for placeholder in PLACEHOLDERS)
    assert r"\input{metadata.tex}" in base
    assert r"\IfFileExists{links.tex}{\input{links.tex}}{}" in base
    assert r"\usepackage{reportkit-longform}" in base
    assert r"\newcommand{\RKPubPublicationDetails}" in base
    assert r"\RKFrontMatter" in base
    assert r"\input{body.tex}" in base

    for entrypoint_name in (value[0] for value in PAGED_PUBLICATIONS.values()):
        text = (TEMPLATES / entrypoint_name).read_text(encoding="utf-8")
        assert text.count(r"\documentclass") == 1
        assert text.count(r"\newcommand{\RKFrontMatter}") == 1
        assert text.count(r"\input{paged-base.tex}") == 1
        for placeholder in PLACEHOLDERS:
            assert text.count(placeholder) == 1
        assert r"\input{metadata.tex}" not in text
        assert r"\input{body.tex}" not in text


def test_paged_entrypoints_preserve_cover_combined_and_section_front_matter() -> None:
    base = (TEMPLATES / "paged-base.tex").read_text(encoding="utf-8")
    assert len(re.findall(r"^\\RKFrontMatter$", base, flags=re.MULTILINE)) == 1
    assert r"\ifRKPubHasCover" not in base
    assert r"\ifRKPubIsCombined" not in base

    for entrypoint_name in (value[0] for value in PAGED_PUBLICATIONS.values()):
        text = (TEMPLATES / entrypoint_name).read_text(encoding="utf-8")
        assert text.count(r"\ifRKPubHasCover") == 1
        assert text.count(r"\ifRKPubIsCombined") == 1
        assert r"\includegraphics[page=1,width=\textwidth,height=\textheight,keepaspectratio]{\RKPubCoverPath}" in text
        assert r"\RKTitlePage[\RKPubSubtitle]{\RKPubTitle}" in text
        assert r"\RKPubPublicationDetails" in text
        assert r"\RKContents" in text
        assert r"\RKMainMatterBegin" in text
        assert r"\maketitle" in text


def test_staging_a_paged_entrypoint_replaces_only_target_placeholders(tmp_path: Path) -> None:
    source = TEMPLATES / "equity-research.tex"
    destination = tmp_path / "publication.tex"
    stage_entrypoint(
        source,
        destination,
        theme="institutional-research",
        publication_type="equity-research",
        class_name="reportkit",
    )

    staged = destination.read_text(encoding="utf-8")
    assert r"\documentclass[theme=institutional-research,publication-type=equity-research]{reportkit}" in staged
    assert all(placeholder not in staged for placeholder in PLACEHOLDERS)
    assert r"\input{paged-base.tex}" in staged
    assert r"\RKPubPublicationDetails" in staged
