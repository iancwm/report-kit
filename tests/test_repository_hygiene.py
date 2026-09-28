"""Checkout-independence guards for local Docker builds (defense in depth;
the release image is built from a pinned Git context)."""
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (REPO / ".git").exists(), reason="needs a Git checkout (the image has none)")


def _attr(path: str, name: str) -> str:
    out = subprocess.run(["git", "check-attr", name, "--", path], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return out.strip().rsplit(": ", 1)[-1]


@pytest.mark.parametrize("path", [
    "toolchain/Dockerfile", "toolchain/requirements.lock", "toolchain/toolchain.lock.json",
    "scripts/setup_tex.sh", "scripts/acceptance_check.sh", "reportkit", ".githooks/pre-commit",
    "latex_templates/reportkit.cls", "latex_templates/reportkit-algorithms.sty",
    "latex_templates/examples/editorial-feature/report.tex", ".gitattributes", ".dockerignore",
    ".github/workflows/contract-ci.yml", "python_scripts/reportkit/cli.py",
])
def test_engine_text_files_check_out_with_lf(path: str) -> None:
    assert _attr(path, "eol") == "lf", path


@pytest.mark.parametrize("path", ["font_data/GoogleSans-Regular.ttf", "font_data/reportkit-libertinus-fonts.tar.gz",
                                  "latex_templates/examples/editorial-feature/expected/page-01.png"])
def test_binary_assets_are_never_converted(path: str) -> None:
    assert _attr(path, "text") == "unset", path


def test_scripts_keep_executable_mode() -> None:
    required = {"reportkit", ".githooks/pre-commit", "scripts/setup_tex.sh", "scripts/acceptance_check.sh",
                "scripts/reportkit_container.py", "toolchain/container_build.py", "scripts/cross_host_gate.py",
                "toolchain/release_gates.sh"}
    staged = subprocess.run(["git", "ls-files", "-s", *sorted(required)], cwd=REPO, capture_output=True, text=True, check=True).stdout
    modes = {line.split("\t")[1]: line.split()[0] for line in staged.splitlines()}
    assert modes == {path: "100755" for path in required}


def test_dockerignore_keeps_local_state_out_of_the_context() -> None:
    patterns = {line.strip() for line in (REPO / ".dockerignore").read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")}
    assert {".git", "build", "output", "**/__pycache__", "**/.venv", "**/venv", ".pytest_cache", ".ruff_cache"} <= patterns
    for needed in ("font_data", "latex_templates", "python_scripts", "publication_pipeline", "toolchain", "scripts"):
        assert not any(p.rstrip("/") == needed for p in patterns), needed
