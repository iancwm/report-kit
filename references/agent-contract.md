# Agent contract, diagnostics, and trusted build boundary

ReportKit 1.9.3 exposes its host-neutral interface through the `reportkit` CLI.
`reportkit init` scaffolds a consumer project outside the engine clone; its
font installation is opt-in because `TEXMFLOCAL` may be system-owned.
`reportkit context --json` is the authoritative capability catalog; generated
Markdown is explanatory and must not be used as a second source of primitive
signatures.

## Contract discovery

```bash
reportkit context --json
reportkit context --publication-type equity-research \
  --theme institutional-research --kind callout --kind chart --json
reportkit context --schema context
reportkit context --schema diagnostic
reportkit docs --check --json
```

Contract version `1.1.0` describes the combinations registered today:
`technical-report/{default,technical}/paged`,
`equity-research/institutional-research/paged`, and the experimental
`presentation/executive/slides` target. Theme entries expose semantic
capability names, not visual values; `technical` resolves to the same
implementation as `default`. English with Latin script is verified;
Vietnamese is metadata-only pending the i18n phase, and RTL is unsupported.

Fenced `reportkit` blocks in ordinary Markdown are an additive constrained
authoring surface. `reportkit check` validates them into the 1.0.0 authoring
IR before Pandoc or TeX, including primitive availability, arguments,
constraints, source locations, and trusted-fragment containment; `reportkit
build` renders the validated nodes to escaped TeX. Ordinary Markdown remains
Pandoc input. Content-derived fields cannot supply raw TeX. A `fragment:`
field may select only an existing filename under the consumer project's
`fragments/` directory, which is the explicit trusted escape hatch. The
context payload's legacy `capabilities.authoring.mode` remains `trusted-latex`
for compatibility; use the checked-in `schemas/reportkit-authoring.schema.json`
for the constrained dialect's machine contract.

The contract and the ReportKit release have independent versions. `check` and
`build` accept `--contract-version`: a different major version is rejected;
an older same-major caller receives a structured warning and may continue.
Patch releases may clarify descriptions and add diagnostics without removing a
field. Minor releases may add optional records and stable primitives. Removing
or changing stable fields, primitive syntax, or exit meanings requires a major
contract version. A deprecated primitive remains marked and diagnostic-bearing
for at least one minor release before removal. Existing raw LaTeX primitives
and legacy context fields remain supported throughout ReportKit v1.x.

## Diagnostic envelope and exits

JSON-capable commands return `passed`, `schema_version`, `diagnostics`, and
their command-specific result. Every diagnostic includes an actionable
remediation and stable code. The v1.x aliases `errors`, `issues`, `file`,
`line`, `kind`, `owner`, and `blocking` remain available.

| Exit | Meaning |
| --- | --- |
| 0 | success |
| 2 | CLI usage, configuration, or incompatible contract major |
| 3 | static validation, diagnostic gate, documentation drift, or PDF inspection |
| 4 | conversion/compile timeout, memory exhaustion, or TeX/Pandoc failure |
| 5 | required dependency unavailable or pinned-toolchain mismatch |
| 70 | unexpected internal failure |

## Pinned visual toolchain

`toolchain/toolchain.lock.json` records the digest-pinned base image, frozen
Debian snapshot, exact apt and hashed Python dependencies, font checksums,
normalization settings, and 150-DPI renderer identity. Build reports,
`reportkit.lock`, context, doctor output, and visual-baseline manifests record
the expected or resolved fingerprint. Run authoritative release and pixel QA
inside `toolchain/Dockerfile`:

```bash
docker build -f toolchain/Dockerfile -t reportkit-pinned .
docker run --rm reportkit-pinned doctor --require pinned-toolchain --json
```

A pixel comparison made under another fingerprint fails as a toolchain
mismatch; it is never reported as a visual regression. PDF-visible generated
dates and TeX metadata use the fixed `SOURCE_DATE_EPOCH`. Build reports also
record the resolved publication/theme/renderer selection and effective-theme
hashes. Pixel output is the release gate; ReportKit does not promise
byte-identical PDF files in v1.9.

## Security and trust

Markdown is untrusted content: Pandoc's raw-TeX extension is disabled and text
is escaped by conversion. A direct `.tex` document and files under
`fragments/` are the explicit trusted escape hatches. Use them only for content
whose provenance the caller trusts. Static validation rejects shell-escape
primitives, parent traversal, absolute TeX inputs, and escaping Markdown asset
paths before conversion.

Every production converter and TeX pass runs without shell escape, in a scoped
build directory, with restrictive `openin_any`/`openout_any`, a 120-second
wall-clock limit, and a 2 GiB child address-space limit. CLI flags and the
trusted `REPORTKIT_COMPILE_TIMEOUT_SECONDS` /
`REPORTKIT_MEMORY_LIMIT_MB` environment variables may change those resource
limits; publication YAML cannot. If the host cannot enforce the memory limit,
the build exits as an environment failure instead of silently weakening it.

Validated Markdown/IR authoring and slide accessibility parity are implemented
in the current tree. Context-token budgets, broader i18n, and a second host
adapter remain deferred. The slide parity claim is non-tagged: metadata,
catalog language, outline/bookmarks, meaningful links, and diagram
`/ActualText` are gated, while tagged PDF remains unsupported pending the
separate `DocumentMetadata` tagging spike.

## Agent visual feedback loop

Most current models are multimodal: looking at a rendered page catches
overfull lines, collided diagram labels, bad page breaks, and broken slide
composition -- failures that compile cleanly and are invisible in the log.
Treat build, render, and inspect as one authoring loop, not separate CI-only
steps:

```bash
reportkit build --json
reportkit render --pages 1-3 --dpi 150 --json   # cheap: only the pages named
reportkit inspect --json
```

`reportkit render` resolves the most recently built PDF the same way
`reportkit inspect` does (or takes an explicit path), writes PNGs plus an
`index.html` contact sheet and `pages.json` manifest to a predictable
`--out` directory (default: `<output-root>/render`), and accepts a `--pages`
selection (`"1"`, `"1-3"`, `"1,3,5-7"`) so an agent can inspect one slide
without rasterizing an entire book. Like `inspect`, it degrades honestly: with
no PyMuPDF available it exits 5 with `RK_PYMUPDF_MISSING` rather than
claiming a visual check it did not perform.
