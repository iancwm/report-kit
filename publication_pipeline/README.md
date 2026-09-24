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
<report-kit-clone>/publication_pipeline/scripts/setup.sh <publication-project>/build/.venv
<report-kit-clone>/reportkit check --source-root <publication-project>
<report-kit-clone>/reportkit build --mode section --section manuscript/01-introduction.md --source-root <publication-project>
<report-kit-clone>/reportkit build --source-root <publication-project> --output-root <publication-project>/build
<report-kit-clone>/reportkit render --source-root <publication-project> --pages 1,3-4 --dpi 150
```

The `reportkit` facade also exposes `doctor`, `init`, `context`, `diagnose`, `inspect`,
`render`, `docs`, `analyse-history`, and `package`. Add `--profile release` to resolve a release
profile from a nested `publication.yaml`; `--engine` is an explicit TeX-engine
override. Optional `sources.yaml` and `links.yaml` files are validated during
`check` and `build`; the latter renders named `\RKLink{key}` links into the
generated document. `inspect` reports page dimensions, bookmarks, fonts, blank
pages, and near-margin content. Direct `publication_build.py` invocation
remains supported. Set `REPORTKIT_PDF_PYTHON` to override the consumer
project's default `<output-root>/.venv/bin/python` for page rendering and PDF
inspection.

`render` is the standalone authoring-feedback loop for an existing build PDF. It
can select individual pages or ranges, controls rasterization DPI, writes the
selected PNGs atomically, and emits a `pages.json` manifest containing the page
list and renderer fingerprint. Pass the PDF path explicitly when it is outside
the latest build output.

`build` resolves the publication type, theme, renderer, entrypoint, Pandoc
writer, TeX engine, and paper/canvas from `publication.yaml`. It stages the
selected entrypoint as `publication.tex`, records the resolved target under
`selection` in `build-report.json`, and emits a `REPORTKIT-SELECTED` marker in
the build log. The registered presentation target uses the Beamer writer and
the slides renderer; the registered paged targets use the LaTeX writer.

Presentation Markdown may also contain fenced `reportkit` directives such as
```reportkit messageslide
headline: One clear message
content: Supporting evidence.
```
These are parsed into a typed IR before Pandoc, validated against the
capability contract with source-line diagnostics, and rendered as safe TeX.
Only an explicit `fragment:` may include trusted TeX, and it must name a
contained `fragments/*.tex` file. Generated body maps include directive
locations alongside the existing visual-fragment mappings.

The optional top-level `brand:` section accepts only `primary`, `secondary`,
`logo`, and `display_font`. A theme must explicitly opt into brand overrides;
accepted values are normalized once into a shared effective-theme record and
materialized for both TeX and charts. `inspect_pdf.py` automatically consumes
the adjacent `publication.log` selection marker; use `--selection-log` or
`--require-selection-marker` to make that check explicit for another log.

The canonical slide acceptance fixture has a stricter profile available to
the repository gate: `inspect_pdf.py --slide-accessibility` checks PDF
metadata, catalog language, outline entries, meaningful external links,
diagram `/ActualText`, and the declared tagged-PDF capability. The profile is
run by `scripts/acceptance_check.sh` and `tests/test_slide_accessibility.py`.

`<publication-project>/publication.yaml` supplies the title, subtitle, author,
date, and version; set `date: build` to print the local calendar date for each
build, or provide a literal date for a fixed publication date. The
`--title`/`--author`/`--version` CLI flags override their corresponding fields. An
optional `license:` section can override `content_license`,
`content_license_url`, and `classification` for that publication; omitted
values retain the engine defaults. A missing title (in both the config and
the CLI) fails the build with a message naming the file and the flag.

Before TeX runs, optional consumer-project `figures/` and `assets/` files are
copied into the isolated build directory. Their relative paths and SHA-256
hashes are recorded in `build-report.json` for build provenance.

Markdown publications can declare replaceable photograph or illustration
slots in `image-slots.yaml` and reference them with a standalone
`[[REPORTKIT-IMAGE:img:<slug>]]` line. A supplied local asset is captioned and
placed at that location; a missing asset remains a clearly marked placeholder
in draft builds and blocks a release build. Build never downloads images.
See [the callout and image-slot authoring guide](../references/callouts-and-image-slots.md)
for declaration fields, rights metadata, and replacement steps.

`reportkit build --mode combined` is the canonical full-document build and is driven by
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
author. Converter and TeX children run without shell escape, with restricted
output writes, a 120-second timeout, and a 2 GiB address-space limit. The
LuaLaTeX path uses `openin_any=a` because pinned `luaotfload` reads its Unicode
data files through Lua; Markdown remains raw-TeX-disabled and fragment paths
are validated before compilation. Trusted operators can override those resource values with CLI flags or
`REPORTKIT_COMPILE_TIMEOUT_SECONDS` / `REPORTKIT_MEMORY_LIMIT_MB`;
`publication.yaml` cannot weaken them. The complete contract and exit-code
table are in [references/agent-contract.md](../references/agent-contract.md).

## If a publication needs something this pipeline doesn't do

Propose the change here, as a generic capability (a new CLI flag, a new
`publication.yaml` key, a new validation rule) — not as a one-off script or
hard-coded value inside the publication project. See
[references/repository-boundary.md](../references/repository-boundary.md)
for the guardrails this follows.
