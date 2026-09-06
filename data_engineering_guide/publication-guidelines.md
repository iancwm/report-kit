# Publication Guidelines for the Data Engineering Guide

**Status:** Editorial and production specification

**Scope:** This document describes how to turn `data-engineering-guide.md`
into a readable Markdown-to-LaTeX publication. It is deliberately separate
from the manuscript: the later publication skill can implement these rules
without adding build instructions or production metadata to the teaching text.

## Publication Goals

The publication should feel like a guided technical book rather than a
reference dump. A reader should be able to answer three questions at every
point:

1. What problem is this part of a data system solving?
2. What decision or trade-off does the engineer need to make?
3. What should the reader be able to build, inspect, or explain next?

The visual system should reinforce those questions. Use diagrams to explain
relationships and flow, tables to compare choices, and code to make a concept
concrete. Do not add a figure merely to decorate a page.

## Structural Contract

The manuscript has nine instructional sections followed by a glossary and
references:

```text
# Section 1 - Introduction to Data Engineering
# Section 2 - Data Ingestion
# Section 3 - Data Storage
# Section 4 - Data Transformation and Processing
# Section 5 - Orchestration and Scheduling
# Section 6 - Data Quality and Reliability
# Section 7 - Metadata, Governance, and Serving Data
# Section 8 - Topics in Data Engineering
# Section 9 - A Learning Path and Project Roadmap
# Section 10 - Glossary
# Section 11 - References
```

Use H1 only for these main sections. Use H2 for every topic within a section.
Do not introduce H3 headings into the manuscript. When a smaller distinction
is necessary, use a bold lead-in, a short list, a callout, or a table.

The visible `Section N -` prefix is part of the manuscript's reading structure.
Disable automatic section numbering in Pandoc/LaTeX so that the output does
not display a second number. Stable internal identifiers may be added during
the publication build without changing the visible headings:

```text
Section 1 -> sec:introduction
Section 2 -> sec:ingestion
Section 3 -> sec:storage
Section 4 -> sec:processing
Section 5 -> sec:orchestration
Section 6 -> sec:quality
Section 7 -> sec:governance-serving
Section 8 -> sec:practitioner-topics
Section 9 -> sec:learning-path
Section 10 -> sec:glossary
Section 11 -> sec:references
```

The preface and reader roadmap are front matter. They must not compete with
the numbered section hierarchy in the generated table of contents.

## Reader-Facing Layout

Each main section should follow a recognizable rhythm:

1. A short opening that states the role of the stage in the lifecycle.
2. A small set of key terms and the central design questions.
3. Concepts in increasing depth, with one concrete running example.
4. A concise tool-selection discussion, separated from timeless concepts.
5. A capstone continuation or practical application where relevant.
6. A checklist that lets the reader test their understanding and design.

Keep the first explanation of a term close to its first use. When a concept is
needed earlier than its full treatment, give a one-sentence definition and link
forward to the later discussion.

Use a consistent visual vocabulary:

| Element | Role in the book | Suggested treatment |
| --- | --- | --- |
| Key concept | Definition or mental model | `key-concept` callout |
| Design decision | Choice, constraint, or trade-off | `decision` callout or comparison table |
| Failure mode | What breaks and why | `warning` callout |
| Worked example | Concrete application of an idea | `example` callout |
| Practice | Small action for the reader | `practice` callout |
| End-of-section check | Recall and design prompts | `checklist` callout |

Callouts should be short, have one purpose, and never contain another callout.
They must still read sensibly if a renderer reduces them to a titled
paragraph or block quote.

## Section-by-Section Visual Plan

The following plan is the minimum useful visual set. The publication skill may
combine closely related visuals, but it should preserve each stated learning
purpose and the semantic labels.

### Section 1 - Introduction to Data Engineering

**Purpose:** Give the reader a stable map of the lifecycle before the guide
goes deep into any individual stage. Make it clear that the lifecycle is a
feedback loop with cross-cutting concerns, not a rigid one-way assembly line.

**Recommended formats:**

- One top-down Mermaid flowchart or vector figure for the lifecycle.
- One compact table for stage, question, representative artifact, and tool
  category.
- A small role-comparison table if the role discussion remains in this
  section; do not turn it into a second diagram.

**Key nodes and labels:** `Sources`, `Ingestion`, `Storage`, `Processing and
Transformation`, `Orchestration`, `Quality and Reliability`, `Metadata and
Governance`, and `Serving`. The introduction also names observability,
security, and cost as lifecycle concerns; show those as a cross-cutting band
or annotation rather than extra flow nodes so the figure stays readable.
Include feedback from `Serving` to `Sources` only if the diagram remains
legible.

**Caption and accessibility:** Caption the figure with its reading order and
scope, for example, "The data lifecycle from source systems to consumers;
quality, metadata, security, and observability apply across every stage."
The alt text must name all eight core flow stages and state that observability,
security, and cost span them. Do not encode meaning by color alone.

### Section 2 - Data Ingestion

**Purpose:** Explain how data enters the platform and why latency, durability,
delivery semantics, source impact, and replay behavior shape the design.

**Recommended formats:**

- A two-lane Mermaid flowchart comparing batch and streaming ingestion.
- A table comparing at-most-once, at-least-once, and exactly-once processing.
- A compact Mermaid sequence diagram for acknowledgement, retry, duplicate,
  and idempotent sink behavior.
- A separate CDC flow figure only when the CDC discussion needs more than the
  source-to-sink sequence can show.

**Key nodes and labels:** `Source`, `Extractor or Producer`, `Broker or
Buffer`, `Raw Landing`, `Consumer`, `Checkpoint`, `Retry`, `Replay`,
`Deduplication`, and `Idempotent Sink`. For CDC, label `Transaction Log`,
`CDC Connector`, `Change Event`, and `Delete` explicitly.

**Caption and accessibility:** State whether each lane is batch, streaming, or
micro-batch. Explain that at-least-once delivery can create duplicates and that
exactly-once processing depends on coordinated checkpoints and an idempotent
destination. The alt text must describe the failure path, not just list the
boxes.

### Section 3 - Data Storage

**Purpose:** Help the reader choose where data belongs and understand the
relationship among physical files, table formats, catalogs, query engines, and
warehouses or lakehouses.

**Recommended formats:**

- A layered vector figure for object storage, file format, table format,
  catalog, compute, and consumers.
- A comparison table for OLTP versus OLAP and row-oriented versus columnar
  storage.
- A small figure showing partition pruning and clustering on a date or key.
- A warning figure or before/after table for the small-files problem.

**Key nodes and labels:** `Object Storage`, `Parquet or Other File Format`,
`Table Format`, `Catalog`, `Query or Compute Engine`, `Warehouse`, `Lake`,
`Lakehouse`, and `Consumers`. On the layout figure, label `Partition Key`,
`Clustered Data`, `Files Read`, and `Files Skipped`.

**Caption and accessibility:** Keep the physical and logical layers distinct
in both caption and alt text. Explain that Parquet is a file format and a
lakehouse table format supplies transactional metadata around files. For
partition diagrams, state the query predicate and which files are skipped;
avoid relying on a shaded region alone.

### Section 4 - Data Transformation and Processing

**Purpose:** Show how raw records become standardized, modeled, aggregated,
and reusable data while making grain, joins, state, and incremental behavior
visible.

**Recommended formats:**

- A top-down flowchart from raw to standardized to curated to serving data.
- A small entity-relationship or star-schema figure for fact and dimension
  tables.
- A table contrasting ETL and ELT, batch and streaming, and full-refresh and
  incremental processing.
- A compact before/after data example for a grain change or join; prefer a
  table over a dense diagram.

**Key nodes and labels:** `Raw`, `Standardized`, `Curated`, `Fact`,
`Dimension`, `Join Key`, `Grain`, `Aggregation`, `Incremental Boundary`,
`Watermark`, and `Serving Model`. Every example figure must state what one row
  represents.

**Caption and accessibility:** Put the grain in the caption or immediately
  before the figure. Explain one-to-many joins and possible row multiplication
  in prose. Alt text should identify inputs, transformation, output grain, and
  any late-data or state assumption.

### Section 5 - Orchestration and Scheduling

**Purpose:** Make workflow control concrete: dependencies, retries, time,
backfills, concurrency, and the boundary between orchestration and processing.

**Recommended formats:**

- A Mermaid DAG with a small, readable pipeline.
- A timeline figure for a failed run, retry, checkpoint, and backfill.
- A decision tree or table for retry, skip, fail, quarantine, and rerun
  behavior.
- A compact schedule/SLA table; do not use a dashboard screenshot as the
  primary explanation.

**Key nodes and labels:** `Extract`, `Load`, `Validate`, `Transform`,
`Publish`, `Dependency`, `Retry`, `Timeout`, `Backfill`, `Catch-up`,
`Checkpoint`, `SLA`, and `Owner`. Show the data path separately from the
control path when both appear.

**Caption and accessibility:** A DAG caption must name the dependency direction
and identify the first failing task in any failure example. A timeline caption
must include timestamps or relative durations. Alt text should state what is
blocked, what is retried, and what data is safe to rerun.

### Section 6 - Data Quality and Reliability

**Purpose:** Connect correctness expectations to executable tests, monitoring,
incident response, and decisions about whether bad data should block a
pipeline.

**Recommended formats:**

- A matrix mapping quality dimensions to example tests and failure actions.
- A lifecycle flowchart from contract to test to alert to remediation.
- A table distinguishing data quality tests, freshness monitoring,
  observability, and incident management.
- A small decision matrix for blocking, warning, quarantining, and accepting a
  known exception.

**Key nodes and labels:** `Completeness`, `Validity`, `Uniqueness`,
`Consistency`, `Accuracy`, `Timeliness`, `Freshness`, `Test`, `Expectation`,
`Alert`, `Quarantine`, `Owner`, `Remediation`, and `Rerun`. Label the asset and
the boundary at which each check runs.

**Caption and accessibility:** Define every quality dimension in text before
using it in a matrix. Alt text should report the action associated with a
failed check, not only the check name. Do not use red/green as the sole signal;
include words such as `block`, `warn`, or `quarantine`.

### Section 7 - Metadata, Governance, and Serving Data

**Purpose:** Explain how people discover, interpret, control, and consume
datasets after they have been produced.

**Recommended formats:**

- A lineage graph from producer through datasets to dashboard, model, or
  application.
- A responsibility table for producer, platform owner, steward, and consumer.
- A compact serving-pattern table for BI, machine learning, and operational
  applications.
- A data-contract figure only if the contract's producer, schema, quality
  guarantees, and consumer relationship cannot be explained in a table.

**Key nodes and labels:** `Producer`, `Dataset`, `Column`, `Catalog`,
`Lineage`, `Data Contract`, `Steward`, `Dashboard`, `Feature or Model`,
`Application`, `Access Policy`, and `Retention`. Label upstream and downstream
  direction and distinguish technical lineage from ownership.

**Caption and accessibility:** State the direction of dependency and the
impact of changing a field. Alt text must identify the producer, intermediate
asset, consumer, and ownership or policy annotations. Avoid using a graph to
imply that governance is only a catalog feature.

### Section 8 - Topics in Data Engineering

**Purpose:** Place security, privacy, observability, cost, and architecture
patterns in their proper cross-cutting context without making them appear to
be required stages in the core lifecycle.

**Recommended formats:**

- A layered security figure for identity, network, data, and application or
  workload controls.
- A comparison table for Lambda, Kappa, Medallion, and Data Mesh patterns.
- A tool-category map or table grouped by capability, not vendor popularity.
- A cost and operations checklist table tied to measurable drivers.

**Key nodes and labels:** `Identity`, `Network`, `Storage`, `Processing`,
`Secrets`, `Classification`, `Audit`, `Retention`, and `Consumer` for the
security figure. For pattern comparisons, label `Batch`, `Stream`, `Serving
Layer`, `Ownership`, and `Primary Trade-off`.

**Caption and accessibility:** Mark pattern diagrams as conceptual, not
prescriptive reference architectures. Explain that tools can occupy more than
one category and that a pattern is a set of constraints, not a product. Alt
text must include the main trade-off and any security boundary shown.

### Section 9 - A Learning Path and Project Roadmap

**Purpose:** Convert the guide into an achievable sequence of practice. Make
dependencies and stopping points visible so the reader can choose a scope
appropriate to their time and experience.

**Recommended formats:**

- A left-to-right or top-down roadmap figure with beginner, core, and advanced
  milestones.
- A project progression table from local batch pipeline to streaming or
  production-style system.
- A prerequisite matrix mapping concepts to hands-on deliverables and evidence
  of completion.

**Key nodes and labels:** `SQL`, `Python`, `Ingestion`, `Storage`,
`Transformation`, `Orchestration`, `Quality`, `Governance`, `Streaming`,
`Portfolio Project`, and `Production Readiness`. Mark optional branches
  explicitly; do not imply that every reader must learn every tool.

**Caption and accessibility:** Caption the roadmap as one possible learning
  order. Alt text must distinguish required milestones from optional branches
  and name the artifact produced at each milestone. Use text labels and
  patterns in addition to color or position.

## Diagram Production Rules

### Source and Output Files

Keep editable diagram sources outside the manuscript and use stable, semantic
names:

```text
assets/diagrams/sec-01-lifecycle.mmd
assets/diagrams/sec-02-ingestion-semantics.mmd
assets/diagrams/sec-03-lakehouse-layers.mmd
assets/diagrams/sec-04-transformation-flow.mmd
assets/diagrams/sec-05-orchestration-dag.mmd
assets/diagrams/sec-06-quality-loop.mmd
assets/diagrams/sec-07-lineage.mmd
assets/diagrams/sec-08-security-layers.mmd
assets/diagrams/sec-09-learning-roadmap.mmd
```

Render Mermaid sources to a vector format supported by the LaTeX toolchain,
preferably PDF or SVG converted by the publication skill. Use PNG only when a
downstream renderer requires it. Keep the source versioned with the manuscript
so a figure can be regenerated after wording or labels change.

A figure reference should have a semantic ID that remains valid if sections
are reordered:

```text
fig:sec01-lifecycle
fig:sec02-delivery-semantics
fig:sec03-lakehouse-layers
fig:sec04-grain-change
fig:sec05-orchestration-dag
fig:sec06-quality-loop
fig:sec07-lineage
fig:sec08-security-layers
fig:sec09-learning-roadmap
```

Use the same ID in the source asset, the Markdown figure attribute, and the
LaTeX label generated by the publication skill. Captions should explain the
figure without requiring the paragraph that introduced it. Numbering is
generated at build time; never type `Figure 1` into prose.

### Accessibility and Legibility

- Supply meaningful alt text for every non-decorative figure.
- Use short labels in diagrams and put definitions in surrounding prose.
- Keep diagrams top-down or split them when there are more than five nodes in
  a horizontal row.
- Use high contrast, readable type, and line styles or symbols in addition to
  color.
- Ensure grayscale printing preserves flow, grouping, and status.
- Do not place essential information only in a legend or tooltip.
- Put a plain-language interpretation immediately after a complex figure.
- Test figures at the final print width; a diagram that is legible on a screen
  may fail when reduced to a single-column page.

## Pandoc and LaTeX Conventions

### Front Matter and Table of Contents

Use YAML front matter for title, author, date, document class, geometry, and
TOC settings. Keep automatic section numbering disabled because the visible
headings already carry section numbers. Generate one table of contents from
the heading tree. Do not retain a manually typed contents list alongside the
generated TOC.

The default publication should show H1 sections in the TOC and keep H2 topics
out of it to reduce cognitive load. A detailed edition may set `toc-depth: 2`
after checking that the resulting contents page remains useful. The preface,
roadmap, glossary, and references should be included as unnumbered entries
only where the chosen book design calls for them.

### Headings and Cross-References

Keep one blank line around headings, figures, tables, and fenced blocks. Add
stable IDs during the build, or use Pandoc heading attributes when the source
format supports them. Prefer semantic labels such as `sec:storage` and
`fig:sec03-lakehouse-layers` over labels based on page or figure number.

Cross-references should be generated by the publication skill, using the
chosen Pandoc cross-reference filter or equivalent LaTeX mechanism. Prose
should refer to "Section 3" or "Figure" through the reference mechanism rather
than hard-coded numbers, so reordering remains safe.

### Callouts

Use fenced divs with one of the approved classes:

```markdown
::: key-concept
**Key concept.** An idempotent operation can be safely repeated.
:::

::: decision
**Design decision.** Choose batch when the business latency target permits it.
:::
```

The publication skill should map these classes to named LaTeX environments,
with a plain paragraph fallback for HTML or unfiltered Markdown. Avoid raw
LaTeX inside the manuscript unless a feature cannot be represented by the
approved Markdown subset.

### Code

- Use fenced code blocks with an explicit language: `sql`, `python`, `bash`,
  `yaml`, `json`, or `mermaid`.
- Keep one idea per code block and introduce it with the expected input and
  output.
- Remove credentials, account identifiers, machine-specific paths, and
  commands that delete or overwrite data without an explicit warning.
- Prefer short, complete examples over fragments that hide required setup.
- Wrap long lines for the final page width and use a consistent syntax
  highlighting style with a high-contrast monochrome fallback.
- Commands and identifiers in prose use backticks; do not format an entire
  paragraph as code.

Mermaid blocks are source material for figures, not guaranteed LaTeX output.
The publication skill must render or replace them before producing the final
publication and must retain the source diagram for maintenance.

### Tables

Use ordinary Pandoc-compatible Markdown tables for comparisons and compact
reference material. Keep tables narrow enough for the target page width:

- one idea per row;
- short column names;
- no nested lists or paragraphs inside cells;
- split a wide tool landscape into multiple capability tables;
- repeat headers when a table spans pages;
- align numeric values consistently; and
- include a caption and semantic ID for tables that are referenced in prose.

Do not use tables to lay out paragraphs or simulate a diagram. Use a figure for
flow, dependency, topology, or event order. Use a table when the reader needs
to compare the same attributes across alternatives.

### Links, References, and Claims

Use descriptive link text, not bare URLs. Keep durable specifications,
standards, and official tool documentation in Section 11. For mutable web
pages, record an access date in the bibliography metadata. Claims about tool
behavior, delivery guarantees, or pricing should be dated or qualified when
they can change. Avoid vendor logos as explanatory figures; name tools in text
or comparison tables and explain their capability category.

## Editorial Checklist

### Structure

- [ ] H1 headings are limited to Sections 1-11 and match the structural
  contract.
- [ ] All instructional subtopics use H2; no H3 headings or accidental title
  headings remain.
- [ ] The preface and roadmap are outside the numbered section hierarchy.
- [ ] The generated TOC is the only formal contents list; any Reader's Roadmap
      is clearly labeled as a reading aid.
- [ ] Each core section opens with purpose and ends with a useful check or
  checklist.

### Reader Load

- [ ] The introduction defines the lifecycle, key terms, and tool categories.
- [ ] Each acronym is expanded on first use or included in the glossary.
- [ ] Concept, tool, and implementation advice are visibly distinguished.
- [ ] Tool lists identify a default learning choice and the reason to choose
  an alternative.
- [ ] Cross-cutting topics are framed as concerns that apply across stages.
- [ ] Examples state their grain, assumptions, failure behavior, and intended
  audience.

### Visuals

- [ ] Every proposed visual has a learning purpose and is referenced in prose.
- [ ] Every figure has a semantic ID, caption, and meaningful alt text.
- [ ] Diagram labels match the manuscript's terminology exactly.
- [ ] No diagram relies on color alone, and all essential text survives
  grayscale printing.
- [ ] Figures are legible at final page width and do not split awkwardly.
- [ ] Tables are used for comparison, not layout, and have repeatable headers.

### Reproducibility and Safety

- [ ] Code blocks declare their language and avoid secrets or destructive
  commands without warnings.
- [ ] Diagram sources are retained and can be regenerated deterministically.
- [ ] Tool versions, mutable URLs, and time-sensitive claims are qualified.
- [ ] Examples do not imply that a large production stack is required for a
  small learning project.

### LaTeX Output QA

- [ ] The title page, preface, TOC, section openings, and references render as
  intended.
- [ ] No duplicate section numbers or duplicate TOCs appear.
- [ ] Cross-references resolve and figure/table numbering is generated.
- [ ] Code, tables, captions, footnotes, and long URLs do not overflow the
  page margins.
- [ ] Callouts have consistent visual treatment and a plain-text fallback.
- [ ] PDF text remains selectable and figures have usable alternate text or a
  nearby textual description.
- [ ] A final read-through checks that diagrams clarify rather than repeat the
  surrounding prose.
