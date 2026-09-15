"""F2 (tooling-hardening spec): bounded parallel section builds.

`--mode sections` used to loop over every manuscript entry strictly
serially. Before adding `--workers`-bounded concurrency, F2 required a
measured baseline first (see the spec's own "measure before optimising"):
an 8-section synthetic fixture built ~3s/section, ~25s serially and ~6.6s
with 4 workers on 4 cores -- each section's build() call is dominated by
external subprocess time (pandoc, TeX compiled twice, the PDF renderer,
the PDF inspector), which releases the GIL while it waits, so a bounded
thread pool parallelises the real bottleneck.

Running sections concurrently exposed a real, previously-latent bug: build
IDs were keyed on mode+timestamp alone ("section-<stamp>"), so two sections
resolved inside the same wall-clock second raced to the same history
filename. Serial execution never triggered it (each section's own history
file is already written by the time the next one is computed), but
concurrent sections routinely share a timestamp. Fixed by keying the
build ID on the manuscript stem too.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO / "publication_pipeline"

pytestmark = pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("pdflatex", "pandoc")),
    reason="requires a real LaTeX/Pandoc toolchain",
)


def _make_sections_fixture(root: Path, count: int) -> None:
    """A minimal multi-section publication: N sections, each with its own
    manuscript file and its own uniquely-labelled diagram fragment (a
    shared visual slug across sections would fail authoring validation)."""
    shutil.copy2(REPO / "publication_pipeline" / "example_publication" / "publication.yaml", root / "publication.yaml")
    (root / "manuscript").mkdir(parents=True, exist_ok=True)
    (root / "fragments").mkdir(parents=True, exist_ok=True)
    order_lines = []
    for index in range(1, count + 1):
        slug = f"section-{index}-flow"
        (root / "manuscript" / f"{index}-section.md").write_text(
            f"# Section {index}\n\nSynthetic fixture section {index}.\n\n"
            f"[[REPORTKIT-VISUAL:fig:{slug}]]\n",
            encoding="utf-8",
        )
        (root / "fragments" / f"fig-{slug}.tex").write_text(
            f"\\begin{{diagram}}[type=flow,label={{fig:{slug}}},caption={{Section {index} flow.}},"
            f"source={{Fixture.}},description={{A fixture flow for section {index}.}}]\n"
            "  \\begin{reportflow}\n"
            f"    \\step{{s{index}source}}{{Source}}\n"
            f"    \\step{{s{index}publish}}{{Publication}}\n"
            f"    \\flowedge{{s{index}source}}{{s{index}publish}}\n"
            "  \\end{reportflow}\n"
            "\\end{diagram}\n",
            encoding="utf-8",
        )
        order_lines.append(f"{index}-section.md")
    (root / "manuscript" / "order.txt").write_text("\n".join(order_lines) + "\n", encoding="utf-8")


def _run_sections(source: Path, output: Path, workers: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "python3", str(PIPELINE_ROOT / "scripts" / "publication_build.py"),
            "--mode", "sections", "--workers", str(workers),
            "--source-root", str(source), "--output-root", str(output),
            "--engine", "pdflatex",
        ],
        capture_output=True, text=True,
    )


def test_workers_below_one_is_rejected(tmp_path: Path) -> None:
    result = _run_sections(tmp_path, tmp_path / "build", workers=0)
    assert result.returncode == 2
    assert "--workers" in result.stderr


def test_parallel_sections_match_serial_and_avoid_build_id_collisions(tmp_path: Path) -> None:
    source = tmp_path / "publication"
    source.mkdir()
    _make_sections_fixture(source, count=3)

    serial = _run_sections(source, tmp_path / "serial-build", workers=1)
    assert serial.returncode == 0, serial.stderr
    parallel = _run_sections(source, tmp_path / "parallel-build", workers=3)
    assert parallel.returncode == 0, parallel.stderr

    for label, output in (("serial", tmp_path / "serial-build"), ("parallel", tmp_path / "parallel-build")):
        reports = sorted(output.glob("section-*/build-report.json"))
        assert len(reports) == 3, f"{label} run: expected 3 section builds, found {len(reports)}"
        for report_path in reports:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            assert report["status"] == "passed", f"{label} run: {report_path} did not pass"

        history_files = sorted((output / "history").glob("*.json"))
        # One history entry per section -- a build-ID collision would leave
        # fewer history files than section builds (one overwrote another).
        assert len(history_files) == 3, f"{label} run: expected 3 history entries, found {len(history_files)}"
        build_ids = {json.loads(path.read_text(encoding="utf-8"))["build_id"] for path in history_files}
        assert len(build_ids) == 3, f"{label} run: duplicate build_id across history entries"

    # The deterministic aggregate summary lists every section in manuscript
    # order regardless of which worker finished first.
    assert [line for line in parallel.stdout.splitlines() if line.startswith("REPORTKIT-SECTION")] == [
        "REPORTKIT-SECTION 1-section.md: exit 0",
        "REPORTKIT-SECTION 2-section.md: exit 0",
        "REPORTKIT-SECTION 3-section.md: exit 0",
    ]
