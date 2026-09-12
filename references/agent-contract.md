# Agent contract, diagnostics, and trusted build boundary

ReportKit 1.9 exposes its host-neutral interface through the `reportkit` CLI.
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

Contract schema `1.1.0` describes only the combinations that ship today:
`technical-report/{default,technical}/paged` and
`equity-research/institutional-research/paged`. Theme entries expose semantic
capability names, not visual values; `technical` resolves to the same
implementation as `default`. English with Latin script is verified;
Vietnamese is metadata-only pending the i18n phase, and RTL is unsupported.

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
dates and TeX metadata use the fixed `SOURCE_DATE_EPOCH`. Pixel output is the
release gate; ReportKit does not promise byte-identical PDF files in v1.9.

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

Validated Markdown/IR authoring, first-class render/inspect authoring commands,
context-token budgets, broader i18n, slide accessibility parity, and a second
host adapter remain deferred until the companion renderer reaches Phase B.
