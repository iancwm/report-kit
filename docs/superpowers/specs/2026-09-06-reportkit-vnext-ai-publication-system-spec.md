# ReportKit vNext — AI Publication System

**Status:** Draft / roadmap, not started. Substantial overlap with the
tooling-hardening spec (vNext §7–8 ≈ tooling D6, §9 ≈ tooling D4, §12 ≈
tooling C2 plus `SKILL.md`'s primitive table) — reconcile the two before
starting Phase 1.
**Last updated:** 2026-09-07

## Objective

Evolve the existing ReportKit repository from an AI-assisted LaTeX publishing workflow into a reusable **AI publication system** capable of turning large collections of raw AI output, notes, links, tables, and source material into coherent, visually polished, publication-ready long-form documents.

Assume the existing repository already:

- contains working `.cls` / `.sty` publication styling;
- has successfully compiled a large data-engineering book;
- supports figures, tables, diagrams, and normal LaTeX compilation;
- can already be operated by coding agents.

Do not redesign working functionality unless required.

The priority is to add a stable orchestration and QA layer around what already exists.

---

# 1. Core Architecture

Separate the system into three concerns:

```text
AI Publication Skill
    ↓
ReportKit Python CLI / orchestration layer
    ↓
Existing LaTeX + visualization toolchain
```

Responsibilities:

**AI skill**
- ingest source material;
- plan document structure;
- synthesize/rewrite content;
- choose visuals;
- preserve useful links and citations;
- run the publication workflow;
- interpret diagnostics;
- revise until acceptable.

**Python layer**
- expose deterministic commands;
- validate inputs;
- invoke existing tooling;
- parse build output;
- inspect generated PDFs;
- provide structured machine-readable diagnostics.

**LaTeX layer**
- typography;
- layout;
- figure/table appearance;
- reusable semantic environments;
- final PDF generation.

---

# 2. Add a Stable CLI

Create a Python CLI, preferably using Typer.

Minimum commands:

```bash
reportkit doctor
reportkit context
reportkit build
reportkit build --chapter <id>
reportkit check
reportkit diagnose
reportkit inspect
reportkit package
```

Also support machine-readable output where appropriate:

```bash
reportkit context --json
reportkit diagnose --json
reportkit check --json
```

Agents should normally interact with ReportKit through this CLI rather than calling LaTeX tools directly.

---

# 3. `reportkit context`

Add a self-description command so an AI agent can discover repository capabilities without reading the entire codebase.

Example output:

```yaml
version: 0.x

document:
  engine: lualatex
  main: src/book.tex

components:
  figures:
    - architecture
    - process-flow
    - timeline
    - matrix
  tables:
    - comparison
    - longtable
  callouts:
    - note
    - warning
    - definition

commands:
  build: reportkit build
  check: reportkit check
  diagnose: reportkit diagnose
  inspect: reportkit inspect
```

Generate this from actual configuration where possible rather than maintaining duplicate documentation manually.

---

# 4. Publication Configuration

Introduce or normalize a central configuration file:

```text
publication.yaml
```

Minimum fields:

```yaml
publication:
  title:
  subtitle:
  author:
  language:

document:
  main:
  class:
  engine:

profiles:
  draft:
  release:

validation:
  fail_on_undefined_refs:
  fail_on_missing_assets:
  overfull_hbox_threshold:

output:
  directory:
```

Validate using Pydantic.

Do not move styling configuration out of LaTeX unless there is a strong reason.

---

# 5. Structured Diagnostics

Parse existing LaTeX/build logs into structured diagnostics.

Minimum categories:

```text
latex_error
undefined_reference
undefined_citation
duplicate_label
missing_asset
missing_font
missing_glyph
overfull_hbox
underfull_hbox
bibliography_warning
package_warning
```

Example:

```json
{
  "severity": "warning",
  "type": "overfull_hbox",
  "file": "src/chapters/07-streaming.tex",
  "line": 381,
  "amount_pt": 8.4,
  "message": "Overfull hbox"
}
```

`reportkit diagnose` should provide readable output.

`reportkit diagnose --json` should be optimized for AI-agent consumption.

Where practical, classify issues by likely ownership:

```text
CONTENT
STYLE
ASSET
BUILD
TOOLCHAIN
```

---

# 6. Chapter-Level Builds

Support isolated compilation of a chapter or logical section:

```bash
reportkit build --chapter streaming
```

The build should reuse the global preamble/style while minimizing unnecessary compilation.

Purpose:

- shorten agent iteration cycles;
- make visual review easier;
- avoid rebuilding an entire book for small changes.

---

# 7. PDF Inspection

Use PyMuPDF or equivalent to inspect the generated PDF.

Minimum checks:

- page count;
- page dimensions;
- unexpected blank pages;
- links;
- bookmarks;
- basic font metadata;
- suspicious page geometry;
- text or objects outside expected page bounds.

Expose through:

```bash
reportkit inspect
reportkit inspect --json
```

---

# 8. Page Rendering and Visual QA

Add deterministic PDF-to-image rendering.

Support:

```bash
reportkit inspect --render
reportkit inspect --pages 20-30
```

Generate:

```text
build/pages/
build/contact-sheets/
```

Include a contact-sheet mode for rapidly inspecting long documents.

Initial visual heuristics should stay simple:

- almost-empty page;
- content near/outside margins;
- large unexplained whitespace;
- clipped object;
- suspicious figure/table sizing.

Do not attempt complex computer-vision layout intelligence in the first implementation.

---

# 9. Build Manifest

Every release build should produce:

```text
dist/manifest.json
```

Include:

```json
{
  "version": "...",
  "commit": "...",
  "profile": "release",
  "timestamp": "...",
  "pages": 0,
  "figures": 0,
  "tables": 0,
  "warnings": 0,
  "errors": 0,
  "pdf_sha256": "..."
}
```

This provides provenance and allows build-to-build comparison.

---

# 10. Source/Manuscript Model

Introduce a lightweight intermediate content model for large AI-generated inputs.

Do not attempt a complete AST initially.

Minimum entities:

```yaml
sources:
  source_001:
    type: ai_output
    title:
    file:
    links: []

chapters:
  - id:
    title:
    purpose:
    sources: []
    sections: []
    visual_plan: []
```

Primary purposes:

- preserve provenance;
- plan document structure before writing LaTeX;
- track which input material contributed to which chapter;
- support future updates without rereading the entire corpus.

The final written content may remain as normal `.tex` chapter files.

---

# 11. Link Registry

Add optional centralized management for useful URLs found in source material.

Example:

```yaml
links:
  kafka_docs:
    url: https://...
    label: Apache Kafka documentation
    type: documentation
```

Support semantic rendering from LaTeX where useful.

Classify links as:

```text
citation
documentation
repository
dataset
further_reading
interactive_resource
```

Do not expose raw URLs unnecessarily in running prose.

---

# 12. Visualization Registry

Provide a discoverable list of existing visualization primitives.

The system should distinguish semantic visual types such as:

```text
architecture
process-flow
sequence
timeline
hierarchy
matrix
comparison
quantitative-chart
table
```

Agents should choose a semantic type; ReportKit should control presentation.

Do not allow routine agent-generated local formatting hacks.

If a repeated visual pattern is needed, promote it into a reusable ReportKit primitive.

---

# 13. Publication Skill

Add a canonical skill file, e.g.:

```text
skills/publication/SKILL.md
```

Keep it concise.

Workflow:

1. inspect `reportkit context`;
2. inventory supplied material;
3. create/update manuscript structure;
4. deduplicate and synthesize source material;
5. establish chapter briefs;
6. write publication-quality prose;
7. identify sections where visuals materially improve comprehension;
8. use existing ReportKit visual/table primitives;
9. preserve useful citations and links;
10. build draft;
11. read structured diagnostics;
12. fix root causes rather than local formatting symptoms;
13. inspect affected PDF pages;
14. iterate;
15. run release build;
16. return final PDF and QA status.

Key editorial instruction:

> Treat supplied AI output as research material, not publication-ready prose. Synthesize rather than concatenate.

The skill should be platform-neutral enough to operate in Claude Cowork, Claude Code, ChatGPT Work, or equivalent agent environments.

---

# 14. Agent Guardrails

Document these explicitly:

- Do not bypass `.cls` / `.sty` conventions.
- Do not introduce arbitrary font sizes, spacing, or manual geometry into chapter files.
- Do not create one-off repair scripts for recurring problems.
- Do not invoke LuaLaTeX/Biber directly unless debugging ReportKit itself.
- Prefer semantic environments and reusable primitives.
- Fix systemic formatting problems in shared tooling.
- Do not invent citations.
- Do not preserve redundant AI-generated prose merely because it was supplied.

---

# 15. Build History

Store machine-readable results:

```text
build/history/<build-id>.json
```

Record:

- diagnostics;
- build duration;
- page count;
- figure/table counts;
- relevant tool versions.

Add later command:

```bash
reportkit analyse-history
```

Purpose:

- detect recurring errors;
- identify repeated manual fixes;
- suggest candidates for new tooling or abstractions.

This is lower priority than the CLI, diagnostics, and PDF inspection.

---

# 16. Implementation Priority

## Phase 1 — Agent Interface

Implement first:

1. Python CLI
2. `publication.yaml`
3. `reportkit context`
4. structured diagnostics
5. chapter builds
6. release manifest

This creates the stable machine interface.

## Phase 2 — Publication QA

Then:

7. PDF inspection
8. page rendering
9. contact sheets
10. basic visual heuristics
11. asset validation

## Phase 3 — AI Authoring

Then:

12. manuscript/source model
13. link registry
14. visualization registry
15. canonical publication skill

## Phase 4 — Self-Improvement

Finally:

16. build history
17. recurring-diagnostic analysis
18. visual regression testing
19. more sophisticated publication linting

---

# 17. Definition of Done

A fresh AI agent with repository access and a collection of AI-generated research files should be able to receive:

> Turn these materials into a coherent technical publication using ReportKit. Add useful visualizations, preserve relevant links, and produce a release-quality PDF.

Without prior knowledge of repository internals, the agent should be able to:

```text
discover ReportKit capabilities
        ↓
structure the source material
        ↓
author/rewrite the manuscript
        ↓
select existing visual primitives
        ↓
build chapters iteratively
        ↓
consume structured diagnostics
        ↓
inspect rendered output
        ↓
correct content/layout issues
        ↓
produce release build
        ↓
return PDF + QA manifest
```

The vNext implementation is successful when the repo behaves less like a LaTeX template collection and more like a **deterministic publication backend that an AI authoring agent can operate reliably**.