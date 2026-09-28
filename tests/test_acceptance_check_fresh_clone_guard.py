"""Regression test for the fresh-clone acceptance dry run's environment
guard in scripts/acceptance_check.sh.

Background: that guard used to require only that `git`, `pandoc`,
`pdflatex` be on PATH and the Python publication stack import cleanly
before attempting `git clone --no-local "$ROOT" "$FRESH_CLONE"`. Inside a
built toolchain image, `$ROOT` (/opt/reportkit) is COPY'd from a build
context that excludes .git (.dockerignore) or from a remote Git context
that never contains a .git directory either -- so `git` the binary is
present but `$ROOT` is not an actual checkout. The old guard then ran the
clone anyway and failed hard with "could not create fresh-clone acceptance
checkout", turning an expected, harmless skip into a build-breaking FAIL.

This test extracts the guard's exact if/else block (a slice of the
production script, not a re-implementation) so it stays byte-for-byte in
sync, and runs it standalone in two crafted directories:

  * one with no .git -- must WARN and skip, never attempt the clone.
  * one that IS a real (minimal) git checkout -- must still attempt the
    clone (i.e. must not have been over-fixed into skipping unconditionally).
"""
from __future__ import annotations

import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "acceptance_check.sh"

START_MARKER = "# Exercise the documented consumer setup from a clone-shaped checkout."
END_MARKER = 'if [ "$status" -ne 0 ]'


def _extract_guard_snippet() -> str:
    """Pull the exact if/.../else/.../fi guard block out of the real script."""
    content = SCRIPT.read_text(encoding="utf-8")
    start = content.index(START_MARKER)
    end = content.index(END_MARKER, start)
    snippet = content[start:end].strip("\n")
    assert snippet.startswith(START_MARKER)
    assert snippet.rstrip().endswith("fi")
    return snippet


def _write_stub_python3(bin_dir: Path) -> None:
    """A python3 stub that reports the publication deps as importable,
    without needing a real matplotlib/numpy/pandas/pymupitz stack in the
    test environment."""
    stub = bin_dir / "python3"
    stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _run_guard(root: Path, stub_bin: Path) -> subprocess.CompletedProcess:
    snippet = _extract_guard_snippet()
    harness = textwrap.dedent(f"""\
        set -uo pipefail
        ROOT={root}
        hit=0
        {snippet}
        echo "HARNESS_HIT=$hit"
        exit 0
        """)
    env = dict(os.environ)
    env["PATH"] = f"{stub_bin}:{env.get('PATH', '')}"
    return subprocess.run(
        ["bash", "-c", harness],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


@pytest.fixture()
def stub_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    _write_stub_python3(bin_dir)
    return bin_dir


def test_guard_skips_cleanly_when_root_has_no_git(tmp_path: Path, stub_bin: Path) -> None:
    """This is the Task 9 in-image failure mode: git/pandoc/pdflatex/python
    deps all present, but $ROOT is not a Git checkout (no .git)."""
    fake_root = tmp_path / "no-git-root"
    fake_root.mkdir()

    result = _run_guard(fake_root, stub_bin)

    assert "could not create fresh-clone acceptance checkout" not in result.stderr, result.stderr
    assert "WARN" in result.stderr and "skipping fresh-clone dry run" in result.stderr, result.stderr
    assert "HARNESS_HIT=0" in result.stdout, result.stdout + result.stderr


def test_guard_still_attempts_clone_when_root_is_a_real_checkout(tmp_path: Path, stub_bin: Path) -> None:
    """Guard against over-fixing into an unconditional skip: with a real
    .git present the clone must still be attempted (it may fail later for
    unrelated reasons, since this fake root has no `reportkit` script --
    that is not what this test is checking)."""
    fake_root = tmp_path / "real-git-root"
    fake_root.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=fake_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=fake_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=fake_root, check=True)
    (fake_root / "README.md").write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=fake_root, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "init"], cwd=fake_root, check=True)

    result = _run_guard(fake_root, stub_bin)

    # The clone-not-possible skip message must NOT fire here -- a real
    # checkout is present, so the guard should have entered the if-branch.
    assert "skipping fresh-clone dry run" not in result.stderr, result.stderr
    # The clone itself should have succeeded against a real local .git repo.
    assert "could not create fresh-clone acceptance checkout" not in result.stderr, result.stderr
