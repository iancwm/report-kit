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

That was fixed once already with `[ -d "$ROOT/.git" ]`, which introduced two
further problems: (1) it also misfires inside a git WORKTREE checkout (this
repo's own .worktrees/ convention included), where `.git` is a FILE holding
a `gitdir:` pointer, not a directory, even though a worktree is a perfectly
real, clonable checkout; and (2) since `.dockerignore` always excludes `.git`
from any local Docker build context, every CI job that runs this script
INSIDE a container now silently always takes the skip branch, meaning no CI
run anywhere exercises the fresh-clone init/doctor/build path any more.

The guard now uses `git -C "$ROOT" rev-parse --is-inside-work-tree`, which
correctly recognizes both a normal `.git`-directory checkout and a worktree
checkout as real, and still correctly fails (no .git at all) inside the
built image. A new `REPORTKIT_REQUIRE_FRESH_CLONE=1` escape hatch turns the
skip into a hard FAIL, for use on a host-level CI step (never inside the
built image) where a real checkout is expected to exist.

This test extracts the guard's exact if/else block (a slice of the
production script, not a re-implementation) so it stays byte-for-byte in
sync, and runs it standalone in crafted directories:

  * one with no .git -- must WARN and skip, never attempt the clone.
  * one that IS a real (minimal) git checkout -- must still attempt the
    clone (i.e. must not have been over-fixed into skipping unconditionally).
  * one that IS a real git WORKTREE checkout -- must also still attempt the
    clone, proving the worktree case is recognized as a real checkout.
  * the no-.git case again, with REPORTKIT_REQUIRE_FRESH_CLONE=1 -- must FAIL
    (hit=1) instead of warning and skipping quietly.
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


def _run_guard(root: Path, stub_bin: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
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
    env.pop("REPORTKIT_REQUIRE_FRESH_CLONE", None)
    env.update(extra_env or {})
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


def test_guard_recognizes_a_real_git_worktree_checkout(tmp_path: Path, stub_bin: Path) -> None:
    """The specific regression this fix wave targets: `[ -d "$ROOT/.git" ]`
    is false inside a git WORKTREE checkout, because `.git` there is a FILE
    holding a `gitdir:` pointer, not a directory -- even though a worktree is
    a perfectly real, clonable checkout, and is exactly how this repo's own
    development convention (.worktrees/) checks code out. Prove the new
    `git -C "$ROOT" rev-parse --is-inside-work-tree` guard recognizes a real
    `git worktree add` checkout as a real checkout (enters the if-branch),
    rather than misfiring into the skip branch the way the old `-d` check did.
    """
    scratch_repo = tmp_path / "scratch-repo"
    scratch_repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=scratch_repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=scratch_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=scratch_repo, check=True)
    (scratch_repo / "README.md").write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=scratch_repo, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "init"], cwd=scratch_repo, check=True)

    worktree_root = tmp_path / "worktree-checkout"
    subprocess.run(["git", "worktree", "add", "--quiet", str(worktree_root)], cwd=scratch_repo, check=True)
    assert (worktree_root / ".git").is_file(), "sanity check: a worktree's .git must be a file, not a directory"

    result = _run_guard(worktree_root, stub_bin)

    assert "skipping fresh-clone dry run" not in result.stderr, result.stderr
    assert "could not create fresh-clone acceptance checkout" not in result.stderr, result.stderr


def test_guard_fails_hard_when_require_fresh_clone_is_set_and_skip_would_happen(tmp_path: Path, stub_bin: Path) -> None:
    """REPORTKIT_REQUIRE_FRESH_CLONE=1 turns the (otherwise harmless) skip
    into a hard failure, for a host-level CI step where a real checkout is
    expected to exist -- restoring the coverage that .dockerignore excluding
    .git from every in-image run silently took away everywhere else."""
    fake_root = tmp_path / "no-git-root"
    fake_root.mkdir()

    result = _run_guard(fake_root, stub_bin, extra_env={"REPORTKIT_REQUIRE_FRESH_CLONE": "1"})

    assert "WARN" in result.stderr and "skipping fresh-clone dry run" in result.stderr, result.stderr
    assert "FAIL" in result.stderr and "REPORTKIT_REQUIRE_FRESH_CLONE" in result.stderr, result.stderr
    assert "HARNESS_HIT=1" in result.stdout, result.stdout + result.stderr


def test_guard_does_not_fail_when_require_fresh_clone_is_unset_and_skip_happens(tmp_path: Path, stub_bin: Path) -> None:
    """Without the opt-in, the skip stays a non-blocking WARN (unchanged
    behavior for every environment that doesn't explicitly ask to require
    it, e.g. a developer's machine without the full TeX/pandoc stack)."""
    fake_root = tmp_path / "no-git-root"
    fake_root.mkdir()

    result = _run_guard(fake_root, stub_bin)

    assert "HARNESS_HIT=0" in result.stdout, result.stdout + result.stderr
    assert "REPORTKIT_REQUIRE_FRESH_CLONE" not in result.stderr, result.stderr
