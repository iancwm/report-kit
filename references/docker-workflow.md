# Docker cross-host workflow

Build a publication inside the pinned ReportKit toolchain image instead of
installing TeX natively. The publication is streamed into a container (never
bind-mounted), built with no network access, and the verified result replaces
the output directory only on success. This is the recommended path on Windows
and on any host without a working native LuaLaTeX install, and it is the only
path release operators use to qualify a new toolchain image.

## Three operations

Keep these separate; they have different actors and different guarantees.

1. **Image build.** `docker buildx build --platform linux/amd64 -f
   toolchain/Dockerfile ...` produces a candidate image from a pinned base,
   pinned apt package versions, and hash-checked fonts/requirements. Anyone
   can do this locally for development.
2. **Push.** Uploading an image to `ghcr.io/iancwm/report-kit` under a tag. A
   push by itself proves nothing about the image's correctness — **a push
   never qualifies an image for release.** Only the gated workflow below
   (build, in-image gates, push, clean-runner smoke, a real Windows gate, and
   an approved promotion) produces a digest that publication builds should
   trust for a release.
3. **Publication build.** `python3 scripts/reportkit_container.py build`
   stages a publication, runs it inside a named image, and installs the
   verified result. This is what authors run day to day.

## Host prerequisites

Only two things are required on the host that runs `reportkit_container.py`:

- **Python 3.11+** (stdlib only — the launcher and its `rk_container` modules
  import nothing outside the standard library).
- **The Docker CLI**, talking to a daemon running **Linux containers**.

On Windows, Docker Desktop defaults to Windows containers on some installs.
If the daemon reports anything other than `linux`, the launcher fails fast
with `RK_DOCKER_WINDOWS_CONTAINERS` before staging anything — in Docker
Desktop, choose "Switch to Linux containers..." and retry.

ARM hosts (Apple Silicon, ARM64 Windows/Linux) run the `linux/amd64` image
under QEMU emulation. The launcher detects this from `docker version` and
prints a warning (`Docker daemon is arm64; running linux/amd64 under
emulation (not a supported acceptance platform)`) rather than failing —
emulated builds are useful for local iteration but are not an acceptance
platform, and the release workflow never runs one.

## Publication build

The command line is identical on every host; only the interpreter changes.

```bash
# Linux/macOS
python3 scripts/reportkit_container.py build \
  --image ghcr.io/iancwm/report-kit@sha256:<digest> \
  --source-root <publication-dir> \
  --output-root <publication-dir>/output \
  --kind pipeline
```

```powershell
# Windows
py -3 scripts\reportkit_container.py build `
  --image ghcr.io/iancwm/report-kit@sha256:<digest> `
  --source-root <publication-dir> `
  --output-root <publication-dir>\output `
  --kind pipeline
```

For a target-aware hand-authored `.tex` publication, set
`document.source_mode: tex` and `document.main` in `publication.yaml`, then use
`--kind pipeline`. This runs `reportkit check` and `reportkit build` with the
same target, engine, and composition gates as a native build.

Use `--kind direct-tex` only for the lower-level raw-TeX path when the target
reasoning loop is not needed. It compiles the supplied entry and diagnoses its
log, but skips `reportkit check` and `reportkit build` target gates. Pass an
entry file relative to the source root:

```bash
python3 scripts/reportkit_container.py build \
  --image ghcr.io/iancwm/report-kit@sha256:<digest> \
  --source-root <publication-dir> --output-root <publication-dir>/output \
  --kind direct-tex --entry report.tex --engine lualatex
```

`--kind` is always explicit — there is no default and no autodetection from
the staged files. `--engine` (`lualatex`, the default, or `pdflatex`) only
applies to `direct-tex`; `--profile` only applies to `pipeline`. Passing
either flag against the wrong `--kind` is a config error
(`RK_ARGS_PROFILE_UNEXPECTED`/`RK_ARGS_ENTRY_UNEXPECTED`), not a silent
no-op.

If a staged `direct-tex` source contains `editorial-brief.json` next to the
entry file, the container runs the legacy `reportkit audit-editorial` check
before compiling. This optional audit does not replace the target-aware gates
available through `--kind pipeline`.

Recommend `--output-root <publication-dir>/output` (a subdirectory of the
publication, not the engine clone) so the same directory conventions apply
whether the build ran natively or in a container. `--output-root` must be
empty, new, or already owned by this launcher (see **Results** below); it may
not be the source root or a directory that contains it.

Other flags worth knowing: `--pages` (a page selection to render, e.g.
`1,3-5`), `--dpi` (render resolution, default 110), `--no-pull` (fail instead
of pulling if the image is not already local), `--timeout-seconds`/`--cpus`/
`--memory` (container resource limits), and `--json` (machine-readable
output). `python3 scripts/reportkit_container.py summarize <output-root>`
prints the cross-host comparison fields (image digest, selection, page count,
input manifest hash) from an existing result without re-running the build.

## What gets staged

Staging runs entirely on the host, before any container exists
(`scripts/rk_container/staging.py`). Nothing is bind-mounted; the launcher
walks the source tree, hashes every file, and writes a single tar stream via
`docker cp --archive`.

**Excluded automatically**, not staged and not reported as an error: any
directory named `.git`, `.hg`, `.svn`, `.venv`, `venv`, `__pycache__`,
`.pytest_cache`, `.ruff_cache`, `.mypy_cache`, or `.cache` at any depth, plus
any directory containing a `pyvenv.cfg`; and, at the top level only, `build/`,
`output/`, `reportkit.lock`, and any `*.pdf` file.

**Rejected**, which fails the build before any container starts:

| Code | Meaning |
| --- | --- |
| `RK_STAGE_SOURCE_MISSING` | `--source-root` is not a directory |
| `RK_STAGE_SYMLINK` | a symbolic link — replace it with the real file |
| `RK_STAGE_REPARSE_POINT` | a Windows junction or other reparse point |
| `RK_STAGE_PATH_NONPORTABLE` | a name Windows cannot represent: a control character, one of `\:*?"<>\|`, or a trailing space/dot |
| `RK_STAGE_PATH_COLLISION` | two paths collide under case-folding or Unicode (NFC) normalization — for example `café.md` and `café.md`, or `Chapter.md` and `chapter.md` |
| `RK_STAGE_SPECIAL_FILE` | not a regular file or directory (device, FIFO, socket) |
| `RK_STAGE_FILE_TOO_LARGE` | one file exceeds the per-file limit |
| `RK_STAGE_TOO_MANY_FILES` | more files than the file-count limit |
| `RK_STAGE_TOO_LARGE` | total staged size exceeds the total-size limit |
| `RK_STAGE_FILE_CHANGED` | a file's size or hash changed while it was being staged |

Limits default to 1024 MB total / 200 MB per file / 20,000 files and are
overridable with `--max-input-mb`, `--max-file-mb`, and `--max-files`.

The principle behind all of this: **a path is reported, never silently
renamed, normalized, or dropped.** A collision or a Windows-unsafe name fails
the build with the exact offending path so the author fixes it at the
source, rather than shipping a publication whose staged layout on Linux
diverges from what it would be on Windows.

## Results

On success, `/work/result` inside the container becomes `<output-root>/` on
the host. It contains:

- the final PDF
- `build-report.json` (pipeline builds) or an equivalent report for
  `direct-tex`
- `reportkit.lock`
- `inspection.json`
- `render/pages.json` plus one PNG per rendered page
- `logs/<step>.log` for every step used. Pipeline builds include check/build;
  raw direct-TeX builds include compile/diagnostics and the optional editorial
  audit. Both paths render and inspect the PDF.
- `container-build.json` — the manifest described below

`container-build.json` fields: `schema`, `status` (`passed`/`failed`),
`failed_step`, `kind`, `image` (`reference`, `digest`, `id`),
`release_eligible` (true only when the image was pulled by digest — never
for `--allow-unpinned-image`), `reportkit` (`version`, `contract_version`,
`commit`), `input_manifest_sha256`, `selection` (`publication_type`,
`theme`, `engine`, `paper`), `steps`, `diagnostics`, `inspect_passed`, `pdf`
(`path`, `sha256`, `pages`, `width_mm`, `height_mm`), and `outputs` (every
result file's relative path, SHA-256, and size — verified on the host before
anything is installed).

Installing the result is an atomic swap where possible: the new result is
extracted into a sibling temp directory, verified against
`container-build.json`'s own `outputs` list, and only then moved into place
with `os.replace`. If `<output-root>` already existed, its previous contents
are moved aside to `<output-root's parent>/.<name>.previous-<pid>` and
removed only after the swap succeeds — the previous output survives a crash
between the two `os.replace` calls, at that path, rather than being lost.

On failure, the launcher never leaves a partial or corrupt `<output-root>`.
Diagnostics — logs, whatever result files were collected, and a
`launcher-failure.json` record — land in `<output-root>.failed/` next to it,
using the same atomic-install mechanism.

Output/result errors:

| Code | Meaning |
| --- | --- |
| `RK_OUTPUT_NOT_MANAGED` | `<output-root>` (or `.failed/`) already has files this launcher didn't write — point at an empty or new directory |
| `RK_OUTPUT_LOCKED` | the previous output couldn't be replaced, typically because a program (a PDF viewer) still has a file open — close it and retry |
| `RK_OUTPUT_CONTAINS_SOURCE` | `--output-root` is, or contains, `--source-root` |
| `RK_OUTPUT_INSIDE_SOURCE` | `--output-root` is inside the source but not under its `build/` or `output/` subdirectory |
| `RK_OUTPUT_PARENT_MISSING` | the output directory's parent doesn't exist |
| `RK_OUTPUT_SYMLINK` | `--output-root` (or `.failed/`) is a symlink |
| `RK_RESULT_HASH_MISMATCH` | a result file's content doesn't match its recorded SHA-256 — treat the result as untrusted, do not install it by hand |
| `RK_RESULT_MANIFEST_MISSING` / `RK_RESULT_MISSING_FILE` / `RK_RESULT_UNLISTED_FILE` / `RK_RESULT_UNSAFE_MEMBER` / `RK_RESULT_TOO_LARGE` / `RK_RESULT_DUPLICATE_MEMBER` | the returned archive didn't match what the container claimed to produce |

A passing container build is not an editorial sign-off. As with a native
build, **the author must still review every rendered page under `render/`**
for clipped text, overlapping labels, broken arrows, bad page breaks, and
meaning conveyed only by color, before treating the PDF as final.

## Pinning

**Consumers** (anyone building a publication) should pass the exact digest
from a release's `reportkit-image-release.json` (attached to the GitHub
release), not a mutable tag:

```bash
python3 scripts/reportkit_container.py build \
  --image ghcr.io/iancwm/report-kit@sha256:<digest> ...
```

Passing an image reference without `@sha256:...` fails immediately with
`RK_IMAGE_NOT_PINNED` unless `--allow-unpinned-image` is also given.

**Local development** builds of the image itself are unpinned by design —
you're iterating on the Dockerfile, not qualifying a release:

```bash
docker buildx build --platform linux/amd64 -f toolchain/Dockerfile \
  -t reportkit-dev .

python3 scripts/reportkit_container.py build \
  --image reportkit-dev --allow-unpinned-image \
  --source-root <publication-dir> --output-root <publication-dir>/output \
  --kind pipeline
```

Every result built this way records `release_eligible: false` in
`container-build.json` — a reminder that this digest was never pushed,
gated, or cross-host verified, however clean the local build looked.

## Release procedure (operators)

This is what qualifies a new digest as `release_eligible` and worth pinning
consumers to. It needs a Linux CI runner (automatic) and one human on a real
Windows/Docker-Desktop-Linux-containers host (manual — this is the whole
reason the workflow has an approval gate).

1. **Start the workflow.** Either push a `v<version>` tag, or from any host:
   ```bash
   gh workflow run toolchain-release.yml -f tag=vX.Y.Z
   ```
2. **`build-gate-push` (automatic).** Resolves the tag to one full commit
   SHA (hard-fails on any mismatch), builds `toolchain/Dockerfile` from that
   pinned Git context with `SOURCE_DATE_EPOCH` taken from the commit, runs
   `toolchain/release_gates.sh` inside the candidate image (`reportkit
   doctor --require pinned-toolchain`, `reportkit docs --check`,
   `scripts/acceptance_check.sh --require-tex`,
   `scripts/contract_acceptance.py`, and the Linux half of
   `scripts/cross_host_gate.py run`), then pushes the gated image to
   `ghcr.io/iancwm/report-kit:sha-<commit>`. That tag is immutable — the
   push hard-fails if it already exists (see recovery below).
3. **`smoke-by-digest` (automatic, clean runner).** A second, cache-free
   runner pulls the pushed image **by digest** and re-runs the same gates
   against it, confirming the pushed bytes — not just the local build — pass.
   It writes `reportkit-image-release.json` and `linux-gate-summary.json`
   and uploads both to a **draft** GitHub release.
4. **The Windows gate (manual — do this next).** On a real Windows host with
   Docker Desktop set to Linux containers and Developer Mode enabled (needed
   for the symlink-rejection check), clone the repo at the release tag and
   run:
   ```powershell
   py -3 scripts\cross_host_gate.py run `
     --image ghcr.io/iancwm/report-kit@sha256:<digest> `
     --work-dir %TEMP%\rk-gate --summary windows-gate-summary.json `
     --fresh --commit vX.Y.Z
   ```
   Use the digest from `reportkit-image-release.json` on the draft release.
   Then upload the result:
   ```bash
   gh release upload vX.Y.Z windows-gate-summary.json
   ```
5. **`promote` (gated).** Requires the `toolchain-release` GitHub
   Environment's approval (see one-time setup below). Once approved, it
   downloads both gate summaries, confirms `windows-gate-summary.json` is
   actually a Windows summary, and runs
   `python3 scripts/cross_host_gate.py compare linux-gate-summary.json
   windows-gate-summary.json` — any diagnostic or fixture-result divergence
   between the two hosts fails the job. Only then does it point the release
   tag (`ghcr.io/iancwm/report-kit:vX.Y.Z`) at the qualified digest and
   publish the draft release.

**One-time repository setup** (cannot be done from a workflow run — a repo
admin does this once in GitHub's UI):

- Create a GitHub Environment named `toolchain-release` and add required
  reviewers to it. This is what turns `promote` into an approval gate.
- Ensure the repository's `GITHUB_TOKEN` (or the account running the
  workflow) has `packages: write` on `ghcr.io/iancwm/report-kit` — the
  workflow already requests `packages: write` permissions, but a private
  package's visibility/linkage may need a one-time confirmation in the
  package's own settings the first time it's published from Actions.

**Recovery: `sha-<commit>` tag already exists.** `sha-` tags are treated as
immutable by design — the push step hard-fails rather than overwriting one.
This only happens if a release for the exact same commit was attempted
before. Delete that specific package version from the GHCR package's
"Versions" page (not the whole package) and rerun the workflow.

## Non-goals

- **Byte-identical PDFs across hosts.** The cross-host gate compares
  structural facts (image digest, input manifest hash, selection, page
  count, `inspect_passed`) and required-check pass/fail — not pixel- or
  byte-identical PDF output between Linux and Windows.
- **Windows containers.** ReportKit's image is `linux/amd64` only; Windows
  hosts run it under Docker Desktop's Linux container mode, not as a native
  Windows container.
- **arm64.** The published image is `linux/amd64`; an ARM host runs it under
  emulation for local development only, never as an acceptance or release
  platform.
- **Untrusted TeX.** The container build runs with no network access, a
  fixed non-root build user, dropped capabilities, and `shell_escape=f`/
  `no-shell-escape` — but it still compiles whatever TeX/Markdown was
  staged. It is not a sandbox against a maliciously authored manuscript; the
  trust boundary is the same one described in
  [agent-contract.md](agent-contract.md), not a stronger one.
