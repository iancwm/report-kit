# ReportKit Docker Cross-Host Workflow Implementation Plan

**Status:** The launcher, in-image build, Linux CI gate, digest-bound release workflow, and consumer documentation are integrated in `main` through `70a8f28`. A real Windows/Docker Desktop gate remains required for each image release; the task checkboxes below retain the original execution checklist.
**Last updated:** 2026-09-30

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a digest-pinned `linux/amd64` ReportKit toolchain image through a gated release workflow, and turn a separate publication project into a PDF inside that image from Windows (NTFS, Docker Desktop in Linux-container mode) or Linux (ext4) with one stdlib-only host launcher.

**Architecture:** Three explicit operations. An **image build** runs in `.github/workflows/toolchain-release.yml` from a pinned Git context. A **push** is a later step in that workflow and never qualifies an image on its own: the pushed digest is re-gated on a clean runner and then held for a manual Windows gate. A **publication build** runs `scripts/reportkit_container.py`. The launcher validates the host source tree, streams it into a stopped container with `docker cp`, and runs `toolchain/container_build.py` inside the image with no network. It then streams `/work/result` back out, verifies it against a hash manifest, and swaps it into the output directory. The launcher contains no document logic; the in-image entrypoint only sequences existing `reportkit` CLI commands.

**Tech Stack:** Python 3.11+ standard library (host side: `tarfile`, `subprocess`, `unicodedata`), Python 3.13 in the image, Docker CLI and Buildx, GitHub Actions, GHCR, pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-09-28-reportkit-docker-cross-host-workflow-spec.md`

## Open decisions: defaults this plan assumes

The spec's section 6 leaves four decisions open. This plan builds on the defaults below. Confirm them before Task 9, or change the constants named here.

| Decision | Default in this plan | Where it lives |
| --- | --- | --- |
| Registry | `ghcr.io/iancwm/report-kit`. The release jobs get `packages: write` through `GITHUB_TOKEN`. | `IMAGE_REPO` in `toolchain-release.yml` |
| Input limits | 1 GiB total, 200 MiB per file, 20,000 files. Each can be changed with a flag. | `staging.Limits` |
| Runtime limits | 1800 s wall clock, 4 CPUs, 6 GiB memory without extra swap, 1024 PIDs. Each can be changed with a flag. | `docker.RunLimits` |
| Local image builds | Supported for development only. A reference without a digest needs `--allow-unpinned-image`, and the result then records `"release_eligible": false`. | launcher `run_build` |
| `linux/arm64` | Not in v1. On an ARM daemon the launcher runs under emulation with a warning. An arm64 image fails preflight. | `docker.Docker.image` |

## Global Constraints

- Host runtime requirements are only **Python 3.11+ and the Docker CLI**. Everything under `scripts/rk_container/`, `scripts/reportkit_container.py` and `scripts/cross_host_gate.py` imports only the standard library. Do not use `Path.is_junction`, `Path.walk` or any other 3.12-only API. CI enforces this by running the host tests on Python 3.11.
- V1 publishes and runs **`linux/amd64` only**. Every `docker create`/`pull`/`buildx build` passes `--platform linux/amd64`.
- Docker is always invoked with an **argument list**, never `shell=True` and never a command string built from a path.
- **Do not bind-mount** the publication. Inputs go in through `docker cp --archive - <id>:/work`, and results come out through `docker cp <id>:/work/result -`.
- The build container runs with `--network none`, bounded CPU, memory, PIDs and time, `--cap-drop ALL`, `--security-opt no-new-privileges`, no mounts, and as the non-root user **uid/gid 10001**. TeX shell escape stays disabled.
- The entrypoint writes only under `/work/build` and `/work/result`. `/work/source` is verified and then left untouched.
- Consumers pin `ghcr.io/iancwm/report-kit@sha256:<digest>`. Moving tags and `latest` are never release inputs.
- Exit codes follow the existing CLI (`python_scripts/reportkit/cli.py:49-54`): `0` ok, `2` config, `3` validation, `4` compile, `5` environment, `70` internal.
- Publication content stays outside this repository (`references/repository-boundary.md`). Fixtures come only from `latex_templates/examples/editorial-feature/` and `publication_pipeline/example_publication/`.
- A TeX exit code alone never counts as editorial success. The audit (when `editorial-brief.json` exists), the diagnostic gate, render and inspect are all required steps.
- Do not silently rename, re-encode or line-ending-convert publication bytes.
- Ruff runs over `python_scripts publication_pipeline scripts tests adapters toolchain`. Add `toolchain` to the existing command.

## Review Focus

These five inputs are the most likely to hurt a real user and are not otherwise pinned by a task's tests. Each has a test in the task named on its line.

1. **Output root is an existing folder the launcher did not create**, such as the user's Documents folder or the publication root itself. It must be refused before any write and must never be renamed or deleted. (Task 5, `test_refuses_unmanaged_output_root`, `test_refuses_output_root_containing_source`)
2. **A Windows PDF viewer holds the previous output PDF open**, so the rename of the old output fails with `PermissionError`. The previous output must stay intact, the incoming directory must be cleaned up, and the error must be `RK_OUTPUT_LOCKED` with an actionable message. (Task 5, `test_install_keeps_previous_output_when_rename_is_locked`)
3. **PDFs that are real inputs** (`figures/*.pdf` in the editorial fixture) must be staged. Only prior build PDFs at the source root are excluded. (Task 3, `test_nested_pdfs_are_inputs_but_root_pdfs_are_not`)
4. **A hung or runaway TeX run** must hit the wall-clock limit. Then the container is killed and removed, the exit is nonzero, and the prior output is unchanged. **Ctrl-C during a build** must also remove the container and the incoming directory. (Task 6, `test_timeout_kills_and_removes_container`, `test_keyboard_interrupt_still_removes_container`)
5. **A source file edited while staging runs**, for example by an editor autosave, must abort the build before anything reaches the container. A half-changed file must never be built. (Task 3, `test_file_changed_during_archive_is_rejected`)

---

## File structure

| Path | Status | Responsibility |
| --- | --- | --- |
| `.gitattributes` | create | LF for Dockerfile, shell, TeX, Python, lock and control files; binary for fonts and images |
| `.dockerignore` | create | Keep `.git`, build output, caches and venvs out of local Docker contexts |
| `toolchain/Dockerfile` | modify | Commit/ref build args and labels; build user 10001; `/work` layout |
| `publication_pipeline/scripts/publication_build.py:460-475,1147` | modify | Commit/ref fall back to `REPORTKIT_COMMIT`/`REPORTKIT_REF` when the checkout has no `.git` |
| `toolchain/container_build.py` | create | In-image entrypoint that sequences the existing `reportkit` commands and writes `/work/result` plus `container-build.json` |
| `scripts/rk_container/__init__.py` | create | Empty package marker |
| `scripts/rk_container/staging.py` | create | Walk, validate, hash and tar the publication; input manifest |
| `scripts/rk_container/docker.py` | create | Docker CLI adapter: preflight, create, copy in/out, start, remove |
| `scripts/rk_container/results.py` | create | Output-root validation, safe result extraction, hash verification, atomic install, failure directory |
| `scripts/reportkit_container.py` | create | Host launcher CLI: `build`, `summarize` |
| `scripts/cross_host_gate.py` | create | The acceptance gate both hosts run (`run`, `compare`) |
| `scripts/image_release_manifest.py` | create | Machine-readable image release manifest |
| `toolchain/release_gates.sh` | create | In-image gates used by the release and smoke jobs |
| `.github/workflows/contract-ci.yml` | modify | Path filters, `toolchain` in ruff, Linux container gate, Windows/Linux host unit job |
| `.github/workflows/toolchain-release.yml` | create | Build, gate, push, digest smoke, manual Windows gate, promote |
| `tests/test_repository_hygiene.py` | create | Checks for attributes, executable bits and `.dockerignore` |
| `publication_pipeline/tests/test_engine_provenance.py` | create | Commit fallback |
| `tests/test_container_entrypoint.py` | create | Entrypoint with a fake runner |
| `tests/test_container_staging.py` | create | Staging rules |
| `tests/test_container_docker.py` | create | Docker adapter with a fake CLI |
| `tests/test_container_results.py` | create | Result safety and atomicity |
| `tests/test_container_launcher.py` | create | End-to-end launcher against a fake Docker |
| `tests/test_cross_host_gate.py` | create | Summary comparison and fixture materialization |
| `tests/test_container_integration.py` | create | Real-image gate (skips unless `REPORTKIT_CONTAINER_TEST_IMAGE` is set; fails when `REPORTKIT_REQUIRE_DOCKER=1` and no image) |
| `tests/test_image_release_manifest.py` | create | Manifest validation |
| `references/docker-workflow.md` | create | User and release-operator guide, including the Windows gate procedure |
| `SKILL.md`, `README.md`, `AGENTS.md`, `CHANGELOG.md` | modify | Make Docker the recommended cross-host path |

**Host tests and `tests/conftest.py`.** `tests/conftest.py` imports `pymupdf` unconditionally. The host-only jobs (Windows and the Linux launcher job) therefore run pytest with `--noconftest`. The new host tests must not rely on any fixture from `conftest.py`. They add `scripts/` to `sys.path` themselves:

```python
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
```

---

### Task 1: Repository hygiene (`.gitattributes`, `.dockerignore`, CI filters)

**Files:**
- Create: `.gitattributes`, `.dockerignore`, `tests/test_repository_hygiene.py`
- Modify: `.github/workflows/contract-ci.yml` (path filters and the ruff target list only)

**Interfaces:**
- Consumes: nothing.
- Produces: LF guarantees for `toolchain/requirements.lock` and `toolchain/toolchain.lock.json`. The Dockerfile hashes these files, so a CRLF checkout would otherwise break a local image build. Executable bits on every script later tasks add.

- [ ] **Step 1: Write the failing test**

`tests/test_repository_hygiene.py`:

```python
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
    required = {"reportkit", ".githooks/pre-commit", "scripts/setup_tex.sh", "scripts/acceptance_check.sh"}
    staged = subprocess.run(["git", "ls-files", "-s", *sorted(required)], cwd=REPO, capture_output=True, text=True, check=True).stdout
    modes = {line.split("\t")[1]: line.split()[0] for line in staged.splitlines()}
    assert modes == {path: "100755" for path in required}


def test_dockerignore_keeps_local_state_out_of_the_context() -> None:
    patterns = {line.strip() for line in (REPO / ".dockerignore").read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")}
    assert {".git", "build", "output", "**/__pycache__", "**/.venv", "**/venv", ".pytest_cache", ".ruff_cache"} <= patterns
    for needed in ("font_data", "latex_templates", "python_scripts", "publication_pipeline", "toolchain", "scripts"):
        assert not any(p.rstrip("/") == needed for p in patterns), needed
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest --noconftest tests/test_repository_hygiene.py -q`
Expected: FAIL. `eol` is `unspecified`, `text` is `unspecified`, and `.dockerignore` is missing.

- [ ] **Step 3: Add `.gitattributes`**

```gitattributes
# Keep engine text byte-stable across Windows and Linux checkouts. The
# release image is built from a pinned Git context; these rules protect local
# builds, whose Dockerfile hash-checks toolchain/requirements.lock.
* text=auto
Dockerfile text eol=lf
.dockerignore text eol=lf
.gitattributes text eol=lf
.gitignore text eol=lf
.githooks/* text eol=lf
reportkit text eol=lf
*.sh text eol=lf
*.py text eol=lf
*.tex text eol=lf
*.sty text eol=lf
*.cls text eol=lf
*.def text eol=lf
*.bib text eol=lf
*.lock text eol=lf
*.json text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.toml text eol=lf
*.md text eol=lf
*.txt text eol=lf
*.ttf binary
*.otf binary
*.pdf binary
*.png binary
*.jpg binary
*.jpeg binary
*.gz binary
```

- [ ] **Step 4: Add `.dockerignore`**

```gitignore
# Local Docker contexts only. The release build uses a pinned Git context
# (.github/workflows/toolchain-release.yml); this keeps a developer's local
# state out of `docker build .` from any host.
.git
.claude
.agents
.superpowers
.pytest_cache
.ruff_cache
**/__pycache__
**/*.py[cod]
**/.venv
**/venv
build
output
```

Root `build/` holds about 2,200 tracked debug artifacts from commit `c1a2ecc`. No engine code reads them. Step 7 confirms that the image test suite still passes without them. Removing them from Git is a separate change and is out of scope here.

- [ ] **Step 5: Renormalize and confirm no content change**

Run: `git add --renormalize . && git status --short`
Expected: only `.gitattributes`, `.dockerignore` and the new test are listed. (`git ls-files --eol | grep i/crlf` is empty today, so nothing is renormalized.) If a file does show up, stop and review it before continuing.

- [ ] **Step 6: Update the CI path filters and ruff targets**

In `.github/workflows/contract-ci.yml`, add these entries to **both** the `pull_request.paths` and `push.paths` lists:

```yaml
      - ".gitattributes"
      - ".dockerignore"
      - ".github/workflows/**"
      - "reportkit"
```

(`.github/workflows/**` replaces the existing single `.github/workflows/contract-ci.yml` entry.) Change `ruff check python_scripts publication_pipeline scripts tests adapters` to `ruff check python_scripts publication_pipeline scripts tests adapters toolchain`.

- [ ] **Step 7: Run the tests and a local image build**

Run: `python3 -m pytest --noconftest tests/test_repository_hygiene.py -q`
Expected: PASS.

Run: `docker build --file toolchain/Dockerfile --tag reportkit-local . && docker run --rm --entrypoint /bin/bash reportkit-local -lc 'python -m pytest tests publication_pipeline/tests -q -x'`
Expected: the build succeeds and the tests pass. This proves the image never needed `build/`.

- [ ] **Step 8: Commit**

```bash
git add .gitattributes .dockerignore tests/test_repository_hygiene.py .github/workflows/contract-ci.yml
git commit -m "build: pin LF engine text and trim local Docker context"
```

---

### Task 2: Image provenance and build user

**Files:**
- Modify: `toolchain/Dockerfile` (append before the final `ENV`)
- Modify: `publication_pipeline/scripts/publication_build.py:460-475` and `:1147`
- Test: `publication_pipeline/tests/test_engine_provenance.py`

**Interfaces:**
- Produces: image env vars `REPORTKIT_COMMIT` and `REPORTKIT_REF`. OCI labels `org.opencontainers.image.revision` and `.version`. User `reportkit` uid/gid 10001 with home `/work/home`. Directories `/work`, `/work/home`, `/work/build` and `/work/result` owned by 10001. `publication_build.engine_commit() -> str` and `engine_ref() -> str`.

- [ ] **Step 1: Write the failing test**

`publication_pipeline/tests/test_engine_provenance.py`:

```python
"""The image has no .git; commit provenance must come from the build args."""
from __future__ import annotations

import publication_build


def test_commit_falls_back_to_image_environment(monkeypatch) -> None:
    monkeypatch.setattr(publication_build, "git_value", lambda args: "unknown")
    monkeypatch.setenv("REPORTKIT_COMMIT", "a" * 40)
    monkeypatch.setenv("REPORTKIT_REF", "v1.9.3")
    assert publication_build.engine_commit() == "a" * 40
    assert publication_build.engine_ref() == "v1.9.3"


def test_checkout_value_wins_over_environment(monkeypatch) -> None:
    monkeypatch.setattr(publication_build, "git_value", lambda args: "b" * 40)
    monkeypatch.setenv("REPORTKIT_COMMIT", "a" * 40)
    assert publication_build.engine_commit() == "b" * 40


def test_unknown_when_neither_is_available(monkeypatch) -> None:
    monkeypatch.setattr(publication_build, "git_value", lambda args: "unknown")
    monkeypatch.delenv("REPORTKIT_COMMIT", raising=False)
    monkeypatch.setenv("REPORTKIT_REF", "unknown")
    assert publication_build.engine_commit() == "unknown"
    assert publication_build.engine_ref() == "unknown"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest publication_pipeline/tests/test_engine_provenance.py -q`
Expected: FAIL with `AttributeError: module 'publication_build' has no attribute 'engine_commit'`.

- [ ] **Step 3: Implement the fallback**

In `publication_build.py`, directly after `git_value`:

```python
def engine_commit() -> str:
    """Engine commit from the checkout, else the image's baked build arg."""
    value = git_value(["rev-parse", "HEAD"])
    return value if value != "unknown" else os.environ.get("REPORTKIT_COMMIT", "unknown") or "unknown"


def engine_ref() -> str:
    """Engine ref from the checkout, else the image's baked build arg."""
    value = git_value(["describe", "--tags", "--always"])
    return value if value != "unknown" else os.environ.get("REPORTKIT_REF", "unknown") or "unknown"
```

Then replace `git_value(["describe", "--tags", "--always"])` in `write_lock` with `engine_ref()`. Replace both `git_value(["rev-parse", "HEAD"])` calls (in `write_lock` and in the report dict at line ~1147) with `engine_commit()`. Confirm `os` is already imported at the top of the module, and add the import if it is not.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest publication_pipeline/tests/test_engine_provenance.py publication_pipeline/tests -q`
Expected: PASS.

- [ ] **Step 5: Extend the Dockerfile**

Insert this immediately **before** the final `ENV PATH=...` block. It sits late in the file so that changing the commit does not invalidate the TeX/apt layers:

```dockerfile
# Build user for container publication builds (scripts/reportkit_container.py
# runs with --user 10001:10001). /work lives on the container's own Linux
# filesystem; nothing here is bind-mounted from the host.
RUN groupadd --gid 10001 reportkit \
 && useradd --uid 10001 --gid 10001 --home-dir /work/home --no-create-home \
      --shell /usr/sbin/nologin reportkit \
 && install -d -o 10001 -g 10001 -m 0755 /work /work/home /work/build /work/result

ARG REPORTKIT_COMMIT=unknown
ARG REPORTKIT_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/iancwm/report-kit" \
      org.opencontainers.image.revision="${REPORTKIT_COMMIT}" \
      org.opencontainers.image.version="${REPORTKIT_REF}"
```

Add `REPORTKIT_COMMIT=${REPORTKIT_COMMIT}` and `REPORTKIT_REF=${REPORTKIT_REF}` to the existing final `ENV` block. Leave `ENTRYPOINT` unchanged: CI and existing users still run `reportkit` as the entrypoint.

- [ ] **Step 6: Verify in the image**

Run:
```bash
docker build --file toolchain/Dockerfile --build-arg REPORTKIT_COMMIT=$(git rev-parse HEAD) --tag reportkit-local .
docker run --rm --entrypoint /bin/bash reportkit-local -lc 'id reportkit && stat -c "%u %n" /work /work/home /work/build /work/result && echo $REPORTKIT_COMMIT'
docker run --rm --entrypoint /bin/bash reportkit-local -lc 'python -m pytest tests/test_agent_contract.py -q'
```
Expected: `uid=10001(reportkit)`, all four paths owned by `10001`, the full SHA printed, and the Dockerfile contract test (`tests/test_agent_contract.py:552`) still passing.

- [ ] **Step 7: Commit**

```bash
git add toolchain/Dockerfile publication_pipeline/scripts/publication_build.py publication_pipeline/tests/test_engine_provenance.py
git commit -m "build: bake engine commit into the image and add the build user"
```

---

### Task 3: Host staging (walk, validate, hash, tar)

**Files:**
- Create: `scripts/rk_container/__init__.py` (empty), `scripts/rk_container/staging.py`
- Test: `tests/test_container_staging.py`

**Interfaces:**
- Produces (used by Tasks 5, 6 and 8):
  - `Limits(max_total_bytes: int = 1 GiB, max_file_bytes: int = 200 MiB, max_files: int = 20_000)`
  - `Problem(code: str, path: str, message: str)` with `.as_dict() -> dict`
  - `StagingError(problems: list[Problem])` with `.problems`
  - `StagedFile(relative: str, absolute: Path, size: int, sha256: str)`
  - `Staging(root: Path, files: list[StagedFile], directories: list[str], excluded: list[str])` with `.manifest() -> dict`, `.manifest_bytes() -> bytes`, `.manifest_sha256() -> str`, `.total_bytes`
  - `collect(root: Path, limits: Limits = Limits()) -> Staging` raises `StagingError`
  - `write_archive(staging: Staging, stream: BinaryIO) -> None` writes `source/...` and `input-manifest.json`, with every entry owned by 10001:10001
  - `NONPORTABLE_CHARACTERS: frozenset[str]`, `BUILD_UID = BUILD_GID = 10001`, `MANIFEST_SCHEMA = "reportkit-input-manifest/1"`

- [ ] **Step 1: Write the failing tests**

`tests/test_container_staging.py`:

```python
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from rk_container import staging  # noqa: E402
from rk_container.staging import Limits, StagingError, collect, write_archive  # noqa: E402


def _tree(root: Path, files: dict[str, bytes]) -> Path:
    for relative, data in files.items():
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return root


def _codes(exc: pytest.ExceptionInfo[StagingError]) -> set[str]:
    return {p.code for p in exc.value.problems}


def test_manifest_records_bytes_and_posix_spelling(tmp_path: Path) -> None:
    body = b"# Title\r\n\r\nCRLF stays CRLF.\r\n"
    src = _tree(tmp_path / "Publication Tëst ü", {"manuscript/01 intro.md": body, "publication.yaml": b"title: x\n"})
    result = collect(src)
    entry = {f["path"]: f for f in result.manifest()["files"]}["manuscript/01 intro.md"]
    assert entry == {"path": "manuscript/01 intro.md", "size": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    assert result.manifest_sha256() == hashlib.sha256(result.manifest_bytes()).hexdigest()


def test_manifest_is_order_independent(tmp_path: Path) -> None:
    a = collect(_tree(tmp_path / "a", {"b.md": b"1", "a.md": b"2", "z/y.md": b"3"}))
    b = collect(_tree(tmp_path / "b", {"z/y.md": b"3", "a.md": b"2", "b.md": b"1"}))
    assert a.manifest_bytes() == b.manifest_bytes()


def test_excludes_host_state(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {
        "publication.yaml": b"t", ".git/HEAD": b"x", "build/combined/x.pdf": b"%PDF", "output/y.pdf": b"%PDF",
        "manuscript/__pycache__/m.pyc": b"x", ".venv/bin/python": b"x", "env2/pyvenv.cfg": b"home=/",
        "env2/lib/x.py": b"x", ".ruff_cache/x": b"x", "reportkit.lock": b"{}", "report.pdf": b"%PDF",
    })
    result = collect(src)
    assert [f.relative for f in result.files] == ["publication.yaml"]
    assert {".git/", "build/", "output/", "manuscript/__pycache__/", ".venv/", "env2/", ".ruff_cache/", "reportkit.lock", "report.pdf"} <= set(result.excluded)


def test_nested_pdfs_are_inputs_but_root_pdfs_are_not(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"report.tex": b"x", "report.pdf": b"%PDF-old", "figures/chart.pdf": b"%PDF-fig"})
    assert sorted(f.relative for f in collect(src).files) == ["figures/chart.pdf", "report.tex"]


def test_empty_directories_are_kept(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"publication.yaml": b"t"})
    (src / "fragments").mkdir()
    assert "fragments" in collect(src).directories


@pytest.mark.skipif(os.name == "nt", reason="needs a case-sensitive filesystem")
def test_case_collision_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"Chapter.md": b"1", "chapter.md": b"2"})
    if len(list(src.iterdir())) < 2:
        pytest.skip("filesystem is case-insensitive")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_PATH_COLLISION"}


def test_unicode_normalization_collision_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"caf\u00e9.md": b"1"})
    try:
        (src / "cafe\u0301.md").write_bytes(b"2")
    except OSError:
        pytest.skip("filesystem normalizes names")
    if len(list(src.iterdir())) < 2:
        pytest.skip("filesystem normalizes names")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_PATH_COLLISION"}


def test_symlink_is_rejected_without_reading_target(tmp_path: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_bytes(b"do not stage")
    src = _tree(tmp_path / "p", {"a.md": b"1"})
    try:
        (src / "link.md").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable (enable Developer Mode on Windows)")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_SYMLINK"}


@pytest.mark.skipif(os.name != "nt", reason="junctions are Windows-only")
def test_junction_is_rejected(tmp_path: Path) -> None:
    import _winapi
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.md").write_bytes(b"secret")
    src = _tree(tmp_path / "p", {"a.md": b"1"})
    _winapi.CreateJunction(str(outside), str(src / "junction"))
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_REPARSE_POINT"}


@pytest.mark.skipif(os.name == "nt" or not hasattr(os, "mkfifo"), reason="needs mkfifo")
def test_special_file_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"a.md": b"1"})
    os.mkfifo(src / "pipe")
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_SPECIAL_FILE"}


@pytest.mark.skipif(os.name == "nt", reason="Windows cannot create these names")
@pytest.mark.parametrize("name", ["a\\b.md", "a:b.md", "trailing.md ", "ctrl\x01.md"])
def test_names_windows_cannot_represent_are_reported_not_renamed(tmp_path: Path, name: str) -> None:
    src = _tree(tmp_path / "p", {name: b"1"})
    with pytest.raises(StagingError) as exc:
        collect(src)
    assert _codes(exc) == {"RK_STAGE_PATH_NONPORTABLE"}
    assert exc.value.problems[0].path == name


def test_limits_are_enforced_before_hashing(tmp_path: Path, monkeypatch) -> None:
    src = _tree(tmp_path / "p", {"a.bin": b"x" * 10, "b.bin": b"y" * 10})
    monkeypatch.setattr(staging, "_hash", lambda path: pytest.fail("hashed despite limit failure"))
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_file_bytes=5))
    assert _codes(exc) == {"RK_STAGE_FILE_TOO_LARGE"}
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_total_bytes=15))
    assert _codes(exc) == {"RK_STAGE_TOO_LARGE"}
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_files=1))
    assert _codes(exc) == {"RK_STAGE_TOO_MANY_FILES"}


def test_all_problems_are_reported_together(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"big.bin": b"x" * 10, "ok.md": b"1"})
    try:
        (src / "link").symlink_to(src / "ok.md")
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(StagingError) as exc:
        collect(src, Limits(max_file_bytes=5))
    assert _codes(exc) == {"RK_STAGE_SYMLINK", "RK_STAGE_FILE_TOO_LARGE"}


def test_archive_layout_ownership_and_bytes(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"manuscript/ä b.md": b"x\r\n", "publication.yaml": b"t"})
    (src / "fragments").mkdir()
    result = collect(src)
    buffer = io.BytesIO()
    write_archive(result, buffer)
    buffer.seek(0)
    with tarfile.open(fileobj=buffer) as archive:
        members = {m.name: m for m in archive.getmembers()}
        assert {"source", "source/manuscript", "source/fragments", "source/manuscript/ä b.md",
                "source/publication.yaml", "input-manifest.json"} == set(members)
        assert all((m.uid, m.gid) == (10001, 10001) for m in members.values())
        assert archive.extractfile("source/manuscript/ä b.md").read() == b"x\r\n"
        assert archive.extractfile("input-manifest.json").read() == result.manifest_bytes()
    assert json.loads(result.manifest_bytes())["directories"] == ["fragments", "manuscript"]


def test_file_changed_during_archive_is_rejected(tmp_path: Path) -> None:
    src = _tree(tmp_path / "p", {"a.md": b"original"})
    result = collect(src)
    (src / "a.md").write_bytes(b"editeddd")  # same size, different bytes
    with pytest.raises(StagingError) as exc:
        write_archive(result, io.BytesIO())
    assert _codes(exc) == {"RK_STAGE_FILE_CHANGED"}


def test_missing_source_root(tmp_path: Path) -> None:
    with pytest.raises(StagingError) as exc:
        collect(tmp_path / "nope")
    assert _codes(exc) == {"RK_STAGE_SOURCE_MISSING"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest --noconftest tests/test_container_staging.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'rk_container'`.

- [ ] **Step 3: Implement `scripts/rk_container/staging.py`**

```python
"""Validate a publication directory and stream it into a build container.

Standard library only: this runs on the author's host (Windows or Linux,
Python 3.11+), never inside the toolchain image. Nothing is renamed or
re-encoded; a path that cannot be staged identically on both hosts is
reported instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
from typing import BinaryIO
import unicodedata

BUILD_UID = 10001
BUILD_GID = 10001
MANIFEST_SCHEMA = "reportkit-input-manifest/1"
EXCLUDED_ANY_DEPTH = frozenset({".git", ".hg", ".svn", ".venv", "venv", "__pycache__",
                                ".pytest_cache", ".ruff_cache", ".mypy_cache", ".cache"})
EXCLUDED_TOP_LEVEL = frozenset({"build", "output", "reportkit.lock"})
NONPORTABLE_CHARACTERS = frozenset('\\:*?"<>|')
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class Limits:
    max_total_bytes: int = 1024 * 1024 * 1024
    max_file_bytes: int = 200 * 1024 * 1024
    max_files: int = 20_000


@dataclass(frozen=True)
class Problem:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class StagingError(Exception):
    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("; ".join(f"{p.path}: {p.message}" for p in problems[:5]))
        self.problems = problems


@dataclass(frozen=True)
class StagedFile:
    relative: str
    absolute: Path
    size: int
    sha256: str


@dataclass
class Staging:
    root: Path
    files: list[StagedFile] = field(default_factory=list)
    directories: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.files)

    def manifest(self) -> dict:
        ordered = sorted(self.files, key=lambda item: item.relative.encode("utf-8"))
        return {
            "schema": MANIFEST_SCHEMA,
            "directories": sorted(self.directories, key=lambda d: d.encode("utf-8")),
            "files": [{"path": f.relative, "size": f.size, "sha256": f.sha256} for f in ordered],
        }

    def manifest_bytes(self) -> bytes:
        return (json.dumps(self.manifest(), ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")

    def manifest_sha256(self) -> str:
        return hashlib.sha256(self.manifest_bytes()).hexdigest()


def _fold(relative: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", relative).casefold())


def _excluded(parts: tuple[str, ...], is_dir: bool, path: str) -> bool:
    name = parts[-1]
    if is_dir and (name in EXCLUDED_ANY_DEPTH or os.path.isfile(os.path.join(path, "pyvenv.cfg"))):
        return True
    return len(parts) == 1 and (name in EXCLUDED_TOP_LEVEL or (not is_dir and name.lower().endswith(".pdf")))


def _name_problem(relative: str, name: str) -> Problem | None:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        return Problem("RK_STAGE_PATH_NONPORTABLE", relative, "name contains a control character")
    bad = "".join(sorted(set(name) & NONPORTABLE_CHARACTERS))
    if bad:
        return Problem("RK_STAGE_PATH_NONPORTABLE", relative, f"name contains {bad!r}, which Windows cannot represent")
    if name.endswith((" ", ".")):
        return Problem("RK_STAGE_PATH_NONPORTABLE", relative, "name ends with a space or dot, which Windows strips")
    return None


def _hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def collect(root: Path, limits: Limits = Limits()) -> Staging:
    """Validate and hash every stageable file under root, or raise with all problems."""
    root = Path(root)
    if not root.is_dir():
        raise StagingError([Problem("RK_STAGE_SOURCE_MISSING", str(root), "source root is not a directory")])
    result = Staging(root.resolve())
    problems: list[Problem] = []
    seen: dict[str, str] = {}
    candidates: list[tuple[str, Path, int]] = []
    pending: list[tuple[str, ...]] = [()]
    while pending:
        parts = pending.pop()
        with os.scandir(result.root.joinpath(*parts)) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            child = (*parts, entry.name)
            relative = "/".join(child)
            info = entry.stat(follow_symlinks=False)
            if entry.is_symlink():
                problems.append(Problem("RK_STAGE_SYMLINK", relative, "symbolic links are not staged; replace it with the real file"))
                continue
            if getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
                problems.append(Problem("RK_STAGE_REPARSE_POINT", relative, "junctions and other reparse points are not staged"))
                continue
            is_dir = stat.S_ISDIR(info.st_mode)
            if _excluded(child, is_dir, entry.path):
                result.excluded.append(relative + ("/" if is_dir else ""))
                continue
            problem = _name_problem(relative, entry.name)
            if problem:
                problems.append(problem)
                continue
            key = _fold(relative)
            if key in seen:
                problems.append(Problem("RK_STAGE_PATH_COLLISION", relative,
                                        f"collides with {seen[key]!r} under case folding or Unicode normalization"))
                continue
            seen[key] = relative
            if is_dir:
                result.directories.append(relative)
                pending.append(child)
            elif not stat.S_ISREG(info.st_mode):
                problems.append(Problem("RK_STAGE_SPECIAL_FILE", relative, "only regular files and directories can be staged"))
            elif info.st_size > limits.max_file_bytes:
                problems.append(Problem("RK_STAGE_FILE_TOO_LARGE", relative,
                                        f"{info.st_size} bytes exceeds the per-file limit of {limits.max_file_bytes}"))
            else:
                candidates.append((relative, Path(entry.path), info.st_size))
    if len(candidates) > limits.max_files:
        problems.append(Problem("RK_STAGE_TOO_MANY_FILES", ".", f"{len(candidates)} files exceeds the limit of {limits.max_files}"))
    total = sum(size for _, _, size in candidates)
    if total > limits.max_total_bytes:
        problems.append(Problem("RK_STAGE_TOO_LARGE", ".", f"{total} bytes exceeds the total limit of {limits.max_total_bytes}"))
    if problems:
        raise StagingError(problems)
    for relative, absolute, size in candidates:
        digest, actual = _hash(absolute)
        if actual != size:
            problems.append(Problem("RK_STAGE_FILE_CHANGED", relative, "file changed while it was being staged"))
        result.files.append(StagedFile(relative, absolute, actual, digest))
    if problems:
        raise StagingError(problems)
    return result


class _VerifyingReader:
    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle
        self._digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        chunk = self._handle.read(size)
        self._digest.update(chunk)
        return chunk

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def _info(name: str, kind: bytes, mode: int, size: int = 0) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type, info.mode, info.size, info.mtime = kind, mode, size, 0
    info.uid, info.gid, info.uname, info.gname = BUILD_UID, BUILD_GID, "reportkit", "reportkit"
    return info


def write_archive(staging: Staging, stream: BinaryIO) -> None:
    """Write source/ and input-manifest.json for `docker cp --archive - <id>:/work`."""
    manifest = staging.manifest()
    with tarfile.open(fileobj=stream, mode="w|", format=tarfile.PAX_FORMAT) as archive:
        archive.addfile(_info("source", tarfile.DIRTYPE, 0o755))
        for directory in manifest["directories"]:
            archive.addfile(_info(f"source/{directory}", tarfile.DIRTYPE, 0o755))
        for item in sorted(staging.files, key=lambda f: f.relative.encode("utf-8")):
            with open(item.absolute, "rb") as handle:
                reader = _VerifyingReader(handle)
                try:
                    archive.addfile(_info(f"source/{item.relative}", tarfile.REGTYPE, 0o644, item.size), reader)
                except OSError as exc:  # file shrank after hashing
                    raise StagingError([Problem("RK_STAGE_FILE_CHANGED", item.relative, f"file changed after it was hashed ({exc})")]) from None
            if reader.hexdigest() != item.sha256:
                raise StagingError([Problem("RK_STAGE_FILE_CHANGED", item.relative, "file changed after it was hashed")])
        data = staging.manifest_bytes()
        archive.addfile(_info("input-manifest.json", tarfile.REGTYPE, 0o644, len(data)), io.BytesIO(data))
```

Note: `tarfile.addfile` reads exactly `info.size` bytes and raises `OSError("unexpected end of data")` if the file shrank. The hash comparison catches edits that keep the same size.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest --noconftest tests/test_container_staging.py -q`
Expected: PASS. The Windows-only tests are skipped on Linux; the Windows host job runs them in Task 8.

- [ ] **Step 5: Commit**

```bash
git add scripts/rk_container/__init__.py scripts/rk_container/staging.py tests/test_container_staging.py
git commit -m "feat(container): validate and archive publication sources on the host"
```

---

### Task 4: Docker CLI adapter

**Files:**
- Create: `scripts/rk_container/docker.py`
- Test: `tests/test_container_docker.py`

**Interfaces:**
- Consumes: `staging.BUILD_UID` and `staging.BUILD_GID`.
- Produces (used by Tasks 6 and 8):
  - `DockerError(code: str, message: str)`. Codes: `RK_DOCKER_MISSING`, `RK_DOCKER_TIMEOUT`, `RK_DOCKER_DAEMON_UNAVAILABLE`, `RK_DOCKER_WINDOWS_CONTAINERS`, `RK_DOCKER_IMAGE_UNAVAILABLE`, `RK_DOCKER_IMAGE_PLATFORM`, `RK_DOCKER_DIGEST_MISMATCH`, `RK_DOCKER_CREATE_FAILED`, `RK_DOCKER_COPY_FAILED`.
  - `DaemonInfo(os: str, architecture: str, version: str, emulated: bool)`
  - `ImageInfo(reference: str, image_id: str, digest: str | None, os: str, architecture: str)` with `.pinned -> bool`
  - `RunLimits(cpus: str = "4", memory: str = "6g", pids: int = 1024, timeout_seconds: int = 1800)`
  - `RunOutcome(exit_code: int | None, timed_out: bool, output_tail: bytes)`
  - `Docker(executable="docker", run=subprocess.run, popen=subprocess.Popen)` with `.daemon() -> DaemonInfo`, `.image(reference, *, pull: bool) -> ImageInfo`, `.create(image, command: list[str], env: dict[str, str], limits: RunLimits) -> str`, `.copy_in(container, write: Callable[[BinaryIO], None]) -> None`, `.start(container, timeout: int) -> RunOutcome`, `.copy_out(container, path, consume: Callable[[BinaryIO], None]) -> None`, `.remove(container) -> None`
  - `PLATFORM = "linux/amd64"`

- [ ] **Step 1: Write the failing tests**

`tests/test_container_docker.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from rk_container.docker import Docker, DockerError, RunLimits  # noqa: E402

DIGEST = "sha256:" + "a" * 64
PINNED = f"ghcr.io/iancwm/report-kit@{DIGEST}"


class FakeCli:
    """Scripted `docker` responses keyed by the first argument(s)."""

    def __init__(self, responses: dict[tuple[str, ...], list[subprocess.CompletedProcess | BaseException]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        assert isinstance(argv, list) and "shell" not in kwargs
        self.calls.append(argv)
        for key, queue in self.responses.items():
            if tuple(argv[1:1 + len(key)]) == key:
                item = queue.pop(0) if len(queue) > 1 else queue[0]
                if isinstance(item, BaseException):
                    raise item
                return item
        raise AssertionError(f"unexpected docker call {argv}")


def ok(stdout: str | bytes = b"", rc: int = 0, stderr: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, stdout.encode() if isinstance(stdout, str) else stdout, stderr)


def version(os_name="linux", arch="amd64") -> subprocess.CompletedProcess:
    return ok(json.dumps({"Client": {}, "Server": {"Os": os_name, "Arch": arch, "Version": "27.0"}}))


def inspect(os_name="linux", arch="amd64", digests=(f"ghcr.io/iancwm/report-kit@{DIGEST}",)) -> subprocess.CompletedProcess:
    return ok(json.dumps({"Id": "sha256:" + "b" * 64, "Os": os_name, "Architecture": arch, "RepoDigests": list(digests)}))


def test_missing_cli() -> None:
    with pytest.raises(DockerError) as exc:
        Docker(run=FakeCli({("version",): [FileNotFoundError()]})).daemon()
    assert exc.value.code == "RK_DOCKER_MISSING"


def test_daemon_unavailable() -> None:
    cli = FakeCli({("version",): [ok(json.dumps({"Client": {}}), rc=1, stderr=b"Cannot connect to the Docker daemon")]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).daemon()
    assert exc.value.code == "RK_DOCKER_DAEMON_UNAVAILABLE"
    assert "Cannot connect" in exc.value.message


def test_windows_container_mode_is_actionable() -> None:
    with pytest.raises(DockerError) as exc:
        Docker(run=FakeCli({("version",): [version(os_name="windows")]})).daemon()
    assert exc.value.code == "RK_DOCKER_WINDOWS_CONTAINERS"
    assert "Switch to Linux containers" in exc.value.message


def test_arm_daemon_is_marked_emulated() -> None:
    info = Docker(run=FakeCli({("version",): [version(arch="arm64")]})).daemon()
    assert info.emulated is True


def test_pinned_image_is_pulled_when_absent_and_digest_verified() -> None:
    cli = FakeCli({("image", "inspect"): [ok(rc=1), inspect()], ("pull",): [ok()]})
    info = Docker(run=cli).image(PINNED, pull=True)
    assert info.digest == DIGEST and info.pinned
    assert ["docker", "pull", "--platform", "linux/amd64", PINNED] in cli.calls


def test_unavailable_image() -> None:
    cli = FakeCli({("image", "inspect"): [ok(rc=1)], ("pull",): [ok(rc=1, stderr=b"manifest unknown")]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=True)
    assert exc.value.code == "RK_DOCKER_IMAGE_UNAVAILABLE"
    assert "manifest unknown" in exc.value.message


def test_no_pull_reports_unavailable_without_pulling() -> None:
    cli = FakeCli({("image", "inspect"): [ok(rc=1)]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=False)
    assert exc.value.code == "RK_DOCKER_IMAGE_UNAVAILABLE"
    assert not any(c[1] == "pull" for c in cli.calls)


def test_wrong_architecture_image() -> None:
    cli = FakeCli({("image", "inspect"): [inspect(arch="arm64")]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=False)
    assert exc.value.code == "RK_DOCKER_IMAGE_PLATFORM"


def test_digest_mismatch() -> None:
    cli = FakeCli({("image", "inspect"): [inspect(digests=("ghcr.io/iancwm/report-kit@sha256:" + "c" * 64,))]})
    with pytest.raises(DockerError) as exc:
        Docker(run=cli).image(PINNED, pull=False)
    assert exc.value.code == "RK_DOCKER_DIGEST_MISMATCH"


def test_local_unpinned_image_has_no_digest() -> None:
    info = Docker(run=FakeCli({("image", "inspect"): [inspect(digests=())]})).image("reportkit-local", pull=False)
    assert info.digest is None and not info.pinned


def test_create_is_isolated_and_runs_the_inspected_image_id() -> None:
    cli = FakeCli({("create",): [ok("cid123\n")]})
    image = Docker(run=FakeCli({("image", "inspect"): [inspect()]})).image(PINNED, pull=False)
    cid = Docker(run=cli).create(image, ["/opt/py", "/opt/entry.py", "--kind", "pipeline"], {"B": "2", "A": "1"}, RunLimits())
    argv = cli.calls[0]
    assert cid == "cid123"
    for flag in (["--network", "none"], ["--user", "10001:10001"], ["--cap-drop", "ALL"], ["--platform", "linux/amd64"],
                 ["--security-opt", "no-new-privileges"], ["--memory", "6g"], ["--memory-swap", "6g"], ["--cpus", "4"],
                 ["--entrypoint", "/opt/py"], ["--env", "A=1"]):
        assert any(argv[i:i + 2] == flag for i in range(len(argv))), flag
    assert not any(a.startswith(("-v", "--volume", "--mount")) for a in argv)
    assert argv[-4:] == ["sha256:" + "b" * 64, "/opt/entry.py", "--kind", "pipeline"]


def test_start_timeout_kills_container() -> None:
    cli = FakeCli({("start",): [subprocess.TimeoutExpired(["docker"], 5, output=b"partial")], ("kill",): [ok()]})
    outcome = Docker(run=cli).start("cid", timeout=5)
    assert outcome.timed_out and outcome.exit_code is None
    assert ["docker", "kill", "cid"] in cli.calls


def test_start_reports_exit_code_and_bounded_tail() -> None:
    cli = FakeCli({("start",): [ok(b"x" * 200_000, rc=4)]})
    outcome = Docker(run=cli).start("cid", timeout=5)
    assert outcome.exit_code == 4 and len(outcome.output_tail) == 64 * 1024


def test_remove_never_raises() -> None:
    Docker(run=FakeCli({("rm",): [FileNotFoundError()]})).remove("cid")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest --noconftest tests/test_container_docker.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'rk_container.docker'`.

- [ ] **Step 3: Implement `scripts/rk_container/docker.py`**

```python
"""Docker CLI adapter for the ReportKit container launcher (stdlib only).

Every call is an argument list. No shell, no path interpolation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
from typing import BinaryIO, Callable

from .staging import BUILD_GID, BUILD_UID

PLATFORM = "linux/amd64"
OUTPUT_TAIL_BYTES = 64 * 1024


class DockerError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DaemonInfo:
    os: str
    architecture: str
    version: str
    emulated: bool


@dataclass(frozen=True)
class ImageInfo:
    reference: str
    image_id: str
    digest: str | None
    os: str
    architecture: str

    @property
    def pinned(self) -> bool:
        return "@sha256:" in self.reference


@dataclass(frozen=True)
class RunLimits:
    cpus: str = "4"
    memory: str = "6g"
    pids: int = 1024
    timeout_seconds: int = 1800


@dataclass(frozen=True)
class RunOutcome:
    exit_code: int | None
    timed_out: bool
    output_tail: bytes


def _last_line(data: bytes | None) -> str:
    lines = (data or b"").decode("utf-8", "replace").strip().splitlines()
    return lines[-1] if lines else "no error output"


def _repository(reference: str) -> str:
    if "@" in reference:
        return reference.split("@", 1)[0]
    head, _, tail = reference.rpartition("/")
    name = tail.split(":", 1)[0]
    return f"{head}/{name}" if head else name


class Docker:
    def __init__(self, executable: str = "docker", run: Callable = subprocess.run, popen: Callable = subprocess.Popen) -> None:
        self.executable = executable
        self._runner = run
        self._popen = popen

    def _run(self, args: list[str], *, timeout: float = 120) -> subprocess.CompletedProcess:
        try:
            return self._runner([self.executable, *args], capture_output=True, timeout=timeout)
        except FileNotFoundError:
            raise DockerError("RK_DOCKER_MISSING", "the Docker CLI was not found on PATH; install Docker Desktop (Windows) or Docker Engine (Linux)") from None
        except subprocess.TimeoutExpired:
            raise DockerError("RK_DOCKER_TIMEOUT", f"`docker {args[0]}` did not finish within {timeout:.0f} seconds") from None

    def daemon(self) -> DaemonInfo:
        proc = self._run(["version", "--format", "{{json .}}"], timeout=30)
        try:
            data = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
        except json.JSONDecodeError:
            data = {}
        server = data.get("Server") if isinstance(data, dict) else None
        if proc.returncode != 0 or not server:
            raise DockerError("RK_DOCKER_DAEMON_UNAVAILABLE",
                              f"the Docker daemon is not reachable; start Docker Desktop or the docker service and retry ({_last_line(proc.stderr)})")
        os_name, arch = server.get("Os", ""), server.get("Arch", "")
        if os_name != "linux":
            raise DockerError("RK_DOCKER_WINDOWS_CONTAINERS",
                              f"Docker is running {os_name or 'non-Linux'} containers; ReportKit needs Linux containers. "
                              "In Docker Desktop choose 'Switch to Linux containers...' and retry")
        return DaemonInfo(os_name, arch, server.get("Version", ""), emulated=arch not in ("amd64", "x86_64"))

    def _inspect(self, reference: str) -> ImageInfo | None:
        proc = self._run(["image", "inspect", "--format", "{{json .}}", reference], timeout=60)
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
        digests = [d for d in data.get("RepoDigests") or [] if "@" in d]
        wanted = reference.split("@", 1)[1] if "@" in reference else None
        if wanted:
            if not any(d.split("@", 1)[1] == wanted for d in digests):
                raise DockerError("RK_DOCKER_DIGEST_MISMATCH", f"local image for {reference} does not carry digest {wanted}")
            digest = wanted
        else:
            repo = _repository(reference)
            digest = next((d.split("@", 1)[1] for d in digests if d.split("@", 1)[0] == repo), None)
        return ImageInfo(reference, data.get("Id", ""), digest, data.get("Os", ""), data.get("Architecture", ""))

    def image(self, reference: str, *, pull: bool) -> ImageInfo:
        info = self._inspect(reference)
        if info is None and pull:
            proc = self._run(["pull", "--platform", PLATFORM, reference], timeout=3600)
            if proc.returncode != 0:
                raise DockerError("RK_DOCKER_IMAGE_UNAVAILABLE", f"could not pull {reference}: {_last_line(proc.stderr)}")
            info = self._inspect(reference)
        if info is None:
            raise DockerError("RK_DOCKER_IMAGE_UNAVAILABLE", f"image {reference} is not available locally" + ("" if pull else " and --no-pull was given"))
        if (info.os, info.architecture) != ("linux", "amd64"):
            raise DockerError("RK_DOCKER_IMAGE_PLATFORM", f"image {reference} is {info.os}/{info.architecture}; ReportKit v1 images are linux/amd64 only")
        return info

    def create(self, image: ImageInfo, command: list[str], env: dict[str, str], limits: RunLimits) -> str:
        args = ["create", "--platform", PLATFORM, "--network", "none", "--user", f"{BUILD_UID}:{BUILD_GID}",
                "--cpus", limits.cpus, "--memory", limits.memory, "--memory-swap", limits.memory,
                "--pids-limit", str(limits.pids), "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--workdir", "/work", "--entrypoint", command[0]]
        for key, value in sorted(env.items()):
            args += ["--env", f"{key}={value}"]
        args += [image.image_id or image.reference, *command[1:]]
        proc = self._run(args, timeout=120)
        if proc.returncode != 0:
            raise DockerError("RK_DOCKER_CREATE_FAILED", f"could not create the build container: {_last_line(proc.stderr)}")
        return proc.stdout.decode().strip()

    def copy_in(self, container: str, write: Callable[[BinaryIO], None]) -> None:
        try:
            proc = self._popen([self.executable, "cp", "--archive", "-", f"{container}:/work"],
                               stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except FileNotFoundError:
            raise DockerError("RK_DOCKER_MISSING", "the Docker CLI was not found on PATH") from None
        try:
            write(proc.stdin)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        stderr = proc.stderr.read()
        if proc.wait(timeout=600) != 0:
            raise DockerError("RK_DOCKER_COPY_FAILED", f"staging into the container failed: {_last_line(stderr)}")

    def start(self, container: str, timeout: int) -> RunOutcome:
        try:
            proc = self._runner([self.executable, "start", "--attach", container], capture_output=True, timeout=timeout)
        except FileNotFoundError:
            raise DockerError("RK_DOCKER_MISSING", "the Docker CLI was not found on PATH") from None
        except subprocess.TimeoutExpired as exc:
            try:
                self._run(["kill", container], timeout=60)
            except DockerError:
                pass
            return RunOutcome(None, True, ((exc.output or b"") + (exc.stderr or b""))[-OUTPUT_TAIL_BYTES:])
        return RunOutcome(proc.returncode, False, ((proc.stdout or b"") + (proc.stderr or b""))[-OUTPUT_TAIL_BYTES:])

    def copy_out(self, container: str, path: str, consume: Callable[[BinaryIO], None]) -> None:
        proc = self._popen([self.executable, "cp", f"{container}:{path}", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            consume(proc.stdout)
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        proc.stdout.close()
        stderr = proc.stderr.read()
        if proc.wait(timeout=600) != 0:
            raise DockerError("RK_DOCKER_COPY_FAILED", f"collecting {path} failed: {_last_line(stderr)}")

    def remove(self, container: str) -> None:
        try:
            self._run(["rm", "--force", "--volumes", container], timeout=120)
        except DockerError:
            pass
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest --noconftest tests/test_container_docker.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/rk_container/docker.py tests/test_container_docker.py
git commit -m "feat(container): Docker preflight and lifecycle adapter"
```

---

### Task 5: Result validation, extraction and atomic install

**Files:**
- Create: `scripts/rk_container/results.py`
- Test: `tests/test_container_results.py`

**Interfaces:**
- Consumes: `staging.NONPORTABLE_CHARACTERS`.
- Produces (used by Tasks 6 and 8):
  - `ResultError(code: str, message: str)`
  - `validate_output_root(output_root: Path, source_root: Path) -> tuple[Path, Path]` returns `(target, failure_dir)`. Codes: `RK_OUTPUT_CONTAINS_SOURCE`, `RK_OUTPUT_INSIDE_SOURCE`, `RK_OUTPUT_PARENT_MISSING`, `RK_OUTPUT_SYMLINK`, `RK_OUTPUT_NOT_DIRECTORY`, `RK_OUTPUT_NOT_MANAGED`.
  - `incoming_dir(target: Path) -> Path` creates an empty sibling directory `.<name>.incoming-XXXX`.
  - `extract_result(stream: BinaryIO, destination: Path) -> None`. Codes: `RK_RESULT_UNSAFE_MEMBER`, `RK_RESULT_DUPLICATE_MEMBER`, `RK_RESULT_TOO_LARGE`.
  - `verify_result(directory: Path) -> dict` returns the parsed `container-build.json`. Codes: `RK_RESULT_MANIFEST_MISSING`, `RK_RESULT_MISSING_FILE`, `RK_RESULT_UNLISTED_FILE`, `RK_RESULT_HASH_MISMATCH`.
  - `install(staged: Path, target: Path) -> None`. Code: `RK_OUTPUT_LOCKED`.
  - `record_failure(failure_dir: Path, collected: Path | None, launcher_record: dict) -> None` writes `launcher-failure.json` (the marker used to recognize a managed failure directory).
  - `clear_failure(failure_dir: Path) -> None`
  - `RESULT_MANIFEST = "container-build.json"`, `FAILURE_RECORD = "launcher-failure.json"`

- [ ] **Step 1: Write the failing tests**

`tests/test_container_results.py`:

```python
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from rk_container import results  # noqa: E402
from rk_container.results import ResultError, extract_result, install, validate_output_root, verify_result  # noqa: E402


def _tar(entries: list[tuple[str, bytes | None, bytes]]) -> io.BytesIO:
    """entries: (name, data or None for dir, tar type)"""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind == tarfile.SYMTYPE:
                info.linkname = "/etc/passwd"
            if data is not None:
                info.size = len(data)
            archive.addfile(info, io.BytesIO(data) if data is not None else None)
    buffer.seek(0)
    return buffer


def _good_result() -> io.BytesIO:
    pdf = b"%PDF-1.7 ok"
    manifest = {"status": "passed", "outputs": [{"path": "doc.pdf", "sha256": hashlib.sha256(pdf).hexdigest(), "bytes": len(pdf)}]}
    return _tar([("result", None, tarfile.DIRTYPE), ("result/doc.pdf", pdf, tarfile.REGTYPE),
                 ("result/container-build.json", json.dumps(manifest).encode(), tarfile.REGTYPE)])


def test_good_result_round_trip(tmp_path: Path) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    extract_result(_good_result(), dest)
    assert verify_result(dest)["status"] == "passed"


@pytest.mark.parametrize("name,kind", [
    ("result/../escape.txt", tarfile.REGTYPE), ("/result/abs.txt", tarfile.REGTYPE), ("other/x", tarfile.REGTYPE),
    ("result/a\\b", tarfile.REGTYPE), ("result/a:stream", tarfile.REGTYPE), ("result/link", tarfile.SYMTYPE),
    ("result/hard", tarfile.LNKTYPE), ("result/dev", tarfile.CHRTYPE),
])
def test_unsafe_members_are_rejected_before_writing(tmp_path: Path, name: str, kind: bytes) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    data = None if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE) else b"x"
    with pytest.raises(ResultError) as exc:
        extract_result(_tar([(name, data, kind)]), dest)
    assert exc.value.code == "RK_RESULT_UNSAFE_MEMBER"
    assert not (tmp_path / "escape.txt").exists()
    assert list(dest.rglob("*")) == []


def test_duplicate_member_is_rejected(tmp_path: Path) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    with pytest.raises(ResultError) as exc:
        extract_result(_tar([("result/a", b"1", tarfile.REGTYPE), ("result/a", b"2", tarfile.REGTYPE)]), dest)
    assert exc.value.code == "RK_RESULT_DUPLICATE_MEMBER"


def test_result_size_limit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(results, "MAX_RESULT_BYTES", 3)
    dest = tmp_path / "in"
    dest.mkdir()
    with pytest.raises(ResultError) as exc:
        extract_result(_tar([("result/a", b"1234", tarfile.REGTYPE)]), dest)
    assert exc.value.code == "RK_RESULT_TOO_LARGE"


def test_hash_mismatch_and_unlisted_files(tmp_path: Path) -> None:
    dest = tmp_path / "in"
    dest.mkdir()
    extract_result(_good_result(), dest)
    (dest / "extra.txt").write_bytes(b"x")
    with pytest.raises(ResultError) as exc:
        verify_result(dest)
    assert exc.value.code == "RK_RESULT_UNLISTED_FILE"
    (dest / "extra.txt").unlink()
    (dest / "doc.pdf").write_bytes(b"%PDF tampered")
    with pytest.raises(ResultError) as exc:
        verify_result(dest)
    assert exc.value.code == "RK_RESULT_HASH_MISMATCH"


def test_output_root_rules(tmp_path: Path) -> None:
    source = tmp_path / "project"
    (source / "manuscript").mkdir(parents=True)
    target, failure = validate_output_root(tmp_path / "out", source)
    assert target == (tmp_path / "out").resolve() and failure.name == "out.failed"
    assert validate_output_root(source / "output", source)[0] == (source / "output").resolve()
    with pytest.raises(ResultError) as exc:
        validate_output_root(source / "manuscript" / "pdf", source)
    assert exc.value.code == "RK_OUTPUT_INSIDE_SOURCE"
    with pytest.raises(ResultError) as exc:
        validate_output_root(tmp_path / "missing" / "out", source)
    assert exc.value.code == "RK_OUTPUT_PARENT_MISSING"


def test_refuses_output_root_containing_source(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    for candidate in (source, tmp_path):
        with pytest.raises(ResultError) as exc:
            validate_output_root(candidate, source)
        assert exc.value.code == "RK_OUTPUT_CONTAINS_SOURCE"


def test_refuses_unmanaged_output_root(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    documents = tmp_path / "Documents"
    documents.mkdir()
    (documents / "taxes.xlsx").write_bytes(b"precious")
    with pytest.raises(ResultError) as exc:
        validate_output_root(documents, source)
    assert exc.value.code == "RK_OUTPUT_NOT_MANAGED"
    assert (documents / "taxes.xlsx").read_bytes() == b"precious"
    (documents / "taxes.xlsx").unlink()
    validate_output_root(documents, source)  # empty is fine


def test_refuses_unmanaged_failure_dir(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    (tmp_path / "out.failed").mkdir()
    (tmp_path / "out.failed" / "notes.txt").write_bytes(b"mine")
    with pytest.raises(ResultError) as exc:
        validate_output_root(tmp_path / "out", source)
    assert exc.value.code == "RK_OUTPUT_NOT_MANAGED"


def test_install_replaces_previous_output(tmp_path: Path) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "old.pdf").write_bytes(b"old")
    staged = results.incoming_dir(target)
    (staged / "new.pdf").write_bytes(b"new")
    install(staged, target)
    assert [p.name for p in target.iterdir()] == ["new.pdf"]
    assert not staged.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["out"]


def test_install_keeps_previous_output_when_rename_is_locked(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "old.pdf").write_bytes(b"old")
    staged = results.incoming_dir(target)
    (staged / "new.pdf").write_bytes(b"new")
    real_replace = os.replace

    def locked(src, dst):
        if Path(src) == target:
            raise PermissionError(32, "The process cannot access the file because it is being used by another process")
        return real_replace(src, dst)

    monkeypatch.setattr(results.os, "replace", locked)
    with pytest.raises(ResultError) as exc:
        install(staged, target)
    assert exc.value.code == "RK_OUTPUT_LOCKED"
    assert "close" in exc.value.message
    assert (target / "old.pdf").read_bytes() == b"old"


def test_install_rolls_back_if_second_rename_fails(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "out"
    target.mkdir()
    (target / "old.pdf").write_bytes(b"old")
    staged = results.incoming_dir(target)
    real_replace = os.replace

    def fail_second(src, dst):
        if Path(src) == staged:
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr(results.os, "replace", fail_second)
    with pytest.raises(OSError):
        install(staged, target)
    assert (target / "old.pdf").read_bytes() == b"old"


def test_record_and_clear_failure(tmp_path: Path) -> None:
    failure = tmp_path / "out.failed"
    collected = tmp_path / "collected"
    (collected / "logs").mkdir(parents=True)
    (collected / "logs" / "build.log").write_text("! Undefined control sequence.")
    results.record_failure(failure, collected, {"code": "RK_CONTAINER_FAILED", "exit_code": 4})
    assert json.loads((failure / "launcher-failure.json").read_text())["exit_code"] == 4
    assert (failure / "logs" / "build.log").is_file()
    results.clear_failure(failure)
    assert not failure.exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest --noconftest tests/test_container_results.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/rk_container/results.py`**

```python
"""Validate, extract and atomically install container build results (stdlib only)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
from typing import BinaryIO

from .staging import NONPORTABLE_CHARACTERS

RESULT_PREFIX = "result"
RESULT_MANIFEST = "container-build.json"
FAILURE_RECORD = "launcher-failure.json"
MAX_RESULT_BYTES = 4 * 1024 ** 3
MAX_RESULT_FILES = 50_000
MANAGED_DIRECTORIES = ("build", "output")


class ResultError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _absolute(path: Path) -> Path:
    path = Path(path).absolute()
    return path.parent.resolve() / path.name


def _managed(directory: Path, marker: str) -> bool:
    return not directory.exists() or not any(directory.iterdir()) or (directory / marker).is_file()


def validate_output_root(output_root: Path, source_root: Path) -> tuple[Path, Path]:
    """Resolve the output and failure directories and refuse anything unsafe to replace."""
    target = _absolute(output_root)
    source = Path(source_root).resolve()
    if target == source or source.is_relative_to(target):
        raise ResultError("RK_OUTPUT_CONTAINS_SOURCE", f"output root {target} contains the source root; choose a separate directory")
    if target.is_relative_to(source) and target.relative_to(source).parts[0] not in MANAGED_DIRECTORIES:
        raise ResultError("RK_OUTPUT_INSIDE_SOURCE", "an output root inside the source must be under its build/ or output/ directory, which are never staged")
    if not target.parent.is_dir():
        raise ResultError("RK_OUTPUT_PARENT_MISSING", f"parent directory {target.parent} does not exist")
    failure = target.with_name(target.name + ".failed")
    for directory, marker in ((target, RESULT_MANIFEST), (failure, FAILURE_RECORD)):
        if directory.is_symlink():
            raise ResultError("RK_OUTPUT_SYMLINK", f"{directory} is a symbolic link; pass the real directory")
        if directory.exists() and not directory.is_dir():
            raise ResultError("RK_OUTPUT_NOT_DIRECTORY", f"{directory} exists and is not a directory")
        if not _managed(directory, marker):
            raise ResultError("RK_OUTPUT_NOT_MANAGED", f"{directory} already contains files this launcher did not write; choose an empty or new directory")
    return target, failure


def incoming_dir(target: Path) -> Path:
    return Path(tempfile.mkdtemp(prefix=f".{target.name}.incoming-", dir=target.parent))


def _member_path(name: str) -> PurePosixPath:
    unsafe = ResultError("RK_RESULT_UNSAFE_MEMBER", f"{name!r}: result archive entries must stay inside result/")
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        raise unsafe
    parts = PurePosixPath(name).parts
    if not parts or parts[0] != RESULT_PREFIX or ".." in parts:
        raise unsafe
    for part in parts[1:]:
        if set(part) & NONPORTABLE_CHARACTERS or part.endswith((" ", ".")) or any(ord(ch) < 32 for ch in part):
            raise unsafe
    return PurePosixPath(*parts[1:]) if len(parts) > 1 else PurePosixPath()


def extract_result(stream: BinaryIO, destination: Path) -> None:
    """Extract a `docker cp <id>:/work/result -` stream into an empty directory."""
    total = count = 0
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for member in archive:
            relative = _member_path(member.name)
            count += 1
            if count > MAX_RESULT_FILES:
                raise ResultError("RK_RESULT_TOO_LARGE", f"result has more than {MAX_RESULT_FILES} entries")
            if member.isdir():
                destination.joinpath(*relative.parts).mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile() or not relative.parts:
                raise ResultError("RK_RESULT_UNSAFE_MEMBER", f"{member.name!r}: only regular files and directories are accepted")
            total += member.size
            if total > MAX_RESULT_BYTES:
                raise ResultError("RK_RESULT_TOO_LARGE", f"result exceeds {MAX_RESULT_BYTES} bytes")
            path = destination.joinpath(*relative.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                handle = open(path, "xb")
            except FileExistsError:
                raise ResultError("RK_RESULT_DUPLICATE_MEMBER", f"{member.name!r} appears twice in the result archive") from None
            with handle, archive.extractfile(member) as source:
                shutil.copyfileobj(source, handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_result(directory: Path) -> dict:
    manifest_path = directory / RESULT_MANIFEST
    if not manifest_path.is_file():
        raise ResultError("RK_RESULT_MANIFEST_MISSING", f"the container did not return {RESULT_MANIFEST}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = {_member_path(f"{RESULT_PREFIX}/{item['path']}").as_posix(): item for item in manifest.get("outputs", [])}
    present = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()} - {RESULT_MANIFEST}
    if missing := sorted(set(listed) - present):
        raise ResultError("RK_RESULT_MISSING_FILE", f"result is missing {missing[:5]}")
    if extra := sorted(present - set(listed)):
        raise ResultError("RK_RESULT_UNLISTED_FILE", f"result contains files not in {RESULT_MANIFEST}: {extra[:5]}")
    for relative, item in listed.items():
        if _sha256(directory / relative) != item["sha256"]:
            raise ResultError("RK_RESULT_HASH_MISMATCH", f"{relative} does not match its recorded SHA-256")
    return manifest


def install(staged: Path, target: Path) -> None:
    """Swap staged into target. The previous target survives any failure."""
    backup = None
    if target.exists():
        backup = target.with_name(f".{target.name}.previous-{os.getpid()}")
        if backup.exists():
            shutil.rmtree(backup)
        try:
            os.replace(target, backup)
        except PermissionError:
            shutil.rmtree(staged, ignore_errors=True)
            raise ResultError("RK_OUTPUT_LOCKED", f"could not replace {target}; close any program holding files there (for example a PDF viewer) and retry") from None
    try:
        os.replace(staged, target)
    except OSError:
        if backup is not None:
            os.replace(backup, target)
        shutil.rmtree(staged, ignore_errors=True)
        raise
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)


def record_failure(failure_dir: Path, collected: Path | None, launcher_record: dict) -> None:
    staged = incoming_dir(failure_dir)
    if collected is not None and collected.is_dir():
        shutil.copytree(collected, staged, dirs_exist_ok=True)
        shutil.rmtree(collected, ignore_errors=True)
    (staged / FAILURE_RECORD).write_text(json.dumps(launcher_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    install(staged, failure_dir)


def clear_failure(failure_dir: Path) -> None:
    if failure_dir.is_dir() and (failure_dir / FAILURE_RECORD).is_file():
        shutil.rmtree(failure_dir)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest --noconftest tests/test_container_results.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/rk_container/results.py tests/test_container_results.py
git commit -m "feat(container): verified result extraction and atomic output swap"
```

---

### Task 6: Host launcher CLI (`scripts/reportkit_container.py`)

**Files:**
- Create: `scripts/reportkit_container.py` (mode 100755)
- Test: `tests/test_container_launcher.py`

**Interfaces:**
- Consumes: everything from Tasks 3–5, and the entrypoint argument contract from Task 7 (`--kind`, `--entry`, `--engine`, `--profile`, `--pages`, `--dpi`). The entrypoint returns `container-build.json` with `status`, `outputs`, `pdf`, `selection` and `input_manifest_sha256`.
- Produces:
  - CLI `build --image REF --source-root DIR --output-root DIR --kind {pipeline,direct-tex} [--entry REL] [--engine {lualatex,pdflatex}] [--profile NAME] [--pages SEL] [--dpi N] [--allow-unpinned-image] [--no-pull] [--timeout-seconds N] [--cpus N] [--memory SIZE] [--max-input-mb N] [--max-file-mb N] [--max-files N] [--json]`
  - CLI `summarize OUTPUT_ROOT` prints the summary JSON.
  - `run_build(args: argparse.Namespace, docker: Docker | None = None) -> tuple[int, dict]`
  - `summarize(output_root: Path) -> dict` with the keys `image_digest`, `release_eligible`, `input_manifest_sha256`, `selection` (`publication_type`, `theme`, `engine`, `paper`), `page_count`, `inspect_passed`, `pdf_sha256`.
  - `ENTRYPOINT = ["/opt/reportkit/.venv/bin/python", "/opt/reportkit/toolchain/container_build.py"]`

- [ ] **Step 1: Write the failing tests**

`tests/test_container_launcher.py`. The fake Docker implements the adapter interface in memory and acts as the "container". It unpacks the staged tar and returns a result tar that the test scenario writes.

```python
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import reportkit_container as launcher  # noqa: E402
from rk_container.docker import DaemonInfo, DockerError, ImageInfo, RunOutcome  # noqa: E402

DIGEST = "sha256:" + "d" * 64
IMAGE = f"ghcr.io/iancwm/report-kit@{DIGEST}"


def result_tar(files: dict[str, bytes], status: str = "passed", **extra) -> bytes:
    outputs = [{"path": p, "sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)} for p, d in files.items()]
    manifest = {"schema": "reportkit-container-build/1", "status": status, "outputs": outputs, **extra}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in {**files, "container-build.json": json.dumps(manifest).encode()}.items():
            info = tarfile.TarInfo(f"result/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeDocker:
    def __init__(self, exit_code=0, result=None, timed_out=False, daemon_error=None, interrupt_on_start=False):
        self.exit_code, self.result, self.timed_out = exit_code, result, timed_out
        self.daemon_error, self.interrupt_on_start = daemon_error, interrupt_on_start
        self.created = self.removed = 0
        self.staged: dict[str, bytes] = {}
        self.command: list[str] = []
        self.env: dict[str, str] = {}

    def daemon(self):
        if self.daemon_error:
            raise self.daemon_error
        return DaemonInfo("linux", "amd64", "27", False)

    def image(self, reference, *, pull):
        return ImageInfo(reference, "sha256:" + "e" * 64, DIGEST if "@" in reference else None, "linux", "amd64")

    def create(self, image, command, env, limits):
        self.created += 1
        self.command, self.env = command, env
        return "cid"

    def copy_in(self, container, write):
        buffer = io.BytesIO()
        write(buffer)
        buffer.seek(0)
        with tarfile.open(fileobj=buffer) as archive:
            self.staged = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}

    def start(self, container, timeout):
        if self.interrupt_on_start:
            raise KeyboardInterrupt
        return RunOutcome(None if self.timed_out else self.exit_code, self.timed_out, b"tail of output")

    def copy_out(self, container, path, consume):
        if self.result is None:
            raise DockerError("RK_DOCKER_COPY_FAILED", "no result")
        consume(io.BytesIO(self.result))

    def remove(self, container):
        self.removed += 1


def project(tmp_path: Path) -> Path:
    src = tmp_path / "Publication Tëst ü"
    (src / "manuscript").mkdir(parents=True)
    (src / "manuscript" / "01.md").write_bytes(b"# One\r\n")
    (src / "publication.yaml").write_bytes(b"title: T\n")
    return src


def args(src: Path, out: Path, *extra: str):
    return launcher.build_parser().parse_args(["build", "--image", IMAGE, "--source-root", str(src), "--output-root", str(out), "--kind", "pipeline", *extra])


def good_result() -> bytes:
    return result_tar({"doc.pdf": b"%PDF new", "build-report.json": b"{}"},
                      pdf={"path": "doc.pdf", "sha256": hashlib.sha256(b"%PDF new").hexdigest(), "pages": 3},
                      selection={"publication_type": "report", "theme": "default", "engine": "pdflatex", "paper": "a4"},
                      input_manifest_sha256="x", image={"reference": IMAGE, "digest": DIGEST}, inspect_passed=True)


def test_success_installs_verified_output(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    fake = FakeDocker(result=good_result())
    code, record = launcher.run_build(args(src, out), fake)
    assert code == 0 and record["passed"]
    assert (out / "doc.pdf").read_bytes() == b"%PDF new"
    assert fake.removed == 1
    assert fake.staged["source/manuscript/01.md"] == b"# One\r\n"
    assert fake.command[:2] == launcher.ENTRYPOINT and fake.command[2:4] == ["--kind", "pipeline"]
    assert fake.env["REPORTKIT_IMAGE_DIGEST"] == DIGEST
    assert not out.with_name("out.failed").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Publication Tëst ü", "out"]


def test_failure_keeps_prior_output_and_writes_failure_dir(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    launcher.run_build(args(src, out), FakeDocker(result=good_result()))
    before = (out / "doc.pdf").read_bytes()
    failed = result_tar({"logs/build.log": b"! Undefined control sequence."}, status="failed", failed_step="build")
    code, record = launcher.run_build(args(src, out), FakeDocker(exit_code=4, result=failed))
    assert code == 4 and not record["passed"]
    assert (out / "doc.pdf").read_bytes() == before
    failure = out.with_name("out.failed")
    assert (failure / "logs" / "build.log").is_file()
    assert json.loads((failure / "launcher-failure.json").read_text())["exit_code"] == 4


def test_timeout_kills_and_removes_container(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    fake = FakeDocker(timed_out=True, result=None)
    code, record = launcher.run_build(args(src, out, "--timeout-seconds", "5"), fake)
    assert code == 4 and record["code"] == "RK_CONTAINER_TIMEOUT"
    assert fake.removed == 1 and not out.exists()
    assert json.loads((out.with_name("out.failed") / "launcher-failure.json").read_text())["timed_out"] is True


def test_keyboard_interrupt_still_removes_container(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    fake = FakeDocker(interrupt_on_start=True)
    with pytest.raises(KeyboardInterrupt):
        launcher.run_build(args(src, out), fake)
    assert fake.removed == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Publication Tëst ü"]


def test_preflight_failure_happens_before_staging(tmp_path: Path, monkeypatch) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    monkeypatch.setattr(launcher.staging, "collect", lambda *a, **k: pytest.fail("staged before preflight"))
    fake = FakeDocker(daemon_error=DockerError("RK_DOCKER_WINDOWS_CONTAINERS", "switch"))
    code, record = launcher.run_build(args(src, out), fake)
    assert code == 5 and record["code"] == "RK_DOCKER_WINDOWS_CONTAINERS"


def test_staging_problems_stop_before_container_creation(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    (src / "big.bin").write_bytes(b"x" * 2 * 1024 * 1024)
    fake = FakeDocker(result=good_result())
    code, record = launcher.run_build(args(src, out, "--max-file-mb", "1"), fake)
    assert code == 2 and fake.created == 0
    assert record["problems"][0]["code"] == "RK_STAGE_FILE_TOO_LARGE"


def test_unpinned_image_requires_opt_in(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    parsed = launcher.build_parser().parse_args(["build", "--image", "reportkit-local", "--source-root", str(src), "--output-root", str(out), "--kind", "pipeline"])
    code, record = launcher.run_build(parsed, FakeDocker())
    assert code == 2 and record["code"] == "RK_IMAGE_NOT_PINNED"
    parsed.allow_unpinned_image = True
    code, record = launcher.run_build(parsed, FakeDocker(result=good_result()))
    assert code == 0 and record["release_eligible"] is False


def test_direct_tex_requires_existing_entry(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    base = ["build", "--image", IMAGE, "--source-root", str(src), "--output-root", str(out), "--kind", "direct-tex"]
    code, record = launcher.run_build(launcher.build_parser().parse_args(base), FakeDocker())
    assert code == 2 and record["code"] == "RK_ARGS_ENTRY_REQUIRED"
    code, record = launcher.run_build(launcher.build_parser().parse_args([*base, "--entry", "report.tex"]), FakeDocker())
    assert code == 2 and record["code"] == "RK_ARGS_ENTRY_MISSING"


def test_tampered_result_is_not_installed(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    bad = bytearray(good_result())
    bad[bad.index(b"%PDF new")] = ord("X")
    code, record = launcher.run_build(args(src, out), FakeDocker(result=bytes(bad)))
    assert code == 3 and record["code"] == "RK_RESULT_HASH_MISMATCH" and not out.exists()


def test_summarize(tmp_path: Path) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    launcher.run_build(args(src, out), FakeDocker(result=good_result()))
    summary = launcher.summarize(out)
    assert summary["page_count"] == 3 and summary["selection"]["paper"] == "a4" and summary["image_digest"] == DIGEST


def test_main_json_output(tmp_path: Path, capsys, monkeypatch) -> None:
    src, out = project(tmp_path), tmp_path / "out"
    monkeypatch.setattr(launcher, "_docker", lambda: FakeDocker(result=good_result()))
    assert launcher.main(["build", "--image", IMAGE, "--source-root", str(src), "--output-root", str(out), "--kind", "pipeline", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest --noconftest tests/test_container_launcher.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'reportkit_container'`.

- [ ] **Step 3: Implement `scripts/reportkit_container.py`**

```python
#!/usr/bin/env python3
"""Build a ReportKit publication inside the pinned toolchain container.

Host requirements: Python 3.11+ and the Docker CLI talking to a Linux-container
daemon. Arguments are identical on every host:

    python3 scripts/reportkit_container.py build --image ghcr.io/iancwm/report-kit@sha256:<digest> \\
        --kind pipeline --source-root <publication> --output-root <publication>/output
    py -3 scripts\\reportkit_container.py build ...   (Windows)

The publication is streamed into the container (never bind-mounted), built
without network, and the verified result replaces the output directory only
on success.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rk_container import results, staging  # noqa: E402
from rk_container.docker import Docker, DockerError, RunLimits  # noqa: E402

EXIT_OK, EXIT_CONFIG, EXIT_VALIDATION, EXIT_COMPILE, EXIT_ENVIRONMENT, EXIT_INTERNAL = 0, 2, 3, 4, 5, 70
ENTRYPOINT = ["/opt/reportkit/.venv/bin/python", "/opt/reportkit/toolchain/container_build.py"]
MIB = 1024 * 1024


class LauncherError(Exception):
    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code, self.message, self.exit_code = code, message, exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reportkit_container.py", description="Build a ReportKit publication inside the pinned toolchain image")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="stage, build, verify and install one publication")
    build.add_argument("--image", required=True, help="toolchain image, normally ghcr.io/iancwm/report-kit@sha256:<digest>")
    build.add_argument("--source-root", required=True)
    build.add_argument("--output-root", required=True)
    build.add_argument("--kind", required=True, choices=("pipeline", "direct-tex"), help="Markdown pipeline from publication.yaml, or one hand-authored .tex entry")
    build.add_argument("--entry", help="direct-tex only: entry .tex path relative to the source root")
    build.add_argument("--engine", choices=("lualatex", "pdflatex"), default="lualatex", help="direct-tex only")
    build.add_argument("--profile", help="pipeline only: publication.yaml profile, for example release")
    build.add_argument("--pages", help="page selection to render, e.g. '1,3-5' (default: every page)")
    build.add_argument("--dpi", type=int, default=110)
    build.add_argument("--allow-unpinned-image", action="store_true", help="development only: accept an image without @sha256 digest")
    build.add_argument("--no-pull", action="store_true")
    build.add_argument("--timeout-seconds", type=int, default=RunLimits.timeout_seconds)
    build.add_argument("--cpus", default=RunLimits.cpus)
    build.add_argument("--memory", default=RunLimits.memory)
    build.add_argument("--max-input-mb", type=int, default=staging.Limits.max_total_bytes // MIB)
    build.add_argument("--max-file-mb", type=int, default=staging.Limits.max_file_bytes // MIB)
    build.add_argument("--max-files", type=int, default=staging.Limits.max_files)
    build.add_argument("--json", action="store_true")
    summary = sub.add_parser("summarize", help="print the cross-host comparison summary of an output directory")
    summary.add_argument("output_root")
    return parser


def _docker() -> Docker:
    return Docker()


def container_command(args: argparse.Namespace) -> list[str]:
    command = [*ENTRYPOINT, "--kind", args.kind, "--dpi", str(args.dpi)]
    if args.kind == "direct-tex":
        command += ["--entry", args.entry, "--engine", args.engine]
    if args.profile:
        command += ["--profile", args.profile]
    if args.pages:
        command += ["--pages", args.pages]
    return command


def _check_arguments(args: argparse.Namespace) -> None:
    if args.kind == "direct-tex" and not args.entry:
        raise LauncherError("RK_ARGS_ENTRY_REQUIRED", "--kind direct-tex needs --entry <file.tex>", EXIT_CONFIG)
    if args.kind == "pipeline" and args.entry:
        raise LauncherError("RK_ARGS_ENTRY_UNEXPECTED", "--entry applies only to --kind direct-tex", EXIT_CONFIG)
    if args.kind == "direct-tex" and args.profile:
        raise LauncherError("RK_ARGS_PROFILE_UNEXPECTED", "--profile applies only to --kind pipeline", EXIT_CONFIG)
    if "@sha256:" not in args.image and not args.allow_unpinned_image:
        raise LauncherError("RK_IMAGE_NOT_PINNED", "pass the image by digest (ghcr.io/iancwm/report-kit@sha256:...), "
                            "or --allow-unpinned-image for a development build", EXIT_CONFIG)
    if not Path(args.source_root).is_dir():
        raise LauncherError("RK_SOURCE_MISSING", f"source root {args.source_root} is not a directory", EXIT_CONFIG)


def run_build(args: argparse.Namespace, docker: Docker | None = None) -> tuple[int, dict]:
    record: dict = {"passed": False, "image": args.image}
    try:
        _check_arguments(args)
        output, failure = results.validate_output_root(Path(args.output_root), Path(args.source_root))
        record.update(output_root=str(output), failure_root=str(failure))
        docker = docker or _docker()
        daemon = docker.daemon()
        if daemon.emulated:
            print(f"WARN: Docker daemon is {daemon.architecture}; running linux/amd64 under emulation (not a supported acceptance platform)", file=sys.stderr)
        image = docker.image(args.image, pull=not args.no_pull)
        record.update(image_digest=image.digest, release_eligible=image.pinned and image.digest is not None)
        limits = staging.Limits(args.max_input_mb * MIB, args.max_file_mb * MIB, args.max_files)
        staged = staging.collect(Path(args.source_root), limits)
        if args.kind == "direct-tex" and args.entry.replace("\\", "/") not in {f.relative for f in staged.files}:
            raise LauncherError("RK_ARGS_ENTRY_MISSING", f"entry {args.entry} is not a staged file under the source root", EXIT_CONFIG)
        if args.entry:
            args.entry = args.entry.replace("\\", "/")
        record["input_manifest_sha256"] = staged.manifest_sha256()
    except LauncherError as exc:
        return exc.exit_code, {**record, "code": exc.code, "message": exc.message}
    except results.ResultError as exc:
        return EXIT_CONFIG, {**record, "code": exc.code, "message": exc.message}
    except DockerError as exc:
        return EXIT_ENVIRONMENT, {**record, "code": exc.code, "message": exc.message}
    except staging.StagingError as exc:
        return EXIT_CONFIG, {**record, "code": exc.problems[0].code, "message": str(exc), "problems": [p.as_dict() for p in exc.problems]}

    env = {"REPORTKIT_IMAGE_REF": args.image, "REPORTKIT_IMAGE_DIGEST": image.digest or "",
           "REPORTKIT_IMAGE_ID": image.image_id, "REPORTKIT_RELEASE_ELIGIBLE": "1" if record["release_eligible"] else "0",
           "HOME": "/work/home"}
    run_limits = RunLimits(cpus=str(args.cpus), memory=args.memory, timeout_seconds=args.timeout_seconds)
    container = incoming = None
    try:
        container = docker.create(image, container_command(args), env, run_limits)
        docker.copy_in(container, lambda stream: staging.write_archive(staged, stream))
        outcome = docker.start(container, args.timeout_seconds)
        incoming = results.incoming_dir(output)
        collect_error = None
        try:
            docker.copy_out(container, "/work/result", lambda stream: results.extract_result(stream, incoming))
        except (DockerError, results.ResultError) as exc:
            collect_error = exc
        if outcome.exit_code == 0 and not outcome.timed_out:
            if collect_error:
                raise collect_error
            manifest = results.verify_result(incoming)
            if manifest.get("status") != "passed":
                raise results.ResultError("RK_RESULT_STATUS", f"container exited 0 but reported status {manifest.get('status')!r}")
            results.install(incoming, output)
            incoming = None
            results.clear_failure(failure)
            return EXIT_OK, {**record, "passed": True, "container_build": manifest}
        code = "RK_CONTAINER_TIMEOUT" if outcome.timed_out else "RK_CONTAINER_FAILED"
        exit_code = EXIT_COMPILE if outcome.timed_out or outcome.exit_code not in (2, 3, 4, 5) else outcome.exit_code
        failure_record = {"code": code, "exit_code": outcome.exit_code, "timed_out": outcome.timed_out,
                          "collect_error": getattr(collect_error, "message", None),
                          "output_tail": outcome.output_tail.decode("utf-8", "replace")}
        results.record_failure(failure, None if collect_error else incoming, failure_record)
        incoming = None
        message = f"build failed (exit {outcome.exit_code}); diagnostics in {failure}" if not outcome.timed_out else \
            f"build exceeded {args.timeout_seconds} s and was stopped; diagnostics in {failure}"
        return exit_code, {**record, "code": code, "message": message}
    except results.ResultError as exc:
        return EXIT_VALIDATION, {**record, "code": exc.code, "message": exc.message}
    except DockerError as exc:
        return EXIT_ENVIRONMENT, {**record, "code": exc.code, "message": exc.message}
    except staging.StagingError as exc:
        return EXIT_CONFIG, {**record, "code": exc.problems[0].code, "message": str(exc), "problems": [p.as_dict() for p in exc.problems]}
    finally:
        if container:
            docker.remove(container)
        if incoming is not None:
            shutil.rmtree(incoming, ignore_errors=True)


def summarize(output_root: Path) -> dict:
    manifest = json.loads((Path(output_root) / results.RESULT_MANIFEST).read_text(encoding="utf-8"))
    selection = manifest.get("selection", {})
    return {
        "image_digest": manifest.get("image", {}).get("digest"),
        "release_eligible": manifest.get("release_eligible"),
        "input_manifest_sha256": manifest.get("input_manifest_sha256"),
        "selection": {key: selection.get(key) for key in ("publication_type", "theme", "engine", "paper")},
        "page_count": manifest.get("pdf", {}).get("pages"),
        "inspect_passed": manifest.get("inspect_passed"),
        "pdf_sha256": manifest.get("pdf", {}).get("sha256"),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "summarize":
        print(json.dumps(summarize(Path(args.output_root)), indent=2, sort_keys=True))
        return EXIT_OK
    try:
        code, record = run_build(args, _docker())
    except KeyboardInterrupt:
        print("interrupted; the build container was removed", file=sys.stderr)
        return 130
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False))
    elif code == EXIT_OK:
        print(f"PASS: {record['output_root']} (image {record.get('image_digest') or 'unpinned'})")
        print("  Review every rendered page under render/ before release; a passing build is not an editorial sign-off.")
    else:
        print(f"FAIL [{record.get('code')}]: {record.get('message')}", file=sys.stderr)
        for problem in record.get("problems", [])[:50]:
            print(f"- {problem['path']} [{problem['code']}]: {problem['message']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
```

Note on `release_eligible`: the entrypoint (Task 7) copies `REPORTKIT_RELEASE_ELIGIBLE` into `container-build.json`, so the recorded value comes from the launcher's pinned-digest check.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest --noconftest tests/test_container_launcher.py tests/test_container_staging.py tests/test_container_docker.py tests/test_container_results.py -q`
Expected: PASS.

- [ ] **Step 5: Mark the script executable and commit**

```bash
chmod +x scripts/reportkit_container.py
git add scripts/reportkit_container.py tests/test_container_launcher.py tests/test_repository_hygiene.py
git update-index --chmod=+x scripts/reportkit_container.py
git commit -m "feat(container): host launcher for digest-pinned publication builds"
```

Add `scripts/reportkit_container.py` to the `required` set in `tests/test_repository_hygiene.py::test_scripts_keep_executable_mode` in the same commit.

---

### Task 7: In-image entrypoint (`toolchain/container_build.py`)

**Files:**
- Create: `toolchain/container_build.py` (mode 100755)
- Test: `tests/test_container_entrypoint.py`

**Interfaces:**
- Consumes: the existing CLI (`reportkit check|build|audit-editorial|diagnose|render|inspect --json`), `publication_build.write_lock`, `reportkit.toolchain.toolchain_context`/`version_line`, `reportkit.version`. Env from the launcher: `REPORTKIT_IMAGE_REF`, `REPORTKIT_IMAGE_DIGEST`, `REPORTKIT_IMAGE_ID`, `REPORTKIT_RELEASE_ELIGIBLE`. Image env: `REPORTKIT_COMMIT`.
- Produces:
  - CLI `container_build.py --kind {pipeline,direct-tex} [--entry REL] [--engine lualatex|pdflatex] [--profile NAME] [--pages SEL] [--dpi N] [--compile-timeout-seconds N] [--work-root /work]`. The exit code is the failing step's code, or `3` for an input mismatch, or `70` for an internal error.
  - `/work/result/` layout: `<pdf>`, `build-report.json`, `reportkit.lock`, `inspection.json`, `render/pages.json` plus PNGs, `logs/<step>.log` (each tail-bounded to 256 KiB), and `container-build.json`.
  - `container-build.json` keys: `schema` = `"reportkit-container-build/1"`, `status` (`passed`/`failed`), `failed_step`, `kind`, `image` {`reference`, `digest`, `id`}, `release_eligible`, `reportkit` {`version`, `contract_version`, `commit`}, `input_manifest_sha256`, `selection` {`publication_type`, `theme`, `engine`, `paper`}, `steps` [{`name`, `exit_code`, `seconds`, `log`}], `diagnostics` [{`step`, `code`, `severity`, `message`}], `inspect_passed`, `pdf` {`path`, `sha256`, `pages`, `width_mm`, `height_mm`}, `outputs` [{`path`, `sha256`, `bytes`}].

- [ ] **Step 1: Write the failing tests**

`tests/test_container_entrypoint.py`:

```python
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("container_build", REPO / "toolchain" / "container_build.py")
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

MEASURE = lambda pdf: {"pages": 7, "width_mm": 210, "height_mm": 297, "paper": "a4"}  # noqa: E731


def stage(work: Path, files: dict[str, bytes]) -> None:
    source = work / "source"
    entries = []
    for rel, data in files.items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        entries.append({"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (work / "input-manifest.json").write_text(json.dumps({"schema": "reportkit-input-manifest/1", "directories": [], "files": entries}))
    (work / "build").mkdir()
    (work / "result").mkdir()


class FakeTools:
    """Plays the reportkit CLI and TeX. fail maps a step name to an exit code."""

    def __init__(self, fail: dict[str, int] | None = None) -> None:
        self.fail = fail or {}
        self.calls: list[tuple[str, list[str], dict]] = []

    def __call__(self, argv, cwd, env, timeout):
        name = argv[2] if len(argv) > 2 and argv[1].endswith("reportkit") else Path(argv[0]).name
        self.calls.append((name, argv, env))
        code = self.fail.get(name, 0)
        payload = {"passed": code == 0, "diagnostics": [] if code == 0 else [{"code": f"RK_FAKE_{name.upper()}", "severity": "error", "message": f"{name} failed"}]}
        if name == "build" and code == 0:
            out = Path(argv[argv.index("--output-root") + 1]) / "combined"
            out.mkdir(parents=True)
            (out / "doc.pdf").write_bytes(b"%PDF pipeline")
            (out / "build-report.json").write_text(json.dumps({"pdf": "doc.pdf", "selection": {"publication_type": "report", "theme": "default", "engine": "pdflatex", "paper": None}}))
            (Path(argv[argv.index("--source-root") + 1]) / "reportkit.lock").write_text("{}")
        if name in ("lualatex", "pdflatex") and code == 0:
            stem = Path(argv[-1]).stem
            (Path(cwd) / f"{stem}.pdf").write_bytes(b"%PDF direct")
            (Path(cwd) / f"{stem}.log").write_text("clean log")
        if name == "render" and code == 0:
            out = Path(argv[argv.index("--out") + 1])
            out.mkdir(parents=True)
            (out / "pages.json").write_text("{}")
            (out / "page-001.png").write_bytes(b"png")
        return subprocess.CompletedProcess(argv, code, json.dumps(payload).encode(), b"stderr text")


def run(work: Path, tools: FakeTools, *argv: str, lock=lambda path, engine: path.write_text("{}")) -> int:
    return cb.main(["--work-root", str(work), *argv], runner=tools, measure=MEASURE, write_lock=lock,
                   environ={"REPORTKIT_IMAGE_REF": "img@sha256:" + "a" * 64, "REPORTKIT_IMAGE_DIGEST": "sha256:" + "a" * 64,
                            "REPORTKIT_COMMIT": "c" * 40, "REPORTKIT_RELEASE_ELIGIBLE": "1"})


def manifest(work: Path) -> dict:
    return json.loads((work / "result" / "container-build.json").read_text())


def test_pipeline_success_writes_complete_result(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n", "manuscript/01.md": b"# A\r\n"})
    tools = FakeTools()
    assert run(tmp_path, tools, "--kind", "pipeline") == 0
    data = manifest(tmp_path)
    assert data["status"] == "passed" and data["kind"] == "pipeline"
    assert [s["name"] for s in data["steps"]] == ["verify-inputs", "check", "build", "render", "inspect"]
    assert data["selection"] == {"publication_type": "report", "theme": "default", "engine": "pdflatex", "paper": "a4"}
    assert data["pdf"]["pages"] == 7 and data["pdf"]["sha256"] == hashlib.sha256(b"%PDF pipeline").hexdigest()
    assert data["reportkit"]["commit"] == "c" * 40 and data["image"]["digest"] == "sha256:" + "a" * 64
    assert data["input_manifest_sha256"] == hashlib.sha256((tmp_path / "input-manifest.json").read_bytes()).hexdigest()
    result = tmp_path / "result"
    listed = {o["path"] for o in data["outputs"]}
    assert {"doc.pdf", "build-report.json", "reportkit.lock", "inspection.json", "render/pages.json", "render/page-001.png"} <= listed
    assert listed == {p.relative_to(result).as_posix() for p in result.rglob("*") if p.is_file()} - {"container-build.json"}


def test_source_is_never_written(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    run(tmp_path, FakeTools(), "--kind", "pipeline")
    assert sorted(p.name for p in (tmp_path / "source").iterdir()) == ["publication.yaml"]


def test_every_step_runs_without_shell_escape_and_offline_python(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"\\documentclass[theme=editorial,publication-type=feature-article]{reportkit}"})
    tools = FakeTools()
    assert run(tmp_path, tools, "--kind", "direct-tex", "--entry", "report.tex") == 0
    compiles = [argv for name, argv, _ in tools.calls if name == "lualatex"]
    assert len(compiles) == 2 and all("-no-shell-escape" in argv for argv in compiles)
    env = next(env for name, _, env in tools.calls if name == "lualatex")
    assert env["shell_escape"] == "f" and env["openout_any"] == "p" and "latex_templates" in env["TEXINPUTS"]
    data = manifest(tmp_path)
    assert data["selection"] == {"publication_type": "feature-article", "theme": "editorial", "engine": "lualatex", "paper": "a4"}
    assert [s["name"] for s in data["steps"]] == ["verify-inputs", "compile-1", "compile-2", "diagnose", "render", "inspect"]


def test_editorial_brief_triggers_audit_first(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"\\documentclass{reportkit}", "editorial-brief.json": b"{}"})
    tools = FakeTools(fail={"audit-editorial": 3})
    assert run(tmp_path, tools, "--kind", "direct-tex", "--entry", "report.tex") == 3
    data = manifest(tmp_path)
    assert data["status"] == "failed" and data["failed_step"] == "audit-editorial"
    assert not any(name == "lualatex" for name, _, _ in tools.calls)
    assert data["diagnostics"][0]["code"] == "RK_FAKE_AUDIT-EDITORIAL"
    assert {o["path"] for o in data["outputs"]} == {"logs/verify-inputs.log", "logs/audit-editorial.log"}


@pytest.mark.parametrize("step,code", [("check", 3), ("build", 4), ("render", 5), ("inspect", 3)])
def test_pipeline_failure_stops_and_withholds_pdf(tmp_path: Path, step: str, code: int) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    assert run(tmp_path, FakeTools(fail={step: code}), "--kind", "pipeline") == code
    data = manifest(tmp_path)
    assert data["failed_step"] == step and data["status"] == "failed"
    assert not any(o["path"].endswith(".pdf") for o in data["outputs"])


def test_diagnostic_gate_failure_on_direct_tex(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"\\documentclass{reportkit}"})
    assert run(tmp_path, FakeTools(fail={"diagnose": 3}), "--kind", "direct-tex", "--entry", "report.tex") == 3
    assert manifest(tmp_path)["failed_step"] == "diagnose"


def test_input_mismatch_is_rejected_before_any_tool(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    (tmp_path / "source" / "publication.yaml").write_bytes(b"title: tampered\n")
    tools = FakeTools()
    assert run(tmp_path, tools, "--kind", "pipeline") == 3
    assert tools.calls == [] and manifest(tmp_path)["failed_step"] == "verify-inputs"


def test_unexpected_extra_source_file_is_rejected(tmp_path: Path) -> None:
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    (tmp_path / "source" / "stowaway.tex").write_bytes(b"x")
    assert run(tmp_path, FakeTools(), "--kind", "pipeline") == 3


def test_logs_are_tail_bounded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cb, "MAX_LOG_BYTES", 100)
    stage(tmp_path, {"publication.yaml": b"title: T\n"})
    run(tmp_path, FakeTools(), "--kind", "pipeline")
    assert (tmp_path / "result" / "logs" / "build.log").stat().st_size <= 100


def test_direct_tex_entry_must_stay_inside_source(tmp_path: Path) -> None:
    stage(tmp_path, {"report.tex": b"x"})
    assert run(tmp_path, FakeTools(), "--kind", "direct-tex", "--entry", "../etc/passwd.tex") == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_container_entrypoint.py -q`
Expected: FAIL with `FileNotFoundError` for `toolchain/container_build.py`.

- [ ] **Step 3: Implement `toolchain/container_build.py`**

```python
#!/usr/bin/env python3
"""Container-side ReportKit publication build.

Runs inside the toolchain image, started by scripts/reportkit_container.py:
  /work/input-manifest.json  staged by the launcher (verified first)
  /work/source               staged publication (never written)
  /work/build                scratch: a working copy plus all TeX output
  /work/result               returned to the host; listed in container-build.json

It only sequences existing ReportKit commands. Document logic stays in the
CLI and publication_pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python_scripts"))
sys.path.insert(0, str(REPO_ROOT / "publication_pipeline" / "scripts"))

from reportkit.version import CONTRACT_VERSION, REPORTKIT_VERSION  # noqa: E402

SCHEMA = "reportkit-container-build/1"
MAX_LOG_BYTES = 256 * 1024
TEMPLATES = REPO_ROOT / "latex_templates"
REPORTKIT = [sys.executable, str(REPO_ROOT / "reportkit")]
CLASS_OPTIONS = re.compile(r"\\documentclass\s*\[([^\]]*)\]\s*\{reportkit\}")
PAPERS = {(210, 297): "a4", (297, 210): "a4-landscape", (216, 279): "letter", (279, 216): "letter-landscape"}

Runner = Callable[[list[str], Path, dict[str, str], int], subprocess.CompletedProcess]


class StepFailed(Exception):
    def __init__(self, step: str, exit_code: int) -> None:
        super().__init__(f"{step} failed with exit {exit_code}")
        self.step, self.exit_code = step, exit_code


def run_process(argv: list[str], cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(argv, 4, exc.stdout or b"", (exc.stderr or b"") + f"\ntimed out after {timeout} s".encode())


def measure_pdf(pdf: Path) -> dict[str, Any]:
    import pymupdf
    with pymupdf.open(pdf) as document:
        rect = document[0].rect
        width, height = round(rect.width * 25.4 / 72), round(rect.height * 25.4 / 72)
        return {"pages": document.page_count, "width_mm": width, "height_mm": height,
                "paper": PAPERS.get((width, height), f"{width}x{height}mm")}


def default_write_lock(path: Path, engine: str) -> None:
    from publication_build import write_lock
    from reportkit.toolchain import toolchain_context, version_line
    write_lock(path, engine=engine, toolchain=toolchain_context(REPO_ROOT),
               tool_versions={"python": platform.python_version(), "pandoc": version_line("pandoc") or "unknown"})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Build:
    def __init__(self, work: Path, args: argparse.Namespace, runner: Runner, measure: Callable, write_lock: Callable, environ: dict[str, str]) -> None:
        self.work, self.args, self.runner, self.measure, self.write_lock = work, args, runner, measure, write_lock
        self.source, self.scratch, self.result = work / "source", work / "build", work / "result"
        self.environ = environ
        self.env = {**os.environ, "LC_ALL": "C", "HOME": str(work / "home"), "TEXMFVAR": str(work / "home" / "texmf-var"),
                    "REPORTKIT_PDF_PYTHON": sys.executable, "shell_escape": "f", "openout_any": "p"}
        self.steps: list[dict[str, Any]] = []
        self.diagnostics: list[dict[str, str]] = []
        self.payloads: dict[str, Any] = {}
        self.record: dict[str, Any] = {"selection": {}, "inspect_passed": False}

    def step(self, name: str, argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 900) -> dict | None:
        started = time.monotonic()
        proc = self.runner(argv, cwd or self.scratch, env or self.env, timeout)
        log = self.result / "logs" / f"{name}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(((proc.stdout or b"") + b"\n--- stderr ---\n" + (proc.stderr or b""))[-MAX_LOG_BYTES:])
        self.steps.append({"name": name, "exit_code": proc.returncode, "seconds": round(time.monotonic() - started, 2), "log": f"logs/{name}.log"})
        try:
            payload = json.loads(proc.stdout or b"null")
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        self.payloads[name] = payload
        if isinstance(payload, dict):
            for item in (payload.get("diagnostics") or payload.get("issues") or [])[:100]:
                if isinstance(item, dict) and len(self.diagnostics) < 100:
                    self.diagnostics.append({"step": name, "code": str(item.get("code", "")), "severity": str(item.get("severity", "error")),
                                             "message": str(item.get("message", ""))[:500]})
        if proc.returncode != 0:
            raise StepFailed(name, proc.returncode)
        return payload

    def verify_inputs(self) -> None:
        manifest_path = self.work / "input-manifest.json"
        self.record["input_manifest_sha256"] = sha256(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {item["path"]: item["sha256"] for item in manifest["files"]}
        present = {p.relative_to(self.source).as_posix() for p in self.source.rglob("*") if p.is_file() or p.is_symlink()}
        problems = sorted(set(expected) ^ present) + [p for p in sorted(expected) if p in present and sha256(self.source / p) != expected[p]]
        log = self.result / "logs" / "verify-inputs.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("\n".join(problems[:200]) or "all staged inputs match input-manifest.json", encoding="utf-8")
        self.steps.append({"name": "verify-inputs", "exit_code": 3 if problems else 0, "seconds": 0, "log": "logs/verify-inputs.log"})
        if problems:
            self.diagnostics.append({"step": "verify-inputs", "code": "RK_CONTAINER_INPUT_MISMATCH", "severity": "error",
                                     "message": f"{len(problems)} staged paths differ from the input manifest"})
            raise StepFailed("verify-inputs", 3)
        shutil.copytree(self.source, self.scratch / "source")

    def pipeline(self) -> Path:
        workspace, out = self.scratch / "source", self.scratch / "output"
        paths = ["--source-root", str(workspace), "--output-root", str(out)]
        profile = ["--profile", self.args.profile] if self.args.profile else []
        self.step("check", [*REPORTKIT, "check", *paths, *profile, "--json"])
        self.step("build", [*REPORTKIT, "build", *paths, *profile, "--json"], timeout=self.args.compile_timeout_seconds * 4)
        report_path = out / "combined" / "build-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.record["selection"] = report.get("selection") or {}
        self.collect_file(report_path, "build-report.json")
        self.collect_file(workspace / "reportkit.lock", "reportkit.lock")
        return out / "combined" / report["pdf"]

    def direct_tex(self) -> Path:
        entry = PurePosixPath(self.args.entry)
        workspace = self.scratch / "source"
        tex = workspace.joinpath(*entry.parts)
        brief = workspace / "editorial-brief.json"
        if brief.is_file():
            self.step("audit-editorial", [*REPORTKIT, "audit-editorial", str(tex), "--brief", str(brief), "--json"])
        texinputs = os.pathsep.join(str(p) for p in (tex.parent, TEMPLATES, TEMPLATES / "themes", TEMPLATES / "publication_types")) + os.pathsep
        env = {**self.env, "TEXINPUTS": texinputs}
        if self.args.engine == "lualatex":
            env["openin_any"] = "a"  # pinned luaotfload reads its Unicode data through Lua (see publication_pipeline/README.md)
        for run in (1, 2):
            self.step(f"compile-{run}", [self.args.engine, "-no-shell-escape", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                      cwd=tex.parent, env=env, timeout=self.args.compile_timeout_seconds)
        self.step("diagnose", [*REPORTKIT, "diagnose", str(tex.with_suffix(".log")), "--source-root", str(workspace), "--output-root", str(self.scratch), "--json"])
        match = CLASS_OPTIONS.search(tex.read_text(encoding="utf-8", errors="replace"))
        options = dict(part.strip().split("=", 1) for part in (match.group(1) if match else "").split(",") if "=" in part)
        self.record["selection"] = {"publication_type": options.get("publication-type"), "theme": options.get("theme", "default"), "engine": self.args.engine}
        pdf = tex.with_suffix(".pdf")
        report = {"schema": "reportkit-direct-tex-build/1", "entry": self.args.entry, "engine": self.args.engine, "pdf": pdf.name,
                  "selection": self.record["selection"], "input_manifest_sha256": self.record["input_manifest_sha256"], "status": "passed"}
        (self.result / "build-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.write_lock(self.result / "reportkit.lock", self.args.engine)
        return pdf

    def collect_file(self, source: Path, relative: str) -> None:
        target = self.result / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def finish_pdf(self, pdf: Path) -> None:
        render_dir = self.scratch / "render"
        render = [*REPORTKIT, "render", str(pdf), "--out", str(render_dir), "--dpi", str(self.args.dpi), "--json"]
        if self.args.pages:
            render[-1:-1] = ["--pages", self.args.pages]
        self.step("render", render)
        inspection = self.step("inspect", [*REPORTKIT, "inspect", str(pdf), "--json"])
        self.record["inspect_passed"] = True
        (self.result / "inspection.json").write_text(json.dumps(inspection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.copytree(render_dir, self.result / "render", dirs_exist_ok=True)
        measured = self.measure(pdf)
        self.record["selection"] = {key: self.record["selection"].get(key) for key in ("publication_type", "theme", "engine", "paper")}
        self.record["selection"]["paper"] = self.record["selection"]["paper"] or measured["paper"]
        self.collect_file(pdf, pdf.name)
        self.record["pdf"] = {"path": pdf.name, "sha256": sha256(pdf), **{k: measured[k] for k in ("pages", "width_mm", "height_mm")}}

    def write_manifest(self, status: str, failed_step: str | None) -> None:
        outputs = [{"path": p.relative_to(self.result).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size}
                   for p in sorted(self.result.rglob("*")) if p.is_file() and p.name != "container-build.json"]
        manifest = {
            "schema": SCHEMA, "status": status, "failed_step": failed_step, "kind": self.args.kind,
            "image": {"reference": self.environ.get("REPORTKIT_IMAGE_REF"), "digest": self.environ.get("REPORTKIT_IMAGE_DIGEST") or None,
                      "id": self.environ.get("REPORTKIT_IMAGE_ID")},
            "release_eligible": self.environ.get("REPORTKIT_RELEASE_ELIGIBLE") == "1",
            "reportkit": {"version": REPORTKIT_VERSION, "contract_version": CONTRACT_VERSION, "commit": self.environ.get("REPORTKIT_COMMIT", "unknown")},
            "steps": self.steps, "diagnostics": self.diagnostics, "outputs": outputs, **self.record,
        }
        (self.result / "container-build.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _clear_to_logs(result: Path) -> None:
    for child in result.iterdir():
        if child.name != "logs":
            shutil.rmtree(child) if child.is_dir() else child.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", required=True, choices=("pipeline", "direct-tex"))
    parser.add_argument("--entry")
    parser.add_argument("--engine", choices=("lualatex", "pdflatex"), default="lualatex")
    parser.add_argument("--profile")
    parser.add_argument("--pages")
    parser.add_argument("--dpi", type=int, default=110)
    parser.add_argument("--compile-timeout-seconds", type=int, default=300)
    parser.add_argument("--work-root", default="/work")
    return parser


def main(argv: list[str] | None = None, *, runner: Runner = run_process, measure: Callable = measure_pdf,
         write_lock: Callable = default_write_lock, environ: dict[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    work = Path(args.work_root)
    build = Build(work, args, runner, measure, write_lock, dict(os.environ if environ is None else environ))
    build.result.mkdir(parents=True, exist_ok=True)
    if args.kind == "direct-tex":
        entry = PurePosixPath(args.entry or "")
        if not args.entry or entry.is_absolute() or ".." in entry.parts or entry.suffix != ".tex":
            build.diagnostics.append({"step": "arguments", "code": "RK_CONTAINER_ENTRY_INVALID", "severity": "error",
                                      "message": "--entry must be a relative .tex path inside the source"})
            build.write_manifest("failed", "arguments")
            return 2
    try:
        build.verify_inputs()
        pdf = build.pipeline() if args.kind == "pipeline" else build.direct_tex()
        build.finish_pdf(pdf)
    except StepFailed as exc:
        _clear_to_logs(build.result)
        build.write_manifest("failed", exc.step)
        print(f"FAIL: {exc}", file=sys.stderr)
        return exc.exit_code if exc.exit_code in (2, 3, 4, 5) else 4
    except Exception as exc:  # noqa: BLE001 -- always return a manifest to the host
        _clear_to_logs(build.result)
        build.diagnostics.append({"step": "internal", "code": "RK_CONTAINER_INTERNAL", "severity": "error", "message": repr(exc)[:500]})
        build.write_manifest("failed", "internal")
        return 70
    build.write_manifest("passed", None)
    print(f"PASS: {build.record['pdf']['path']} ({build.record['pdf']['pages']} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`build --json` owns the Markdown path's compile and its strict log gate. The entrypoint adds nothing there beyond render and inspect. For direct TeX, `diagnose` is the log gate. `_clear_to_logs` guarantees that a failed run never returns a PDF.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_container_entrypoint.py -q`
Expected: PASS.

- [ ] **Step 5: Run the entrypoint for real inside the image, as the build user**

```bash
docker build --file toolchain/Dockerfile --tag reportkit-local .
python3 scripts/reportkit_container.py build --image reportkit-local --allow-unpinned-image --no-pull \
  --kind direct-tex --entry report.tex \
  --source-root latex_templates/examples/editorial-feature --output-root "$(mktemp -d)/Out Tëst"
```

Expected: `PASS`. The output directory contains `report.pdf`, `container-build.json` with `status: passed`, a `selection.theme` of `editorial`, and 6–8 pages (compare `tests/test_editorial_theme.py:256`). If the LuaLaTeX font cache is not writable as uid 10001, this step fails with a luaotfload error in `logs/compile-1.log`. In that case fix `TEXMFVAR`/`HOME` in `Build.env`; do not run the container as root. (The source root here is inside the engine checkout only for this smoke run. The launcher reads it and never writes there, and the output goes to a temporary directory.)

- [ ] **Step 6: Commit**

```bash
chmod +x toolchain/container_build.py
git add toolchain/container_build.py tests/test_container_entrypoint.py tests/test_repository_hygiene.py
git update-index --chmod=+x toolchain/container_build.py
git commit -m "feat(container): in-image build entrypoint with result manifest"
```

Add `toolchain/container_build.py` to the executable-mode test in the same commit.

---

### Task 8: Cross-host gate, real-image integration tests and CI

**Files:**
- Create: `scripts/cross_host_gate.py` (mode 100755), `tests/test_cross_host_gate.py`, `tests/test_container_integration.py`
- Modify: `.github/workflows/contract-ci.yml`

**Interfaces:**
- Consumes: `reportkit_container.run_build`, `reportkit_container.summarize`, `reportkit_container.build_parser`, `rk_container.staging.collect`, `rk_container.results.extract_result`, `rk_container.results.ResultError`.
- Produces:
  - CLI `cross_host_gate.py run --image REF [--allow-unpinned-image] --work-dir DIR --summary FILE [--fresh] [--commit REV]`. Exits `0` only if every required check passed.
  - CLI `cross_host_gate.py compare A.json B.json`. Exits `0` on equivalence and `3` otherwise, and prints the differences.
  - `materialize(commit: str, repo_path: str, destination: Path) -> None` writes raw Git blob bytes with no EOL conversion.
  - `compare_summaries(a: dict, b: dict) -> list[str]` returns a list of differences.
  - Summary schema `reportkit-cross-host-gate/1` with the keys `host`, `image`, `fixtures`, `checks` [{`name`, `status` (`passed`/`failed`/`not-applicable`), `detail`}], `passed`.
  - `FIXTURES`, `REQUIRED_CHECKS` constants.

The gate is one stdlib script that both hosts run unchanged. Windows cannot run Linux containers on hosted runners, so the Windows run is a required manual gate enforced by the release workflow (Task 9). The Linux run happens in CI.

- [ ] **Step 1: Write the failing unit tests**

`tests/test_cross_host_gate.py`:

```python
from __future__ import annotations

import io
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import cross_host_gate as gate  # noqa: E402


def summary(**overrides):
    base = {
        "schema": "reportkit-cross-host-gate/1", "image": {"digest": "sha256:" + "a" * 64},
        "fixtures": {"markdown": {"input_manifest_sha256": "m", "selection": {"theme": "default"}, "page_count": 3, "inspect_passed": True, "pdf_sha256": "p1"}},
        "checks": [{"name": name, "status": "passed", "detail": ""} for name in gate.REQUIRED_CHECKS], "passed": True,
    }
    base.update(overrides)
    return base


def test_equivalent_summaries_ignore_pdf_bytes() -> None:
    other = summary()
    other["fixtures"]["markdown"] = {**other["fixtures"]["markdown"], "pdf_sha256": "p2"}
    assert gate.compare_summaries(summary(), other) == []


def test_differences_are_reported() -> None:
    other = summary(image={"digest": "sha256:" + "b" * 64})
    other["fixtures"]["markdown"] = {**other["fixtures"]["markdown"], "page_count": 4}
    diffs = gate.compare_summaries(summary(), other)
    assert any("image digest" in d for d in diffs) and any("page_count" in d for d in diffs)


def test_failed_or_missing_required_check_fails_comparison() -> None:
    other = summary()
    other["checks"] = [c for c in other["checks"] if c["name"] != "path-safety-symlink"]
    assert any("path-safety-symlink" in d for d in gate.compare_summaries(summary(), other))
    other = summary()
    other["checks"][0]["status"] = "failed"
    assert gate.compare_summaries(summary(), other)


def test_materialize_uses_raw_blob_bytes(tmp_path: Path) -> None:
    if not (REPO / ".git").exists():
        pytest.skip("needs a Git checkout")
    gate.materialize("HEAD", "publication_pipeline/example_publication", tmp_path / "Publication Tëst ü")
    raw = subprocess.run(["git", "show", "HEAD:publication_pipeline/example_publication/manuscript/01-fixture.md"],
                         cwd=REPO, capture_output=True, check=True).stdout
    assert (tmp_path / "Publication Tëst ü" / "manuscript" / "01-fixture.md").read_bytes() == raw
    assert b"\r\n" not in raw


def test_dotdot_result_member_check_is_host_side(tmp_path: Path) -> None:
    status, _ = gate.check_result_dotdot(tmp_path)
    assert status == "passed"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest --noconftest tests/test_cross_host_gate.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'cross_host_gate'`.

- [ ] **Step 3: Implement `scripts/cross_host_gate.py`**

```python
#!/usr/bin/env python3
"""Cross-host acceptance gate for the ReportKit container workflow.

Run the same command on Windows (Docker Desktop, Linux containers) and on
Linux, then compare the two summaries:

    python3 scripts/cross_host_gate.py run --image ghcr.io/iancwm/report-kit@sha256:<d> --work-dir <dir> --summary linux.json
    py -3 scripts\\cross_host_gate.py run --image ... --summary windows.json
    python3 scripts/cross_host_gate.py compare linux.json windows.json

Fixture bytes come from Git blobs, never from the checkout, so a CRLF
checkout still stages identical bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reportkit_container as launcher  # noqa: E402
from rk_container import results, staging  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "reportkit-cross-host-gate/1"
WORK_NAME = "Publication Tëst ü"
FIXTURES = {
    "markdown": {"path": "publication_pipeline/example_publication", "kind": "pipeline", "entry": None},
    "editorial": {"path": "latex_templates/examples/editorial-feature", "kind": "direct-tex", "entry": "report.tex"},
}
REQUIRED_CHECKS = (
    "doctor", "build-markdown", "build-editorial", "crlf-bytes-preserved", "unicode-collision-rejected",
    "path-safety-symlink", "path-safety-dotdot-result", "failure-atomicity",
)
COMPARED_FIXTURE_KEYS = ("input_manifest_sha256", "selection", "page_count", "inspect_passed")


def materialize(commit: str, repo_path: str, destination: Path) -> None:
    listing = subprocess.run(["git", "ls-tree", "-r", "-z", "--full-tree", commit, "--", repo_path],
                             cwd=REPO, capture_output=True, check=True).stdout
    for record in filter(None, listing.split(b"\0")):
        meta, name = record.split(b"\t", 1)
        blob = meta.split()[2].decode()
        relative = Path(name.decode("utf-8")).relative_to(repo_path)
        if relative.parts[0] in ("build",):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.run(["git", "cat-file", "blob", blob], cwd=REPO, capture_output=True, check=True).stdout)


def _build(image: str, allow_unpinned: bool, source: Path, output: Path, kind: str, entry: str | None) -> tuple[int, dict]:
    argv = ["build", "--image", image, "--source-root", str(source), "--output-root", str(output), "--kind", kind]
    argv += ["--entry", entry] if entry else []
    argv += ["--allow-unpinned-image"] if allow_unpinned else []
    return launcher.run_build(launcher.build_parser().parse_args(argv))


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def check_result_dotdot(work: Path) -> tuple[str, str]:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        info = tarfile.TarInfo("result/../escaped.txt")
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    buffer.seek(0)
    destination = work / "dotdot" / "in"
    destination.mkdir(parents=True, exist_ok=True)
    try:
        results.extract_result(buffer, destination)
    except results.ResultError as exc:
        escaped = (destination.parent / "escaped.txt").exists()
        return ("failed", "entry escaped") if escaped else ("passed", exc.code)
    return "failed", "a ../ result entry was accepted"


def _expect_rejection(source: Path, code: str) -> tuple[str, str]:
    try:
        staging.collect(source)
    except staging.StagingError as exc:
        codes = {p.code for p in exc.problems}
        return ("passed", code) if code in codes else ("failed", f"rejected with {sorted(codes)}")
    return "failed", "accepted"


def run(args: argparse.Namespace) -> dict:
    work = Path(args.work_dir) / WORK_NAME
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    checks: list[dict] = []
    fixtures: dict[str, dict] = {}

    def record(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    if args.fresh:
        subprocess.run(["docker", "image", "rm", "--force", args.image], capture_output=True)
    record("host-has-no-lualatex", "passed" if shutil.which("lualatex") is None else "failed", shutil.which("lualatex") or "")
    doctor = subprocess.run(["docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64", args.image,
                             "doctor", "--require", "pinned-toolchain", "--json"], capture_output=True)
    record("doctor", "passed" if doctor.returncode == 0 else "failed", doctor.stdout.decode("utf-8", "replace")[-2000:])

    for name, fixture in FIXTURES.items():
        source = work / f"{name} source"
        materialize(args.commit, fixture["path"], source)
        code, outcome = _build(args.image, args.allow_unpinned_image, source, work / f"{name} output", fixture["kind"], fixture["entry"])
        record(f"build-{name}", "passed" if code == 0 else "failed", outcome.get("message", ""))
        if code == 0:
            fixtures[name] = launcher.summarize(work / f"{name} output")

    crlf = work / "markdown-crlf source"
    materialize(args.commit, FIXTURES["markdown"]["path"], crlf)
    for md in crlf.rglob("*.md"):
        md.write_bytes(md.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    expected = staging.collect(crlf).manifest_sha256()
    code, outcome = _build(args.image, args.allow_unpinned_image, crlf, work / "markdown-crlf output", "pipeline", None)
    staged_hash = launcher.summarize(work / "markdown-crlf output")["input_manifest_sha256"] if code == 0 else None
    record("crlf-bytes-preserved", "passed" if code == 0 and staged_hash == expected else "failed", f"exit {code}; {outcome.get('message', '')}")
    if code == 0:
        fixtures["markdown-crlf"] = launcher.summarize(work / "markdown-crlf output")

    unicode_dir = work / "unicode-collision"
    unicode_dir.mkdir()
    (unicode_dir / "caf\u00e9.md").write_bytes(b"1")
    (unicode_dir / "cafe\u0301.md").write_bytes(b"2")
    if len(list(unicode_dir.iterdir())) == 2:
        record("unicode-collision-rejected", *_expect_rejection(unicode_dir, "RK_STAGE_PATH_COLLISION"))
    else:
        record("unicode-collision-rejected", "failed", "filesystem normalized the names; run the gate on a non-normalizing filesystem")

    case_dir = work / "case-collision"
    case_dir.mkdir()
    (case_dir / "Chapter.md").write_bytes(b"1")
    (case_dir / "chapter.md").write_bytes(b"2")
    if len(list(case_dir.iterdir())) == 2:
        record("case-collision-rejected", *_expect_rejection(case_dir, "RK_STAGE_PATH_COLLISION"))
    else:
        record("case-collision-rejected", "not-applicable", "case-insensitive filesystem cannot hold both names")

    link_dir = work / "symlink"
    link_dir.mkdir()
    (work / "outside.txt").write_bytes(b"outside")
    try:
        (link_dir / "link.md").symlink_to(work / "outside.txt")
        record("path-safety-symlink", *_expect_rejection(link_dir, "RK_STAGE_SYMLINK"))
    except OSError as exc:
        record("path-safety-symlink", "failed", f"cannot create a symlink ({exc}); enable Windows Developer Mode and rerun")

    if os.name == "nt":
        import _winapi
        junction_dir = work / "junction"
        junction_dir.mkdir()
        (work / "outside-dir").mkdir()
        _winapi.CreateJunction(str(work / "outside-dir"), str(junction_dir / "j"))
        record("path-safety-junction", *_expect_rejection(junction_dir, "RK_STAGE_REPARSE_POINT"))

    record("path-safety-dotdot-result", *check_result_dotdot(work))

    good_output = work / "editorial output"
    if good_output.is_dir():
        before = _tree_digest(good_output)
        broken = work / "editorial-broken source"
        materialize(args.commit, FIXTURES["editorial"]["path"], broken)
        tex = broken / "report.tex"
        tex.write_bytes(tex.read_bytes().replace(b"\\end{document}", b"\\ReportKitGateUndefinedMacro\n\\end{document}"))
        code, _ = _build(args.image, args.allow_unpinned_image, broken, good_output, "direct-tex", "report.tex")
        failure = good_output.with_name(good_output.name + ".failed")
        ok = code != 0 and _tree_digest(good_output) == before and (failure / "launcher-failure.json").is_file() and any((failure / "logs").glob("*.log"))
        record("failure-atomicity", "passed" if ok else "failed", f"exit {code}")
    else:
        record("failure-atomicity", "failed", "editorial fixture did not build")

    digests = {s.get("image_digest") for s in fixtures.values()}
    required_ok = all(any(c["name"] == n and c["status"] == "passed" for c in checks) for n in REQUIRED_CHECKS)
    return {
        "schema": SCHEMA,
        "host": {"system": platform.system(), "release": platform.release(), "python": platform.python_version(), "machine": platform.machine()},
        "image": {"reference": args.image, "digest": digests.pop() if len(digests) == 1 else None},
        "fixtures": fixtures, "checks": checks,
        "passed": required_ok and not any(c["status"] == "failed" for c in checks),
    }


def compare_summaries(a: dict, b: dict) -> list[str]:
    diffs = []
    if a["image"].get("digest") != b["image"].get("digest") or not a["image"].get("digest"):
        diffs.append(f"image digest differs or is missing: {a['image'].get('digest')} vs {b['image'].get('digest')}")
    for name in sorted(set(a["fixtures"]) | set(b["fixtures"])):
        left, right = a["fixtures"].get(name), b["fixtures"].get(name)
        if left is None or right is None:
            diffs.append(f"fixture {name} missing on one host")
            continue
        for key in COMPARED_FIXTURE_KEYS:
            if left.get(key) != right.get(key):
                diffs.append(f"fixture {name} {key}: {left.get(key)!r} vs {right.get(key)!r}")
    for label, summary in (("first", a), ("second", b)):
        statuses = {c["name"]: c["status"] for c in summary["checks"]}
        for name in REQUIRED_CHECKS:
            if statuses.get(name) != "passed":
                diffs.append(f"{label} summary: required check {name} is {statuses.get(name, 'missing')}")
    return diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--image", required=True)
    run_parser.add_argument("--allow-unpinned-image", action="store_true")
    run_parser.add_argument("--work-dir", required=True)
    run_parser.add_argument("--summary", required=True)
    run_parser.add_argument("--fresh", action="store_true", help="remove the local image first so the gate pulls it")
    run_parser.add_argument("--commit", default="HEAD")
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("first")
    compare_parser.add_argument("second")
    args = parser.parse_args(argv)
    if args.command == "compare":
        diffs = compare_summaries(*(json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.first, args.second)))
        print("\n".join(diffs) or "equivalent")
        return 3 if diffs else 0
    result = run(args)
    Path(args.summary).write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    for check in result["checks"]:
        print(f"{check['status'].upper():15} {check['name']}")
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run: `python3 -m pytest --noconftest tests/test_cross_host_gate.py -q`
Expected: PASS.

- [ ] **Step 5: Write the real-image integration test**

`tests/test_container_integration.py`:

```python
"""Runs the cross-host gate against a real image. CI sets
REPORTKIT_CONTAINER_TEST_IMAGE and REPORTKIT_REQUIRE_DOCKER=1 so a missing
daemon fails instead of skipping."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import cross_host_gate as gate  # noqa: E402

IMAGE = os.environ.get("REPORTKIT_CONTAINER_TEST_IMAGE")
if not IMAGE:
    if os.environ.get("REPORTKIT_REQUIRE_DOCKER") == "1":
        raise RuntimeError("REPORTKIT_REQUIRE_DOCKER=1 but REPORTKIT_CONTAINER_TEST_IMAGE is unset")
    pytest.skip("set REPORTKIT_CONTAINER_TEST_IMAGE to run container integration tests", allow_module_level=True)


def test_gate_passes_on_this_host(tmp_path: Path) -> None:
    summary = gate.run(argparse.Namespace(image=IMAGE, allow_unpinned_image="@sha256:" not in IMAGE, work_dir=str(tmp_path),
                                          summary=str(tmp_path / "s.json"), fresh=False, commit="HEAD"))
    failed = [c for c in summary["checks"] if c["status"] == "failed" and c["name"] != "host-has-no-lualatex"]
    assert not failed, failed
    assert summary["fixtures"]["editorial"]["selection"]["theme"] == "editorial"
    assert 6 <= summary["fixtures"]["editorial"]["page_count"] <= 8
    assert summary["fixtures"]["markdown"]["inspect_passed"] is True
```

(`host-has-no-lualatex` is informational on a developer machine. The release gate in Task 9 runs on a clean runner, where it must pass.)

- [ ] **Step 6: Wire CI**

In `.github/workflows/contract-ci.yml`, add these steps to the `pinned-toolchain` job after the existing verify step:

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Container workflow gate (Linux / ext4, uid 10001, no network)
        env:
          REPORTKIT_CONTAINER_TEST_IMAGE: reportkit-ci
          REPORTKIT_REQUIRE_DOCKER: "1"
        run: |
          python -m pip install --disable-pip-version-check pytest
          python -m pytest --noconftest -q tests/test_container_integration.py
```

Add a new job for the host-side unit tests on both operating systems. Windows hosted runners cannot run Linux containers, which is why Task 9 keeps a manual gate:

```yaml
  container-launcher-host:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-24.04, windows-2022]
    runs-on: ${{ matrix.os }}
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4   # Windows runner checks out with core.autocrlf=true
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install --disable-pip-version-check pytest
      - name: Launcher, staging, results and gate unit tests (stdlib only)
        run: >-
          python -m pytest --noconftest -q
          tests/test_container_staging.py tests/test_container_docker.py
          tests/test_container_results.py tests/test_container_launcher.py
          tests/test_cross_host_gate.py tests/test_repository_hygiene.py
```

- [ ] **Step 7: Run everything locally**

Run: `docker build -f toolchain/Dockerfile -t reportkit-ci . && REPORTKIT_CONTAINER_TEST_IMAGE=reportkit-ci REPORTKIT_REQUIRE_DOCKER=1 python3 -m pytest --noconftest -q tests/test_container_integration.py`
Expected: PASS.

Run: `ruff check python_scripts publication_pipeline scripts tests adapters toolchain`
Expected: no findings.

- [ ] **Step 8: Commit**

```bash
chmod +x scripts/cross_host_gate.py
git add scripts/cross_host_gate.py tests/test_cross_host_gate.py tests/test_container_integration.py .github/workflows/contract-ci.yml tests/test_repository_hygiene.py
git update-index --chmod=+x scripts/cross_host_gate.py
git commit -m "test(container): cross-host acceptance gate and CI matrix"
```

Add `scripts/cross_host_gate.py` to the executable-mode test in the same commit.

---

### Task 9: Image release workflow and manifest

**Files:**
- Create: `scripts/image_release_manifest.py`, `tests/test_image_release_manifest.py`, `toolchain/release_gates.sh` (mode 100755), `.github/workflows/toolchain-release.yml`

**Interfaces:**
- Consumes: `cross_host_gate.py run|compare`, `reportkit.version`.
- Produces:
  - `build_manifest(repository: str, digest: str, commit: str, tag: str, source_date_epoch: int, gate_summary: dict) -> dict` raises `ValueError`.
  - CLI `image_release_manifest.py --repository R --digest D --commit C --tag T --source-date-epoch N --gate-summary FILE` prints the manifest JSON.
  - Manifest schema `reportkit-image-release/1` with the keys `image` (`<repo>@<digest>`), `repository`, `digest`, `platform`, `tags` (`sha-<commit>`, `<tag>`), `reportkit` {`version`, `contract_version`, `commit`, `ref`}, `source_date_epoch`, `gates` {`linux`: summary}.
  - GitHub Environment `toolchain-release` with required reviewers (a one-time repository setting; document it).

- [ ] **Step 1: Write the failing tests**

`tests/test_image_release_manifest.py`:

```python
from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "python_scripts"))

from image_release_manifest import build_manifest  # noqa: E402
from reportkit.version import REPORTKIT_VERSION  # noqa: E402

DIGEST, COMMIT, TAG = "sha256:" + "a" * 64, "b" * 40, f"v{REPORTKIT_VERSION}"
GATE = {"passed": True, "image": {"digest": DIGEST}}


def test_manifest_shape() -> None:
    data = build_manifest("ghcr.io/iancwm/report-kit", DIGEST, COMMIT, TAG, 1_700_000_000, GATE)
    assert data["image"] == f"ghcr.io/iancwm/report-kit@{DIGEST}"
    assert data["tags"] == [f"sha-{COMMIT}", TAG] and data["platform"] == "linux/amd64"
    assert data["reportkit"]["commit"] == COMMIT and data["gates"]["linux"] == GATE


@pytest.mark.parametrize("digest,commit,tag,gate", [
    ("sha256:short", COMMIT, TAG, GATE), (DIGEST, "abc", TAG, GATE), (DIGEST, COMMIT, "v0.0.0", GATE),
    (DIGEST, COMMIT, TAG, {"passed": False, "image": {"digest": DIGEST}}),
    (DIGEST, COMMIT, TAG, {"passed": True, "image": {"digest": "sha256:" + "c" * 64}}),
])
def test_manifest_rejects_inconsistent_inputs(digest, commit, tag, gate) -> None:
    with pytest.raises(ValueError):
        build_manifest("ghcr.io/iancwm/report-kit", digest, commit, tag, 1, gate)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest --noconftest tests/test_image_release_manifest.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/image_release_manifest.py`**

```python
#!/usr/bin/env python3
"""Emit the machine-readable release manifest for a gated toolchain image."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_scripts"))

from reportkit.version import CONTRACT_VERSION, REPORTKIT_VERSION  # noqa: E402

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def build_manifest(repository: str, digest: str, commit: str, tag: str, source_date_epoch: int, gate_summary: dict) -> dict:
    if not DIGEST.match(digest):
        raise ValueError(f"not a sha256 digest: {digest}")
    if not COMMIT.match(commit):
        raise ValueError(f"not a full commit SHA: {commit}")
    if tag != f"v{REPORTKIT_VERSION}":
        raise ValueError(f"tag {tag} does not match REPORTKIT_VERSION {REPORTKIT_VERSION}")
    if not gate_summary.get("passed") or gate_summary.get("image", {}).get("digest") != digest:
        raise ValueError("the Linux gate summary did not pass for this digest")
    return {
        "schema": "reportkit-image-release/1", "image": f"{repository}@{digest}", "repository": repository,
        "digest": digest, "platform": "linux/amd64", "tags": [f"sha-{commit}", tag],
        "reportkit": {"version": REPORTKIT_VERSION, "contract_version": CONTRACT_VERSION, "commit": commit, "ref": tag},
        "source_date_epoch": source_date_epoch, "gates": {"linux": gate_summary},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repository", "digest", "commit", "tag", "gate-summary"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--source-date-epoch", type=int, required=True)
    args = parser.parse_args()
    gate = json.loads(Path(args.gate_summary).read_text(encoding="utf-8"))
    print(json.dumps(build_manifest(args.repository, args.digest, args.commit, args.tag, args.source_date_epoch, gate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest --noconftest tests/test_image_release_manifest.py -q`
Expected: PASS.

- [ ] **Step 5: Add `toolchain/release_gates.sh`**

```bash
#!/usr/bin/env bash
# In-image release gates for one image reference (local candidate or pushed
# digest). Usage: toolchain/release_gates.sh <image-ref> <summary.json>
set -euo pipefail
image="$1"
summary="$2"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker run --rm --network none --platform linux/amd64 --entrypoint /bin/bash "$image" -lc '
  set -euo pipefail
  export PATH="/opt/reportkit/.venv/bin:$PATH"
  ./reportkit doctor --require pinned-toolchain --json
  ./reportkit docs --check --json
  bash scripts/acceptance_check.sh --require-tex
  python scripts/contract_acceptance.py --json'

unpinned=()
[[ "$image" == *@sha256:* ]] || unpinned=(--allow-unpinned-image)
python3 "$root/scripts/cross_host_gate.py" run --image "$image" "${unpinned[@]}" \
  --work-dir "${RUNNER_TEMP:-$(mktemp -d)}/gate" --summary "$summary" --commit HEAD
```

- [ ] **Step 6: Add `.github/workflows/toolchain-release.yml`**

```yaml
name: ReportKit toolchain image release

# Three explicit operations: (1) image build from a pinned Git context,
# gated in-image; (2) push of that exact image under an immutable sha tag;
# (3) qualification of the pushed digest on a clean runner, a manual
# Windows gate, and only then the release tag. A push alone never releases.
on:
  push:
    tags: ["v*"]
  workflow_dispatch:
    inputs:
      tag:
        description: "Existing release tag, e.g. v1.9.3 (run from any host with: gh workflow run toolchain-release.yml -f tag=v1.9.3)"
        required: true

permissions:
  contents: read

concurrency:
  group: toolchain-release-${{ inputs.tag || github.ref_name }}
  cancel-in-progress: false

env:
  IMAGE_REPO: ghcr.io/iancwm/report-kit
  RELEASE_TAG: ${{ inputs.tag || github.ref_name }}

jobs:
  build-gate-push:
    runs-on: ubuntu-24.04
    timeout-minutes: 120
    permissions:
      contents: read
      packages: write
    outputs:
      commit: ${{ steps.source.outputs.commit }}
      epoch: ${{ steps.source.outputs.epoch }}
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ env.RELEASE_TAG }}
          fetch-depth: 0
      - name: Resolve release tag to one commit
        id: source
        run: |
          set -euo pipefail
          tag_commit="$(git rev-parse --verify "refs/tags/${RELEASE_TAG}^{commit}")"
          head_commit="$(git rev-parse --verify HEAD)"
          [ "$tag_commit" = "$head_commit" ] || { echo "::error::tag ${RELEASE_TAG} is ${tag_commit}, checkout is ${head_commit}"; exit 1; }
          if [ "$GITHUB_EVENT_NAME" = push ] && [ "$tag_commit" != "$GITHUB_SHA" ]; then
            echo "::error::tag ${RELEASE_TAG} is ${tag_commit}, event SHA is ${GITHUB_SHA}"; exit 1
          fi
          version="$(python3 -c 'import sys; sys.path.insert(0, "python_scripts"); from reportkit.version import REPORTKIT_VERSION as v; print(v)')"
          [ "$RELEASE_TAG" = "v${version}" ] || { echo "::error::tag ${RELEASE_TAG} does not match REPORTKIT_VERSION ${version}"; exit 1; }
          echo "commit=${tag_commit}" >> "$GITHUB_OUTPUT"
          echo "epoch=$(git log -1 --format=%ct "$tag_commit")" >> "$GITHUB_OUTPUT"
      - uses: docker/setup-buildx-action@v3
      - name: Image build (pinned Git context, linux/amd64)
        env:
          SOURCE_DATE_EPOCH: ${{ steps.source.outputs.epoch }}
        run: >-
          docker buildx build
          --platform linux/amd64
          --file toolchain/Dockerfile
          --build-arg SOURCE_DATE_EPOCH
          --build-arg REPORTKIT_COMMIT=${{ steps.source.outputs.commit }}
          --build-arg REPORTKIT_REF=${{ env.RELEASE_TAG }}
          --output type=docker,name=reportkit-release:candidate,rewrite-timestamp=true
          "https://github.com/${{ github.repository }}.git#${{ steps.source.outputs.commit }}"
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: In-image gates before publication
        run: bash toolchain/release_gates.sh reportkit-release:candidate "$RUNNER_TEMP/candidate-gate.json"
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Push the gated image under its immutable sha tag
        id: push
        run: |
          set -euo pipefail
          ref="${IMAGE_REPO}:sha-${{ steps.source.outputs.commit }}"
          if docker manifest inspect "$ref" >/dev/null 2>&1; then
            echo "::error::$ref already exists; sha tags are immutable. Delete that package version to retry."; exit 1
          fi
          docker tag reportkit-release:candidate "$ref"
          docker push "$ref"
          digest="$(docker image inspect --format '{{range .RepoDigests}}{{println .}}{{end}}' "$ref" | grep "^${IMAGE_REPO}@" | head -n1 | cut -d@ -f2)"
          [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "::error::could not read pushed digest"; exit 1; }
          echo "digest=${digest}" >> "$GITHUB_OUTPUT"

  smoke-by-digest:
    needs: build-gate-push
    runs-on: ubuntu-24.04   # a fresh runner: no local TeX, no cached layers
    timeout-minutes: 90
    permissions:
      contents: write
      packages: read
    env:
      IMAGE: ${{ env.IMAGE_REPO }}@${{ needs.build-gate-push.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ needs.build-gate-push.outputs.commit }}
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Pushed digest passes the same gates
        run: |
          set -euo pipefail
          test -z "$(command -v lualatex)" || { echo "::error::runner has lualatex"; exit 1; }
          bash toolchain/release_gates.sh "$IMAGE" linux-gate-summary.json
      - name: Release manifest and draft release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          python3 scripts/image_release_manifest.py --repository "$IMAGE_REPO" \
            --digest "${{ needs.build-gate-push.outputs.digest }}" --commit "${{ needs.build-gate-push.outputs.commit }}" \
            --tag "$RELEASE_TAG" --source-date-epoch "${{ needs.build-gate-push.outputs.epoch }}" \
            --gate-summary linux-gate-summary.json > reportkit-image-release.json
          gh release view "$RELEASE_TAG" >/dev/null 2>&1 || gh release create "$RELEASE_TAG" --draft --verify-tag \
            --title "ReportKit ${RELEASE_TAG}" --notes "Toolchain image: \`${IMAGE}\`. Awaiting the Windows gate (references/docker-workflow.md)."
          gh release upload "$RELEASE_TAG" reportkit-image-release.json linux-gate-summary.json --clobber
      - uses: actions/upload-artifact@v4
        with:
          name: image-release
          path: |
            reportkit-image-release.json
            linux-gate-summary.json

  promote:
    needs: [build-gate-push, smoke-by-digest]
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    environment: toolchain-release   # required reviewers = the manual Windows gate
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ needs.build-gate-push.outputs.commit }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Require an equivalent Windows gate summary for this digest
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          gh release download "$RELEASE_TAG" --pattern linux-gate-summary.json --pattern windows-gate-summary.json --clobber
          test -f windows-gate-summary.json || { echo "::error::upload windows-gate-summary.json to the draft release first"; exit 1; }
          python3 -c 'import json,sys; s=json.load(open("windows-gate-summary.json")); sys.exit(0 if s["host"]["system"]=="Windows" else "not a Windows summary")'
          python3 scripts/cross_host_gate.py compare linux-gate-summary.json windows-gate-summary.json
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Point the release tag at the qualified digest (carbon copy, same digest)
        run: |
          set -euo pipefail
          digest="${{ needs.build-gate-push.outputs.digest }}"
          docker buildx imagetools create --prefer-index=false --tag "${IMAGE_REPO}:${RELEASE_TAG}" "${IMAGE_REPO}@${digest}"
          tagged="$(docker buildx imagetools inspect "${IMAGE_REPO}:${RELEASE_TAG}" --format '{{json .Manifest}}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["digest"])')"
          [ "$tagged" = "$digest" ] || { echo "::error::${RELEASE_TAG} resolved to ${tagged}, expected ${digest}"; exit 1; }
      - name: Publish the release
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh release edit "$RELEASE_TAG" --draft=false
```

- [ ] **Step 7: Validate the workflow statically**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/toolchain-release.yml'))"` and, if `actionlint` is available, `actionlint .github/workflows/toolchain-release.yml`.
Expected: no errors. Also dry-run the gate script against a local image: `bash toolchain/release_gates.sh reportkit-local /tmp/s.json`. Expected: exit 0.

The first real run needs two one-time repository settings. Create the `toolchain-release` environment with required reviewers. Allow GHCR package writes for this repository. Document both in Task 10.

- [ ] **Step 8: Commit**

```bash
chmod +x toolchain/release_gates.sh
git add scripts/image_release_manifest.py tests/test_image_release_manifest.py toolchain/release_gates.sh .github/workflows/toolchain-release.yml tests/test_repository_hygiene.py
git update-index --chmod=+x toolchain/release_gates.sh
git commit -m "ci: gated, digest-bound toolchain image release"
```

Add `toolchain/release_gates.sh` to the executable-mode test in the same commit.

---

### Task 10: Documentation

**Files:**
- Create: `references/docker-workflow.md`
- Modify: `SKILL.md` (first-run block at lines 24–50 and "Build and inspect" at lines 587–610), `README.md`, `AGENTS.md` (first-run steps 2–4), `CHANGELOG.md`

**Interfaces:**
- Consumes: the CLI surfaces from Tasks 6, 8 and 9 exactly as defined above.

- [ ] **Step 1: Write `references/docker-workflow.md`**

Required sections (each must contain real commands, not placeholders):
1. **Three operations.** Define image build, push and publication build as in spec section 1. State that a push never qualifies an image.
2. **Host prerequisites.** Python 3.11+ and the Docker CLI only. On Windows, switch Docker Desktop to Linux containers, and note the `RK_DOCKER_WINDOWS_CONTAINERS` message. ARM hosts run under emulation and are not an acceptance platform.
3. **Publication build.** Give the `build` command for both hosts (`python3` and `py -3`), for `--kind pipeline` and for `--kind direct-tex --entry report.tex`. Explain that the kind is always explicit. Explain `editorial-brief.json` triggering `audit-editorial`. Recommend `--output-root <publication>/output`.
4. **What gets staged.** Cover the exclusion list, the rejection codes table (`RK_STAGE_*`), the limits with their flags, and the principle that paths are reported, never renamed.
5. **Results.** Describe the `/work/result` layout and the `container-build.json` fields. Explain the atomic swap, `<output>.failed/` and `launcher-failure.json`, and the `RK_OUTPUT_*` codes, including `RK_OUTPUT_LOCKED`. Say that the author must still review every page under `render/`.
6. **Pinning.** Consumers use `ghcr.io/iancwm/report-kit@sha256:<digest>` from the release's `reportkit-image-release.json`. Local development builds use `docker buildx build --platform linux/amd64 -f toolchain/Dockerfile -t reportkit-dev .` plus `--allow-unpinned-image`, and those results record `release_eligible: false`.
7. **Release procedure (operators).** Start with `gh workflow run toolchain-release.yml -f tag=vX.Y.Z` (any host) or a tag push. Then the Windows gate: clone at the tag, run `py -3 scripts\cross_host_gate.py run --image ghcr.io/iancwm/report-kit@sha256:<digest> --work-dir %TEMP%\rk-gate --summary windows-gate-summary.json --fresh --commit vX.Y.Z` with Developer Mode enabled, then `gh release upload vX.Y.Z windows-gate-summary.json`, then approve the `toolchain-release` environment. Include the one-time setup: create the environment with required reviewers, and grant GHCR package write. Include recovery when a `sha-` tag already exists.
8. **Non-goals.** Byte-identical PDFs, Windows containers, arm64, and untrusted TeX.

- [ ] **Step 2: Update `SKILL.md`, `README.md` and `AGENTS.md`**

- In `SKILL.md`, before the existing clone/`setup_tex.sh` block, add a short "Recommended cross-host path (Docker)" block with the `reportkit_container.py build` command and a link to `references/docker-workflow.md`. Relabel the existing block "Native Debian/Ubuntu path". In "Build and inspect", add one sentence saying that the container build runs the same `check`/`build`/`render`/`inspect` sequence and that page review is still required.
- In `README.md`, make the Docker workflow the first quick start and keep `scripts/setup_tex.sh` as the native alternative.
- In `AGENTS.md`, add to step 2: "On Windows, or any host without the native toolchain, use `scripts/reportkit_container.py` with a pinned image digest instead of `scripts/setup_tex.sh`." Add to step 4: "for container builds, inspect `container-build.json` → `selection`."
- In `CHANGELOG.md`, add an Unreleased entry listing the launcher, entrypoint, release workflow and `.gitattributes`/`.dockerignore`.

- [ ] **Step 3: Check the generated docs**

Run: `./reportkit docs --check --json`
Expected: `"passed": true`. If an edited region is generated, run `./reportkit docs --write`, review the diff, and rerun `--check`.

Run: `python3 -m pytest tests/test_agent_contract.py tests/test_context_budget.py -q`
Expected: PASS. SKILL.md size budgets may apply. If a budget test fails, move detail into `references/docker-workflow.md` rather than raising the budget.

- [ ] **Step 4: Commit**

```bash
git add references/docker-workflow.md SKILL.md README.md AGENTS.md CHANGELOG.md
git commit -m "docs: recommend the digest-pinned Docker workflow across hosts"
```

---

## Spec coverage map

| Spec requirement | Task |
| --- | --- |
| §2.1 tag → full SHA, fail on mismatch | 9 (`Resolve release tag`) |
| §2.2 pinned base, snapshot, hash lock, font hashes | unchanged Dockerfile, guarded by `test_agent_contract.py:552` and Task 2 Step 6 |
| §2.3 `SOURCE_DATE_EPOCH` from commit | 9 (`--build-arg SOURCE_DATE_EPOCH`, `rewrite-timestamp=true`) |
| §2.4 doctor, docs, TeX acceptance, editorial fixture in-image before publication | 9 (`release_gates.sh` on the candidate) |
| §2.5 push `sha-<commit>` + release tag, digest in machine-readable manifest | 9 (push step, `image_release_manifest.py`, promote) |
| §2.6 consumers use digest | 6 (`RK_IMAGE_NOT_PINNED`), 10 |
| §2.7 push cannot qualify; clean-runner digest smoke | 9 (`smoke-by-digest`, `promote` gated) |
| `.dockerignore`, `.gitattributes` | 1 |
| Platform rule, Windows-container preflight | 4 |
| §3 stdlib launcher, arg array, native paths with spaces/Unicode | 3, 4, 6 |
| Preflight before staging | 6 (`test_preflight_failure_happens_before_staging`) |
| Tar staging via `docker cp`, no bind mount | 4, 6 |
| Archive rules (bytes, exclusions, rejections, limits, manifest) | 3 |
| In-image entrypoint, explicit kinds, audit when brief present | 7 |
| No network, bounded resources, no mounts, non-root, no shell escape | 2, 4, 7 |
| Atomic result return, failure directory, container always removed | 5, 6 |
| Result contents and `container-build.json` fields | 7 |
| §4 matrix: pull by digest, publication build, CRLF, case/Unicode, path safety, clean build, failure atomicity, release from either host | 8 (gate checks), 9 (Windows gate enforced by `promote`) |
| §5.5 docs | 10 |

## Known limitations to state in the PR

- The two `os.replace` calls in `results.install` do not make one atomic filesystem operation. A crash between them leaves the previous output at `.<name>.previous-<pid>` next to the target. That path is named in `references/docker-workflow.md`.
- On Windows, the case-collision check is `not-applicable` because NTFS cannot hold both names in one directory by default. Equivalent rejection is shown through the Unicode-normalization collision, which NTFS can hold.
- The root `build/` directory holds about 2,200 tracked debug files. After Task 1 they stay out of the image, but they remain in Git; clean them up separately.
