"""Shared Markdown image-sentinel rendering and source-map coverage."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from publication_pipeline.scripts import publication_build
from reportkit.image_slots import ImageSlot


def _slot(slug: str, path: str, *, line: int, state: str) -> ImageSlot:
    return ImageSlot(
        slug=slug,
        purpose=f"Purpose for {slug}",
        caption=f"Caption for {slug}.",
        alt=f"Alt text for {slug}.",
        aspect_ratio="square",
        path=path,
        source="Created for the test fixture.",
        creator="ReportKit contributors",
        license="CC0-1.0",
        attribution="No external attribution required.",
        restrictions="None.",
        state=state,
        manuscript_file="manuscript/01.md",
        manuscript_line=line,
        unresolved_reason=None if state == "supplied" else f"missing image file {path}",
    )


def test_render_markdown_tracks_supplied_and_placeholder_images_and_existing_visuals(
    tmp_path: Path, monkeypatch,
) -> None:
    root = tmp_path / "publication"
    (root / "manuscript").mkdir(parents=True)
    (root / "fragments").mkdir()
    (root / "assets" / "images").mkdir(parents=True)
    manuscript = root / "manuscript" / "01.md"
    manuscript.write_text(
        "The supplied image.\n\n[[REPORTKIT-IMAGE:img:supplied]]\n\n"
        "The replaceable image.\n\n[[REPORTKIT-IMAGE:img:replaceable]]\n\n"
        "[[REPORTKIT-VISUAL:fig:flow]]\n",
        encoding="utf-8",
    )
    (root / "fragments" / "fig-flow.tex").write_text("\\begin{diagram}flow\\end{diagram}\n", encoding="utf-8")
    (root / "assets" / "images" / "supplied.png").write_bytes(b"image")
    slots = {
        "supplied": _slot("supplied", "assets/images/supplied.png", line=3, state="supplied"),
        "replaceable": _slot("replaceable", "assets/images/replaceable.png", line=7, state="placeholder"),
    }

    def fake_pandoc(command, *, cwd, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=manuscript.read_text(encoding="utf-8"),
            stderr="",
        )

    monkeypatch.setattr(publication_build, "run_limited", fake_pandoc)
    first = root / "first.tex"
    publication_build.render_markdown(root, manuscript, first, image_slots=slots)

    first_text = first.read_text(encoding="utf-8")
    assert "{supplied}" in first_text
    assert "{placeholder}" in first_text
    assert "\\begin{diagram}flow\\end{diagram}" in first_text
    first_map = first.with_name("first.map.json")
    map_data = json.loads(first_map.read_text(encoding="utf-8"))
    assert [(item["slug"], item["state"], item["source_start"]) for item in map_data["images"]] == [
        ("supplied", "supplied", 3),
        ("replaceable", "placeholder", 7),
    ]

    (root / "assets" / "images" / "replaceable.png").write_bytes(b"image")
    second = root / "second.tex"
    publication_build.render_markdown(root, manuscript, second, image_slots=slots)
    assert "{supplied}" in second.read_text(encoding="utf-8")
    assert "{placeholder}" not in second.read_text(encoding="utf-8")
