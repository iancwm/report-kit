"""Doctor treats bibtex as part of a full build (bibliography-and-contents spec)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_full_build_requires_bibtex(tmp_path: Path) -> None:
    real_bibtex = shutil.which("bibtex")
    if real_bibtex is None:
        pytest.skip("bibtex not installed; nothing to exclude")
    # check_executable only probes shutil.which, so a stub would count as
    # present: instead hide the real bibtex by dropping its directory from
    # PATH. Shadow the other TeX tools with symlinks so bibtex stays the
    # only missing piece even when they share bibtex's directory.
    shadow = tmp_path / "bin"
    shadow.mkdir()
    # Shadow every other tool the doctor probes (including kpsewhich, which
    # backs the font/package checks) so bibtex stays the only missing piece.
    for tool in ("pdflatex", "lualatex", "pandoc", "kpsewhich"):
        target = shutil.which(tool)
        if target is not None:
            (shadow / tool).symlink_to(target)
    # bibtex may be reachable through several PATH entries; hide every
    # directory that provides one.
    path_entries = [
        entry
        for entry in os.environ["PATH"].split(os.pathsep)
        if entry and not (Path(entry) / "bibtex").exists()
    ]
    env = dict(os.environ, PATH=os.pathsep.join([str(shadow), *path_entries]))
    assert shutil.which("bibtex", path=env["PATH"]) is None
    proc = subprocess.run(
        [sys.executable, str(REPO / "python_scripts" / "reportkit_doctor.py"), "--json"],
        capture_output=True, text=True, env=env,
    )
    payload = json.loads(proc.stdout)
    checks = {item["name"]: item["available"] for item in payload["checks"]}
    assert checks["bibtex"] is False
    assert payload["mode"] != "FULL BUILD"
