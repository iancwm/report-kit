# ReportKit Docker workflow: cross-host image and publication builds

**Status:** Implementation integrated in `main` through `70a8f28` (2026-09-28). Linux CI and the digest-bound release workflow are wired; the real Windows/Docker Desktop gate remains required for each image release.
**Target:** `iancwm/report-kit`
**Date:** 28 September 2026
**Last updated:** 2026-09-30

> Saved verbatim from the specification supplied on 2026-09-28. The
> implementation plan is `docs/superpowers/plans/2026-09-28-reportkit-docker-cross-host-workflow.md`.

## 1. Purpose and terminology

Provide one supported workflow that builds a ReportKit toolchain image and uses it to produce a publication PDF from either Windows (NTFS, Docker Desktop in Linux-container mode) or Linux (ext4, Docker Engine). The host must not need LuaLaTeX, ReportKit fonts, Pandoc, or the pinned Python packages.

An **image build** creates the toolchain image. A **push** transfers an already-built image to a registry; it does not rebuild or repair it. A **publication build** uses a particular image digest to turn a separate publication project into a PDF. The workflow must make these three operations explicit.

The existing [Dockerfile](https://github.com/iancwm/report-kit/blob/main/toolchain/Dockerfile) is the starting point. The existing [CI workflow](https://github.com/iancwm/report-kit/blob/main/.github/workflows/contract-ci.yml) already builds and tests that image on Ubuntu. Publication content stays outside the engine repository under the [repository boundary](https://github.com/iancwm/report-kit/blob/main/references/repository-boundary.md).

### Goals

1. A sanctioned image build produces a working `linux/amd64` ReportKit image regardless of whether the command is initiated on Windows or Linux. The pushed image is identified and consumed by digest.
2. The same publication source bytes build through the same container paths and commands on NTFS and ext4, without host LuaLaTeX or shell-specific path syntax.
3. A failed build returns a clear error and cannot leave a partial PDF presented as a successful release.
4. The result records the ReportKit commit, image digest, input hashes, target selection, and build diagnostics.

### Non-goals for v1

- Native Windows containers or a Windows TeX installation.
- Promising byte-identical PDFs across runs. Functional equivalence is required; bitwise reproducibility is a separate gate until timestamps, PDF metadata, font caches, and TeX outputs have been verified.
- Building untrusted arbitrary TeX as a general hosted service. ReportKit's direct `.tex` and fragment inputs remain trusted-author inputs.
- `linux/arm64` support until the pinned base, TeX packages, fonts, and visual fixtures pass on that architecture.

## 2. Image release contract

### Canonical build

The release workflow builds from an exact Git commit, never from an arbitrary host checkout. Use Buildx with `--platform linux/amd64`, the repository's `toolchain/Dockerfile`, and a Git context pinned to the full commit SHA. The remote Git context makes the build input independent of Windows checkout line endings, file modes, and NTFS path behavior. Docker documents Git contexts with commit checksums and explicit target platforms in its [build-context](https://docs.docker.com/build/concepts/context/) and [Buildx](https://docs.docker.com/reference/cli/docker/buildx/build/) references.

The workflow must:

1. Resolve the release tag to a full commit SHA and fail if they disagree.
2. Pin the Linux base image by digest, retain the Debian snapshot and Python hash lock, and verify bundled font hashes as the current Dockerfile does.
3. Set `SOURCE_DATE_EPOCH` from the source commit timestamp (or an explicitly fixed epoch), not the invoking host's clock. Docker documents this for [reproducible builds](https://docs.docker.com/build/ci/github-actions/reproducible-builds/).
4. Run `reportkit doctor --require pinned-toolchain --json`, `reportkit docs --check --json`, the TeX acceptance checks, and the canonical editorial fixture **inside the built image before publication**.
5. Push through the release workflow to the chosen registry, initially `ghcr.io/iancwm/report-kit`, under an immutable `sha-<full-commit>` tag and a release tag. Capture the registry digest and publish it in a machine-readable release manifest.
6. Consumers pull `ghcr.io/iancwm/report-kit@sha256:<digest>`. Moving tags and `latest` are not release inputs.
7. Do not let a standalone `docker push` qualify an image as released. A pushed image must pass the same digest-bound smoke test on a clean runner.

Add or tighten `.dockerignore` so local build output, publication projects, caches, virtual environments, and Git metadata do not enter a local Docker context. Add `.gitattributes` rules that keep Dockerfiles, shell scripts, TeX and repository control files in LF and preserve executable script mode. These are defense in depth; the release build still uses the pinned Git context.

### Platform rule

V1 publishes `linux/amd64` only. Windows Docker Desktop must run **Linux containers**; a Windows-container daemon fails preflight with an actionable message. A Linux ARM host may use an amd64-capable builder/emulation if supported, but is not a required acceptance platform. A later multi-platform manifest must be built and tested per architecture before the release tag points to it. Docker's [multi-platform documentation](https://docs.docker.com/build/building/multi-platform/) explains that a manifest can select variants, but pushing a manifest does not validate each variant.

## 3. Host-neutral publication runner

Add one Python-standard-library launcher, for example `scripts/reportkit_container.py`. Python 3.11+ and the Docker CLI are the only host-side runtime requirements. The launcher arguments are identical on both hosts; invoke it with `py -3` on Windows or `python3` on Linux:

```text
scripts/reportkit_container.py build --image ghcr.io/iancwm/report-kit@sha256:<digest> --source-root <publication-directory> --output-root <publication-output-directory>
```

The launcher invokes Docker with an argument array, never a shell command assembled from a path string. It accepts absolute or relative native host paths, including spaces and non-ASCII characters. It resolves and validates the output target before writing. It reports missing Docker, an unavailable daemon, Windows-container mode, an unsupported architecture, or an unavailable image before staging content.

### Stage inputs inside the Linux filesystem

Do **not** bind-mount the publication directory as the default path. The launcher creates a temporary container from the pinned image and streams a tar archive of the publication into `/work/source` using `docker cp - <container>:/work/source`. Docker supports tar streaming to and from `docker cp` on stopped containers ([reference](https://docs.docker.com/reference/cli/docker/container/cp/)). All TeX, font-cache, intermediate, and output writes then occur in the container's Linux filesystem, not on NTFS or a host bind mount.

The input archive must:

- Preserve regular-file bytes and relative path spelling. Do not silently rewrite manuscript line endings, source encoding, or binary assets.
- Exclude `.git/`, host virtual environments, `build/`, `output/`, caches, and prior PDFs from the input set.
- Reject absolute paths, `..`, symlinks, junctions/reparse points, device files, duplicate archive entries, case-fold or Unicode-normalization collisions, and paths escaping the source root.
- Enforce documented total-size and per-file limits before creating the container.
- Record SHA-256 for each included file in an input manifest. Report invalid paths instead of renaming them.

The image contains a small container entrypoint that runs the ReportKit CLI on `/work/source`, writes only to `/work/build` and `/work/result`, and exits nonzero on a failed check, editorial audit, compile, diagnostic gate, render, or inspect. For a hand-authored feature article, run `audit-editorial` when `editorial-brief.json` is present. For Markdown publications, use the existing `check` and `build` selection from `publication.yaml`. Keep the direct-TeX and Markdown paths explicit rather than guessing from file presence.

Run the build container with no network, bounded CPU/memory/time, and no host mounts. If possible, use a non-root build user with `/work` owned by that user; the tar staging and font-cache locations must be tested under that account. Do not enable TeX shell escape. A container is an isolation boundary for filesystem behavior, but this v1 workflow assumes trusted publication source.

### Return outputs atomically

On success, stream `/work/result` out as a tar archive with `docker cp <container>:/work/result -`. Validate archive members before extraction, verify each output hash against the result manifest, then replace the requested output directory atomically. On failure, leave the last successful output untouched and retain a bounded diagnostic log in a separate failure directory. Always remove the temporary container.

`/work/result` must contain the final PDF, `build-report.json`, `reportkit.lock`, inspection report, page-render manifest and selected page PNGs, plus `container-build.json` with:

- image reference and resolved digest;
- ReportKit commit and contract version;
- publication input manifest hash;
- selected publication type, theme, engine, and paper size;
- command exit statuses and diagnostic summary;
- final PDF SHA-256.

Do not claim a successful editorial build based only on a TeX exit code. The source composition audit and every rendered page remain required review gates under the [feature-article contract](https://github.com/iancwm/report-kit/blob/main/references/feature-article-authoring.md).

## 4. Test matrix and acceptance criteria

| Gate | Windows / NTFS | Linux / ext4 | Pass condition |
| --- | --- | --- | --- |
| Image pull by digest | Docker Desktop, Linux containers | Docker Engine | Same `linux/amd64` manifest digest and successful `doctor` |
| Publication build | Identical fixture bytes at a path with spaces and Unicode | Identical fixture bytes at an equivalent path | Same selected target, input hashes, page count, and successful inspect |
| CRLF checkout | Git checkout configured for CRLF | LF checkout | Engine image unaffected; publication bytes preserved and build succeeds where syntax permits |
| Filesystem edge cases | Case-insensitive input | Case-sensitive input | Case-colliding names rejected identically before build |
| Path safety | Junction, symlink, `..` archive entry | Symlink, `..` archive entry | Rejected without reading outside source root |
| Clean build | No local TeX or cached image layers | No local TeX or cached image layers | Build succeeds after pulling the pinned image |
| Failure atomicity | Invalid source or compilation error | Same | Nonzero exit, readable diagnostics, prior output unchanged |
| Image release | Initiated from Windows or Linux | Initiated from Linux CI | Pushed digest passes the same in-image acceptance and editorial smoke checks |

Acceptance does **not** require identical image digests for two independently rebuilt images unless a separate reproducible-build test proves them. It does require that both builds use the same pinned source, platform, package inputs, and tests, and that consumers use an individually verified digest. A bare `docker push` from either host cannot change the digest of an already-built image; it can only publish what that host built.

## 5. Implementation slices

1. **Image release:** add a release workflow around the existing Dockerfile, pin the Git context and platform, run in-image gates, push only after success, and emit a digest manifest. Add `.gitattributes` and `.dockerignore` rules.
2. **Container build entrypoint:** add one script that runs ReportKit's existing check, audit, build, render, and inspect commands with fixed container paths and writes a result manifest.
3. **Host launcher:** implement tar staging, Docker lifecycle, preflight, archive validation, and atomic result extraction in Python stdlib. Do not duplicate ReportKit's document logic in the launcher.
4. **Cross-filesystem CI:** run the same publication fixture on Windows/NTFS with Docker Desktop and Linux/ext4, plus path-safety and failure-atomicity tests. If hosted Windows runners cannot provide a Linux Docker daemon, keep Windows as a required manual release gate until an eligible runner is available; do not mark the matrix green by skipping it.
5. **Docs:** make the Docker workflow the recommended cross-host path in `SKILL.md` and `README.md`; retain `scripts/setup_tex.sh` as the native Debian/Ubuntu path. Document image digests, publication/source separation, and Docker Desktop Linux-container mode.

## 6. Open decisions before implementation

- Confirm that `ghcr.io/iancwm/report-kit` is the desired registry and that the release workflow has package-write permission.
- Choose explicit input-size and runtime limits appropriate to expected books, images, and charts.
- Decide whether local image builds are supported as a development-only path; release publication should remain digest-bound.
- Decide whether the first release needs `linux/arm64`; if so, add architecture-specific acceptance before publishing a manifest list.
