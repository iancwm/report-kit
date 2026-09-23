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
reportkit context --slice quickstart --json
reportkit context --publication-type equity-research \
  --theme institutional-research --kind callout --kind chart --json
reportkit context --schema context
reportkit context --schema context-slice
reportkit context --schema diagnostic
reportkit docs --check --json
```

Contract version `1.1.0` describes the combinations registered today:
`technical-report/{default,technical}/paged`,
`equity-research/institutional-research/paged`, and the experimental
`presentation/executive/slides` target. Theme entries expose semantic
capability names, not visual values; `technical` resolves to the same
implementation as `default`. English with Latin script is verified;
Vietnamese is metadata-only, and RTL is unsupported.

### Language and script support

Each Python `Theme` declares `script_coverage`: verified and metadata-only
ISO 15924 scripts, a per-script font stack (`body`, `heading`, `mono`, in the
order the theme's `.sty` selects them), verified and metadata-only BCP 47
languages, and `rtl: unsupported`. Context publishes it as
`capabilities.themes.*.language_support`; each renderer's
`language_support` declares left-to-right text only, locale typography
loaded for verified languages only, and the missing-glyph policy.
`selection.language_support` is the combined record for the resolved
target. The `selection` slice carries all three; `quickstart` carries only a
one-line summary.

Declare a document language with `language:` in `publication.yaml` (or
`\setreportkitlanguage{TAG}` in the preamble of hand-written TeX). A
verified language (`en`, including regional tags such as `en-GB`) loads
babel's `american` locale. The pinned format has no separate UK hyphenation
patterns. A metadata-only language (`vi`) sets only the PDF catalog
language and warns with `RK_LANGUAGE_METADATA_ONLY`. A right-to-left
language fails with `RK_LANGUAGE_RTL_UNSUPPORTED`. An undeclared language
warns with `RK_LANGUAGE_UNDECLARED`, or fails with `RK_LANGUAGE_UNSUPPORTED`
under `theme.font_policy: strict`. `reportkit check` reports these before
TeX runs, and the TeX core enforces the same rules. Without a declaration
the catalog language stays `en-US` and no locale package loads; the format's
built-in hyphenation is already US English.

`theme.font_policy` applies to every theme. Under `strict`, the engine stops
at the first missing glyph (`\tracinglostchars=3`), so a build fails with a
`missing_glyph` compile diagnostic that no allowlist can suppress. Under
`fallback`, TeX only logs the glyph, and the build-log gate reports a
blocking `missing_glyph` diagnostic unless the project allowlists it.
pdfLaTeX's "Unicode character ... not set up" failure is also classified as
`missing_glyph`.

Hosts with a small context window can request one progressive-disclosure slice
with `context --slice NAME`. The unfiltered payload remains available for
compatibility. `quickstart` is the always-loaded host-neutral slice and is
limited to 2,000 estimated tokens; costs use deterministic
`ceil(utf8_bytes / 4)` accounting. `selection`, `primitives`, `authoring`,
`commands`, and `toolchain` are on-demand slices, and the full payload exposes
their estimated costs under `context_budget`.

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
build directory, with restricted output (`openout_any=p`), a 120-second
wall-clock limit, and a 2 GiB child address-space limit. LuaLaTeX uses
`openin_any=a` because the pinned `luaotfload` Unicode loader reads its
installed `ScriptExtensions.txt` and `Scripts.txt` through Lua's file API;
the Markdown path remains raw-TeX-disabled, fragment paths are validated, and
direct `.tex` input is the explicit trusted escape hatch. pdfTeX keeps the
paranoid input policy. CLI flags and the trusted `REPORTKIT_COMPILE_TIMEOUT_SECONDS` /
`REPORTKIT_MEMORY_LIMIT_MB` environment variables may change those resource
limits; publication YAML cannot. If the host cannot enforce the memory limit,
the build exits as an environment failure instead of silently weakening it.

Validated Markdown/IR authoring, slide accessibility parity, the standalone
visual feedback loop, progressive-disclosure context slices, and the OpenAI-
style CLI adapter are implemented in the current tree.
`reportkit render` supports page/range and DPI controls, atomically writes
selected page images, emits `pages.json` with the rendered-page list and
toolchain fingerprint, and returns `RK_PYMUPDF_MISSING` when the environment
cannot render. Broader i18n and tagged-PDF work remain deferred; the OpenAI
adapter is generated from the stable CLI contract and does not read this file.
The slide parity claim is non-tagged: metadata, catalog
language, outline/bookmarks, meaningful links, and diagram `/ActualText` are
gated, while tagged PDF remains unsupported pending the separate
`DocumentMetadata` tagging spike.
