# Publication pipeline

Reusable build harness that turns a consumer publication project's
`manuscript/` + `fragments/` into a compiled, QA'd PDF. It ships as part of
the ReportKit engine and knows nothing about any specific publication — see
[references/repository-boundary.md](../references/repository-boundary.md).

The publication itself — its manuscript, figures, `publication.yaml`, build
output, and final PDF — lives in a separate consumer project, not in this
repository. Point the harness at that project with `--source-root`; build
artefacts land there too, via `--output-root` (default:
`<source-root>/build`), never inside this checkout.

`example_publication/` is a small generic fixture used to exercise the
pipeline in this repo's own tests and acceptance checks — it is not a
publication to build on.

## Commands

```bash
bash scripts/setup.sh
<report-kit-clone>/reportkit check --source-root <publication-project>
<report-kit-clone>/reportkit build --mode section --section manuscript/01-introduction.md --source-root <publication-project>
<report-kit-clone>/reportkit build --source-root <publication-project> --output-root <publication-project>/build
```

The `reportkit` facade also exposes `doctor`, `context`, `diagnose`, `inspect`,
`docs`, `analyse-history`, and `package`. Add `--profile release` to resolve a release
profile from a nested `publication.yaml`; `--engine` is an explicit TeX-engine
override. Optional `sources.yaml` and `links.yaml` files are validated during
`check` and `build`; the latter renders named `\RKLink{key}` links into the
generated document. `inspect` reports page dimensions, bookmarks, fonts, blank
pages, and near-margin content. The shell wrappers and direct
`publication_build.py` invocation remain supported.

`<publication-project>/publication.yaml` supplies the title, subtitle, author,
and version; `--title`/`--author`/`--version` on the CLI override it. An
optional `license:` section can override `content_license`,
`content_license_url`, and `classification` for that publication; omitted
values retain the engine defaults. A missing title (in both the config and
the CLI) fails the build with a message naming the file and the flag.

`combine.sh` is the canonical full-document build and is driven by
`manuscript/order.txt`. It validates the publication before Pandoc runs,
compiles twice with `-file-line-error`, applies the strict log gate, renders
pages into an atomic directory, writes `build/combined/build-report.json`,
and — on a passing build — writes `reportkit.lock` at the project root,
pinning the ReportKit ref/commit and toolchain versions the PDF was built
against.

The isolated section command is an author-feedback loop, not a release
artifact. `requirements.txt` pins the one PDF-inspection dependency used by
the harness: PyMuPDF.

Markdown input is converted with raw TeX disabled. Files in `fragments/` and
direct `.tex` documents are trusted escape hatches and must come from a trusted
author. Converter and TeX children run without shell escape, with restrictive
TeX file access, a 120-second timeout, and a 2 GiB address-space limit. Trusted
operators can override those resource values with CLI flags or
`REPORTKIT_COMPILE_TIMEOUT_SECONDS` / `REPORTKIT_MEMORY_LIMIT_MB`;
`publication.yaml` cannot weaken them. The complete contract and exit-code
table are in [references/agent-contract.md](../references/agent-contract.md).

## If a publication needs something this pipeline doesn't do

Propose the change here, as a generic capability (a new CLI flag, a new
`publication.yaml` key, a new validation rule) — not as a one-off script or
hard-coded value inside the publication project. See
[references/repository-boundary.md](../references/repository-boundary.md)
for the guardrails this follows.
