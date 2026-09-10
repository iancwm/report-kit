# ReportKit — Agent Interface & Platform Contract

**Status:** Draft / not started. Companion to
[2026-09-09-reportkit-multi-format-publication-architecture-spec.md](2026-09-09-reportkit-multi-format-publication-architecture-spec.md)
(the "renderer spec"), which it amends in [§18](#18-amendments-to-the-renderer-spec).
**Last updated:** 2026-09-10
**Current-state claims:** verified against the working tree at `2587e03`
(see [Current state](#1-current-state-verified-2026-09-10)). Every premise
carries a `file:line` anchor.
**Priority:** P2 — [§3](#3-the-capability-contract), [§5](#5-documentation-derivation-and-drift)
and [§8](#8-reproducibility-and-toolchain-pinning) are Phase A work in the
renderer spec's sequencing; the rest follows.

---

## Framing: two specs, two questions

The renderer spec answers **"what can ReportKit render, and how is that
organized?"** It is sound and this document does not relitigate it.

This spec answers a different question:

> **How does an AI agent — not necessarily Claude — discover ReportKit's
> capabilities, drive them correctly on the first attempt, and recover
> structurally when it fails?**

The renderer spec touches this once, at its §17, and the instruction is to
update `SKILL.md` prose. That is the right answer for a Claude Code skill and
the wrong answer for a vendor-agnostic platform. Prose is a contract only a
model with a large context window and strong instruction-following can honor.
A platform contract has to be **data**: discoverable, typed, versioned, and
machine-checkable.

The distinction that organizes this document:

| Concern | Owner |
| --- | --- |
| What exists and how it renders | renderer spec |
| How a caller learns what exists | this spec |
| How a caller expresses intent | this spec |
| How a caller learns it was wrong | this spec |
| How a caller reproduces a result | this spec |

### Why now, not after the new themes

The renderer spec's own argument applies with more force here. It sequences
architecture hardening ahead of executive/venture/editorial because retrofitting
an abstraction across five themes is more expensive than across two. The
contract surface has the same shape: today there are 10 callouts, ~20 figure
environments and 11 charts to describe. After the renderer spec lands there are
also six publication types, five themes, two renderers and a slide composition
set. Deriving a machine-readable contract from 40 primitives is a regex change;
deriving it from 100 across two renderers, after the prose has already been
written by hand three more times, is a project.

[§3](#3-the-capability-contract), [§5](#5-documentation-derivation-and-drift)
and [§8](#8-reproducibility-and-toolchain-pinning) therefore belong in the
renderer spec's **Phase A**, not after Phase F.

---

## 1. Current state (verified 2026-09-10)

### 1.1 Foundations that already exist — do not rebuild

ReportKit is further along than a greenfield agent-interface project. These are
real and should be extended, not replaced:

| Capability | Location | Assessment |
| --- | --- | --- |
| Machine-readable self-description | `python_scripts/reportkit/context.py`, `reportkit context --json` | Strong. Most comparable tools have nothing. |
| Typed build diagnostics | `python_scripts/reportkit/diagnostics.py` — 12 categories in `DIAGNOSTIC_TYPES` | Strong; needs remediation data ([§7](#7-unified-diagnostic-contract)). |
| Docs-vs-code drift detection | `registry.py:check_skill_drift()` | Right idea, narrow coverage ([§5](#5-documentation-derivation-and-drift)). |
| JSON output on every command | `cli.py` — `--json` on `doctor`/`context`/`check`/`diagnose`/`inspect`/`package`/`analyse-history` | Strong and consistent. |
| Static pre-compile validation | `publication_pipeline/scripts/publication_validation.py` | Exists; untyped output and wrong scope ([§6](#6-the-authoring-contract), [§7](#7-unified-diagnostic-contract)). |
| PDF page rendering + contact sheet | `publication_pipeline/scripts/render_pdf_pages.py` | Exists; framed as CI-only ([§12](#12-agent-visual-feedback-loop)). |
| Diagram alt-text in the PDF | `reportkit-diagrams.sty:91-116` — `/Span << /ActualText >>` | Above average for a LaTeX toolkit. |
| Document language in the catalog | `reportkit-core.sty:36-60` | Present; the only i18n that ships ([§13](#13-internationalization)). |
| Reasoned accessibility deferral | `references/accessibility-tagging.md` | A documented no-go with a named blocker, not neglect ([§14](#14-accessibility)). |

### 1.2 Verified premises

| Premise | Verified at |
| --- | --- |
| Capability discovery emits primitive **names only** | `reportkit context --json` → `components.figures` is a flat list of strings |
| The extractor discards the argument spec | `registry.py:29` — `re.findall(r"\\NewDocumentEnvironment\{([^}]+)\}", text)`, one capture group |
| Argument specs are present and adjacent in the source | `reportkit-boxes.sty` — `\NewDocumentEnvironment{principle}{m}`; `reportkit-structure.sty` — `\NewDocumentEnvironment{reportmatrix}{O{}...` |
| Drift detection compares name sets only | `registry.py:check_skill_drift()` — set equality on figures and callouts |
| The skill entry point carries vendor-specific frontmatter | `SKILL.md:1-4` — `---\nname: reportkit\ndescription: …\n---` |
| Documentation budget today | `SKILL.md` 17,668 bytes + `references/*.md` 27,428 bytes = ~45 KB for two themes |
| A second, untyped error channel exists | `publication_validation.py:17` — `ValidationResult.errors: list[str]` (plain strings) |
| Typed diagnostics carry no remediation field | `diagnostics.py:192-201` — records are `{type, file, line, message, log_line}` |
| `context` takes no filter arguments | `cli.py:286-289` — only `--json` and `--profile` |
| No shell-escape is enabled anywhere | grep for `shell-escape`/`shell_escape` across `publication_pipeline/scripts/*.py` and `scripts/*.sh` returns nothing |
| Language support is a PDF catalog entry only | `reportkit-core.sty:36-60`; no `babel`/`polyglossia` in core or either theme |
| Tagged PDF is an explicit, blocked no-go | `references/accessibility-tagging.md` — `LaTeX Error: No support files for \DocumentMetadata found.` |

### 1.3 The one-line diagnosis

```python
# registry.py:29 — the name is captured; the signature, one brace group later,
# is thrown away.
re.findall(r"\\NewDocumentEnvironment\{([^}]+)\}", text)
```

An agent can discover that `reportmatrix` exists. It cannot discover how to
call it. The only place that knowledge lives is `SKILL.md` prose, behind
Claude-skill frontmatter. **That is the vendor lock**, and it is one regex wide.

---

## 2. Normative vocabulary

| Term | Meaning |
| --- | --- |
| **Agent** | Any LLM-driven caller. Assume no Claude-specific capability, a smaller context window than Claude's, and weaker instruction-following. |
| **Host** | The runtime the agent lives in (Claude Code, an OpenAI Assistant, a local harness, CI). |
| **Skill package** | The vendor-specific wrapper that introduces ReportKit to one host. `SKILL.md` is the Claude instance. |
| **Contract surface** | Everything an agent may rely on: `reportkit context` output, CLI flags and exit codes, the diagnostic record schema, the authoring IR schema. Changes here are breaking changes ([§9](#9-stability-and-versioning-policy)). |
| **Prose guidance** | Editorial advice with no machine-checkable meaning ("write for the decision"). Legitimately lives in Markdown; never load-bearing for correctness. |

**The load-bearing rule:** if getting it wrong produces a broken build, it
belongs in the contract surface. If getting it wrong produces a worse report, it
may stay prose.

---

## 3. The capability contract

`reportkit context --json` becomes the single authoritative entry point. An
agent that has read `context` output must have everything it needs to author a
valid document without reading any Markdown.

### 3.1 Required additions

Per primitive (callout, figure environment, chart function, and — once the
renderer spec lands — publication type, theme, renderer, slide composition):

| Field | Purpose |
| --- | --- |
| `name` | already present |
| `kind` | `callout` / `figure` / `chart` / `composition` |
| `signature` | argument spec, normalized from xparse ([§4](#4-primitive-signature-extraction)) |
| `arity` | `{required: n, optional: n}` |
| `arguments[]` | per-argument `name`, `type`, `required`, `description`, `default` |
| `constraints` | machine-checkable limits — e.g. `exhibitgrid` column-count ceiling, the `researchmain`/`researchsidebar` adjacency rule, both currently prose-only in `references/institutional-research-theme.md` |
| `example` | one canonical, compilable snippet |
| `available_in` | publication types / themes / renderers where valid |
| `stability` | `stable` / `experimental` / `deprecated` ([§9](#9-stability-and-versioning-policy)) |
| `since` | version introduced |

### 3.2 Requirements

- The contract is **generated from source**, never hand-maintained. A primitive
  that exists in `.sty` but carries no contract metadata fails CI.
- `context` gains filters — at minimum `--publication-type`, `--theme`,
  `--kind` — so an agent can request only what applies ([§11](#11-progressive-disclosure-and-context-budget)).
- The output is a versioned, published JSON Schema. `context --schema` prints it.
- Every field is either derived from source or declared beside the definition it
  documents; nothing lives only in `SKILL.md`.

### 3.3 Acceptance

An agent given **only** `reportkit context --json` output, with no access to
`SKILL.md` or `references/`, can author a document that compiles and uses at
least one callout, one diagram and one chart correctly on the first attempt.

---

## 4. Primitive signature extraction

The mechanical half of [§3](#3-the-capability-contract), separated because it is
small, unblocks everything else, and should land first.

`registry.py:29` captures one group. The xparse argument spec is the next brace
group. Extend the extractor to capture and normalize it:

| Source | Normalized |
| --- | --- |
| `\NewDocumentEnvironment{principle}{m}` | 1 required, 0 optional |
| `\NewDocumentEnvironment{reportmatrix}{O{}...` | leading optional with default, then mandatories |

**Requirements:**

- Handle the xparse specifiers actually used in the tree — `m`, `O{…}`, `o`,
  `s`, and any others present. Enumerate them from source rather than assuming.
- Cover `\NewDocumentCommand` too, not only environments; commands like
  `\RKLink` are equally part of the surface.
- Argument *names* and *descriptions* cannot be derived from xparse. Declare
  them in a structured comment beside each definition, and parse that — keeping
  documentation adjacent to the code it documents, which is what makes
  [§5](#5-documentation-derivation-and-drift) enforceable.
- Where the tree already documents a constraint in prose (`exhibitgrid` column
  ceiling, `researchmain`/`researchsidebar` adjacency), move it into the
  declaration and have `references/institutional-research-theme.md` render from
  it.

---

## 5. Documentation derivation and drift

`check_skill_drift()` compares name sets. Usage prose is unchecked and can rot
silently. The renderer spec multiplies documented combinations by five themes ×
six publication types, so prose grows combinatorially against a check that only
sees identifiers.

**Requirements:**

- Extend drift detection from names to the full contract: signature, arity,
  constraints and stability must match between contract and docs.
- Generate the reference sections of `SKILL.md` and `references/*.md` from the
  contract rather than hand-writing them. Editorial prose stays hand-written;
  primitive tables do not.
- Every documented example must compile. A snippet in the contract that fails to
  build is a CI failure — this is the check that prevents the most common
  agent-visible defect, a documented call that does not work.
- CI fails on drift. It must not be advisory.

---

## 6. The authoring contract

**The largest gap, and the one the renderer spec is entirely silent on.**

Today an agent authors by emitting LaTeX (`report.tex`) or Markdown into
`manuscript/`. Nothing validates *primitive usage* before `lualatex` runs:
`validate_publication()` checks the manuscript/fragment/label contract, not
whether `\begin{reportmatrix}` was given the right number of arguments.

For an LLM — especially a smaller, non-Claude one — raw LaTeX generation is the
dominant failure mode: wrong arity, invented environments, unbalanced braces,
misused optional arguments. Each costs a full compile cycle and returns a TeX
error whose relationship to the mistake is often obscure.

### 6.1 Requirement

Introduce a validated authoring representation between agent output and TeX.
Either shape is acceptable:

- **Structured IR** — JSON/YAML document tree validated against the contract
  schema, from which TeX is generated; or
- **Constrained Markdown dialect** — the existing manuscript pipeline plus a
  declared block/directive syntax for primitives, validated before conversion.

The second is the smaller change and reuses the existing pipeline. The choice is
[open question 2](#21-open-questions).

**Non-negotiable properties:**

- Validation runs **without invoking TeX** and returns in well under a second.
- Every error is a structured diagnostic ([§7](#7-unified-diagnostic-contract))
  pointing at the agent's own source location, not a `.tex` line number.
- Unknown primitive → error naming the closest valid alternatives.
- Wrong arity → error stating expected versus supplied.
- Escaping of content-derived strings is handled by the generator, not the agent
  ([§10](#10-security-posture)).
- Raw LaTeX remains available as an escape hatch. This is additive; hand-written
  `.tex` must keep working, per the renderer spec's §19.

### 6.2 Acceptance

An agent that emits a document with three deliberate primitive-usage errors
receives all three, structurally, in one sub-second validation pass, with no TeX
invocation.

---

## 7. Unified diagnostic contract

ReportKit already has **two** error channels with different shapes:

- `diagnostics.py:192-201` — typed records, `{type, file, line, message, log_line}`,
  12 categories.
- `publication_validation.py:17` — `ValidationResult.errors: list[str]`, plain
  strings.

The renderer spec's §18 adds more checks (font resolution, theme/publication
compatibility, palette synchronization, canvas dimensions, default-theme
leakage) without saying which channel they use — so the default outcome is a
third shape.

### 7.1 Requirements

- **One diagnostic record schema** across static validation, IR validation,
  build-log parsing, PDF inspection and every check the renderer spec adds.
- Extend `DIAGNOSTIC_TYPES` to cover the new categories rather than inventing a
  parallel taxonomy.
- Every record gains:

| Field | Purpose |
| --- | --- |
| `severity` | `error` / `warning` / `info` |
| `remediation` | what to actually do, as text an agent can act on |
| `primitive` | which primitive or config key caused it, where attributable |
| `source` | the agent's own file/line where the IR supports it |
| `docs` | contract pointer for the relevant primitive |

- Where a name was not recognized, include candidate suggestions. Most agent
  errors are near-misses; "did you mean" resolves them without a second build.
- Stable machine-readable error codes, versioned with the contract
  ([§9](#9-stability-and-versioning-policy)).
- Exit codes are documented and stable — distinguishing config error, validation
  failure, compile failure and environment failure, so a caller can branch
  without parsing text.

**Rationale:** a vendor-agnostic platform must assume a weaker model than
Claude. The remediation has to be in the error, not inferred from it.

---

## 8. Reproducibility and toolchain pinning

The renderer spec's Phase A requires "establish a working `lualatex` compile
environment". It does not require **pinning** one. Its §18 then leans on
pixel-diff visual regression across five fixtures.

Unpinned pixel-diff baselines are not a test. A different TeX Live year, font
version, or `pymupdf` build changes rendering enough to fail a diff for reasons
unrelated to any change — the classic outcome is a team that reflexively accepts
new baselines, which the renderer spec's own §18 warns is indistinguishable from
having no test.

**Requirements:**

- Pin and record: TeX Live version, the package set, font versions, Python and
  library versions, renderer DPI.
- Ship a reproducible build environment (container image with a recorded digest,
  or an equivalently exact lockfile).
- `reportkit context` reports the resolved toolchain identity; `reportkit doctor`
  reports drift from the pinned set.
- Visual baselines record the toolchain that produced them. A diff run against a
  different toolchain reports *toolchain mismatch*, not *visual regression* —
  distinguishing "the design changed" from "the machine changed".
- Builds are byte-reproducible given identical inputs and toolchain, or the
  sources of nondeterminism (timestamps, `/ID`) are explicitly neutralized.

---

## 9. Stability and versioning policy

`context` reports `class_version` and a `git describe`, and `context.py:53`
already warns when the two disagree — good. But nothing states which parts of
the surface are stable, and nothing governs removal.

An agent prompted or fine-tuned against v1.8 has no way to discover that a
primitive it relies on is deprecated in v2.

**Requirements:**

- Every contract element carries `stability` and `since`
  ([§3](#3-the-capability-contract)).
- A published semver policy for the **contract surface** as defined in
  [§2](#2-normative-vocabulary): what may change in a patch, minor and major
  release.
- Deprecation is a documented lifecycle — marked `deprecated` in the contract,
  emitting a `deprecated_primitive` diagnostic, for at least one minor release
  before removal.
- `context` output is itself versioned, so a caller can detect a schema it does
  not understand rather than misparsing it.
- The renderer spec's §19 backward-compatibility guarantee is restated as
  policy, not as a one-time promise about today's primitives.

---

## 10. Security posture

Currently unstated in both specs. I verified that **no shell-escape is enabled
anywhere** in the pipeline — the posture is good by default and undocumented,
which means nothing prevents it from regressing.

This matters more the moment an agent generates TeX, and more again if any
publication content originates from an untrusted source (scraped text, user
input, tool output).

**Requirements:**

- Shell-escape stays disabled. State it, and add a CI check asserting no
  invocation path enables it.
- Compiles run under a wall-clock timeout and memory cap. A malformed document
  can loop indefinitely; an agent iterating unattended will hit this.
- Constrain filesystem reach: `\input`/`\include`/`\includegraphics` resolve
  only within the publication root and the templates directory. `TEXINPUTS` is
  already scoped at `publication_build.py:346` — make that a stated guarantee
  with a test.
- The [§6](#6-the-authoring-contract) generator owns escaping of all
  content-derived strings. An agent must never be responsible for escaping, and
  the IR must make injection of raw TeX through content fields impossible except
  via the explicit escape hatch.
- Document the trust boundary: what ReportKit assumes about manuscript
  provenance, and what a caller must sanitize itself.

---

## 11. Progressive disclosure and context budget

~45 KB of documentation covers two themes and one renderer today. The renderer
spec adds three themes, four publication types, a second renderer and a slide
composition set. Linear growth alone lands well past what a small-context model
can hold alongside the actual authoring task — and `context` currently returns
everything, unconditionally.

**Requirements:**

- Layer the documentation: a small always-loaded core (choosing a publication
  type, the build loop, the error loop) with everything else fetched on demand.
- `context` filters ([§3.2](#32-requirements)) so a presentation author
  retrieves slide compositions and its theme's tokens, not the equity-research
  primitive set.
- Publish an approximate token cost per contract slice, so a host can budget.
- Set and enforce a ceiling on the always-loaded core. Without a number this
  regresses on every feature.
- The renderer spec's §17 decision gate becomes **data in the contract**, not
  prose in `SKILL.md`: publication types with selection criteria and compatible
  themes, so any agent can execute the decision without the prose version.

---

## 12. Agent visual feedback loop

`render_pdf_pages.py` already renders pages to PNG with a contact sheet and
manifest — but both specs frame rendering as a *test* concern. The renderer
spec's §18 uses it for regression baselines only.

Most current models across vendors are multimodal. An agent that can look at
what it produced catches overfull lines, collided diagram labels, bad page
breaks and broken slide composition — the failures that compile cleanly and are
invisible in the log. The equity fixture's own history is the evidence: per the
institutional plan, actually rendering the charts is what caught a real
`risk_reward_chart()` label-overlap bug.

**Requirements:**

- Make render-and-inspect a **documented authoring step**, not just CI
  machinery: a first-class command with page selection, resolution control and
  predictable output paths.
- Cheap page-range rendering, so an agent can inspect one slide without
  rasterizing a book.
- Document the loop explicitly in the skill package: build → render → inspect →
  revise.
- Degrade honestly when the environment cannot render (no PyMuPDF, no TeX),
  consistent with `bootstrap.sh`'s existing `MODE:` contract — an agent must
  never claim a visual check it did not perform.

---

## 13. Internationalization

`\rk@language` sets the PDF catalog language and nothing else. There is no
`babel` or `polyglossia` in core or in either theme. A Vietnamese fixture
already ships (`latex_templates/examples/career_guide_vi/`), so this is a live
concern rather than a hypothetical.

The renderer spec's §11 requires each theme to declare fonts and a math
strategy, but says nothing about **scripts**. The editorial theme's preference
for serif body text makes this concrete: a serif stack chosen for Latin text
will not cover CJK, Arabic or Devanagari, and the failure is silent — missing
glyphs, or a fallback that ruins the design the theme exists to provide.

**Requirements:**

- Extend the renderer spec's §9 theme token contract with a declared script
  coverage set per theme, and per-script font stacks where coverage extends
  beyond Latin.
- Hyphenation and locale-aware typography (quotation marks, spacing conventions)
  for supported languages.
- Missing-glyph detection is already a `DIAGNOSTIC_TYPES` category — make it a
  hard failure under the renderer spec's §11 `font_policy: strict`, not a log
  line.
- `context` reports supported languages and scripts per theme, so an agent can
  select a compatible theme instead of discovering incompatibility at compile
  time — the same fail-early principle the renderer spec applies to
  theme×publication-type pairs.
- RTL is explicitly **out of scope** unless a real publication needs it. Declare
  it unsupported rather than leaving it undefined.

---

## 14. Accessibility

`references/accessibility-tagging.md` records a time-boxed spike that
returned a documented no-go, blocked by a real environment limitation
(`No support files for \DocumentMetadata found.`). That is a well-reasoned
deferral. What ships — PDF metadata, catalog language, bookmarks, meaningful
link text, diagram `/ActualText` alternatives — is above average for a LaTeX
toolkit.

The gap is not the deferral. It is that neither spec **protects** what ships.

**Requirements:**

- The slide renderer must preserve the accessibility features the paged renderer
  already provides — metadata, language, bookmarks/outline, link text, diagram
  alternatives. Beamer is notorious for breaking document structure; without an
  explicit requirement this regresses silently.
- Treat the shipped features as a release gate with automated checks, not as
  incidental behavior. The diagram alt-text path is already unit-tested
  (`tests/test_diagram_alttext.py`); extend that posture to the rest.
- Re-run the tagging spike once [§8](#8-reproducibility-and-toolchain-pinning)
  pins a modern TeX Live — the recorded blocker is a stale format, and pinning
  is likely to remove it. Tie the two work items together explicitly so the
  spike is not forgotten.
- `context` reports the accessibility level actually achieved per renderer, so
  an agent can state it honestly rather than guessing.

---

## 15. Renderer interface neutrality

The renderer spec's §21 lists "automatic responsive HTML rendering" as a
non-goal. As a scope decision for this phase that is correct and this spec does
not challenge it.

The concern is narrower: the renderer abstraction is being designed **now**, and
is specified as `paged | slides` with LaTeX assumed throughout. If the renderer
interface is defined in LaTeX terms, a future HTML or EPUB renderer is not a new
implementation of an existing interface — it is a re-architecture.

**Requirement:** define the renderer interface in terms of *what a renderer must
provide* (resolve a publication type's structure, apply theme tokens, place
figures, emit output, report diagnostics) rather than *how LaTeX provides it*.

**This is not a request to build an HTML renderer.** It is a request that
choosing not to build one costs nothing later. The test is a documented
interface a hypothetical non-TeX renderer could satisfy without changing the
publication types or the theme token contract.

---

## 16. Vendor-agnostic skill packaging

`SKILL.md:1-4` carries Claude-skill frontmatter. That file is a legitimate,
well-formed Claude Code skill and should stay one.

The problem is that it is also the **only** description of how to use ReportKit.
A second host has nothing to bind to but a Claude-shaped artifact.

**Requirements:**

- Separate host-neutral guidance from host-specific packaging. The neutral layer
  is the contract ([§3](#3-the-capability-contract)) plus prose that names no
  vendor and assumes no host capability.
- `SKILL.md` becomes a thin Claude Code adapter over the neutral layer:
  frontmatter, host-specific workflow, and pointers into the contract.
- Generate the primitive reference sections rather than hand-writing them
  ([§5](#5-documentation-derivation-and-drift)), so adapters cannot drift from
  each other.
- Provide at least one non-Claude reference adapter — an OpenAI tool-definition
  set, an MCP server, or a plain CLI-driven prompt — to prove the neutral layer
  is genuinely sufficient. Without a second consumer, "vendor-agnostic" is
  untested.
- Assume no host-specific affordance. Everything an agent needs is reachable
  through documented CLI commands with stable JSON output and stable exit codes.

---

## 17. Testing

Extending the renderer spec's §18 rather than duplicating it:

| Check | Requirement |
| --- | --- |
| Contract completeness | Every primitive in `.sty` appears in `context` with full metadata; a primitive without it fails CI. |
| Contract examples | Every example in the contract compiles. |
| Schema conformance | `context` output validates against its published schema. |
| Drift | Contract versus generated docs, on the full record, not names. |
| IR validation | Deliberate-error corpus produces expected structured diagnostics, no TeX invoked. |
| Diagnostic uniformity | Every channel emits the shared schema; no `list[str]` errors survive. |
| Remediation coverage | Every `DIAGNOSTIC_TYPES` category has remediation text and a test asserting it. |
| Toolchain pinning | Builds reproduce byte-identically on the pinned image; baselines record their toolchain. |
| Security | No path enables shell-escape; timeout and resource caps enforced; `TEXINPUTS` containment tested. |
| Context budget | Always-loaded core stays under its declared ceiling. |
| Accessibility parity | Slide renderer preserves the paged renderer's shipped accessibility features. |
| Vendor neutrality | The non-Claude reference adapter authors a valid document using only the neutral layer. |

**The headline acceptance test** ([§3.3](#33-acceptance)): an agent with access
to `reportkit context --json` and no Markdown at all authors a compiling
document using a callout, a diagram and a chart, correctly, first try.

---

## 18. Amendments to the renderer spec

Concrete changes this spec asks for in
[2026-09-09-reportkit-multi-format-publication-architecture-spec.md](2026-09-09-reportkit-multi-format-publication-architecture-spec.md):

| Section | Amendment |
| --- | --- |
| §9 (theme token contract) | Add script coverage and per-script font stacks ([§13](#13-internationalization)). |
| §17 (authoring skill) | The decision gate becomes contract data, not `SKILL.md` prose ([§11](#11-progressive-disclosure-and-context-budget)). |
| §18 (testing) | New checks emit through the shared diagnostic schema ([§7](#7-unified-diagnostic-contract)); visual baselines record their toolchain ([§8](#8-reproducibility-and-toolchain-pinning)). |
| §19 (backward compat) | Restate as a versioning **policy** covering future change, not a one-time promise ([§9](#9-stability-and-versioning-policy)). |
| §20 Phase A | Add: signature extraction ([§4](#4-primitive-signature-extraction)), contract-derived docs ([§5](#5-documentation-derivation-and-drift)), toolchain pinning ([§8](#8-reproducibility-and-toolchain-pinning)). |
| §20 Phase B | Slide renderer must preserve accessibility parity ([§14](#14-accessibility)). |
| §21 (non-goals) | Soften "responsive HTML rendering" from *excluded* to *not now, and not foreclosed* ([§15](#15-renderer-interface-neutrality)). |

---

## 19. Implementation phases

Interleaved with the renderer spec's phases rather than sequenced after them.

### Phase A′ — Contract foundations (with renderer Phase A)

1. Signature extraction ([§4](#4-primitive-signature-extraction)) — smallest
   change, unblocks the rest.
2. Contract schema and enriched `context` ([§3](#3-the-capability-contract)).
3. Contract-derived docs and full drift detection ([§5](#5-documentation-derivation-and-drift)).
4. Toolchain pinning ([§8](#8-reproducibility-and-toolchain-pinning)) — a
   prerequisite for the renderer spec's own visual regression.

**Done when:** `context --json` fully describes every existing primitive; docs
generate from it; CI fails on drift; builds reproduce on a pinned image.

### Phase B′ — Diagnostics and security (with renderer Phase B)

5. Unified diagnostic schema with remediation ([§7](#7-unified-diagnostic-contract)).
6. Security posture stated and tested ([§10](#10-security-posture)).
7. Accessibility parity for the slide renderer ([§14](#14-accessibility)).

**Done when:** every channel emits one schema; every category carries
remediation; security properties are asserted by tests.

### Phase C′ — Authoring contract (after renderer Phase B)

8. Authoring IR or constrained dialect ([§6](#6-the-authoring-contract)).
9. Agent visual feedback loop ([§12](#12-agent-visual-feedback-loop)).

**Done when:** an agent authoring three deliberate errors gets all three
structurally, sub-second, with no TeX invoked.

Deferred to after the renderer spec's Phase B so the IR is designed against both
renderers. Designing it against `paged` alone would repeat the coupling mistake
both specs exist to prevent.

### Phase D′ — Neutrality and scale (with renderer Phase E–F)

10. Progressive disclosure and budget ceiling ([§11](#11-progressive-disclosure-and-context-budget)).
11. Neutral layer plus a non-Claude reference adapter ([§16](#16-vendor-agnostic-skill-packaging)).
12. i18n token extensions ([§13](#13-internationalization)).

**Done when:** a non-Claude agent authors a valid publication using only the
neutral layer, within the declared context budget.

---

## 20. Non-goals

- A hosted service, API server or multi-tenant infrastructure.
- Agent orchestration, planning or prompt engineering. ReportKit provides a
  contract; it does not tell agents how to think.
- Fine-tuning, evaluation harnesses or model-specific optimization.
- A WYSIWYG or interactive editor.
- Supporting arbitrary LaTeX. The contract covers ReportKit's primitives; the
  raw escape hatch is unvalidated by design.
- Building an HTML or EPUB renderer ([§15](#15-renderer-interface-neutrality) asks
  only that the interface not foreclose one).
- RTL script support ([§13](#13-internationalization)), until a real publication
  needs it.
- Replacing `SKILL.md`. It stays the Claude Code adapter.

---

## 21. Open questions

1. **Where does contract metadata live?** Structured comments beside each
   `\NewDocumentEnvironment`, a sidecar file per module, or a central manifest?
   Adjacency resists drift best; a manifest is easier to schema-validate. This
   decision shapes [§4](#4-primitive-signature-extraction) and
   [§5](#5-documentation-derivation-and-drift).

2. **IR or constrained Markdown?** ([§6](#6-the-authoring-contract)) Markdown
   reuses the existing manuscript pipeline and is the smaller change; a JSON IR
   is more precisely validatable and easier for a weak model to emit correctly.
   Possibly both, with Markdown as the surface and IR as the intermediate.

3. **Does the contract describe themes deeply, or only name them?** Full theme
   token exposure lets an agent reason about design; it also risks agents
   attempting the styling the renderer spec's §8 deliberately withholds.

4. **How is a stale agent handled?** When an agent's cached contract predates the
   installed version, does the CLI refuse, warn, or attempt compatibility? Ties
   to [§9](#9-stability-and-versioning-policy).

5. **What is the always-loaded budget ceiling?**
   ([§11](#11-progressive-disclosure-and-context-budget)) A number is needed, and
   it depends on the weakest model targeted — which nobody has yet named.

6. **Which non-Claude adapter proves neutrality?**
   ([§16](#16-vendor-agnostic-skill-packaging)) MCP is closest to an emerging
   cross-vendor standard; an OpenAI tool-definition set is more direct; a plain
   CLI prompt is weakest but cheapest.

7. **Does the IR change the repository boundary?**
   `references/repository-boundary.md` keeps content out of this repository. An
   IR schema is engine, IR instances are content — confirm the boundary holds.

8. **Is byte-reproducibility worth its cost?**
   ([§8](#8-reproducibility-and-toolchain-pinning)) Neutralizing PDF timestamps
   and `/ID` is real work. Toolchain pinning alone may deliver most of the
   benefit for visual regression.
