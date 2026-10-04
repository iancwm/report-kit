# ReportKit skill discoverability spec

**Date:** 2026-10-04
**Scope:** The ReportKit engine's agent-facing surfaces: `SKILL.md`, the
`reportkit context` slices, `reportkit check`, `reportkit status`, and the
per-format references.

## Problem

An agent following `SKILL.md` never suggests image slots, and it misses several
other implemented features. The engine implements and tests these features,
but the loop (SKILL.md table → CLI `next_step` → context slices) never points
the agent at them. In some cases SKILL.md's own rules forbid them.

Audit findings (2026-10-04):

1. **Stop rule excludes Markdown syntax.** SKILL.md says "Use only primitives
   listed by `reportkit context --slice primitives`". That slice lists only
   TeX signatures from the LaTeX registry. These Markdown forms never appear
   there:
   - `[[REPORTKIT-IMAGE:img:<slug>]]` image slots
   - `[[REPORTKIT-VISUAL:fig:<slug>]]` visual markers
   - ```` ```reportkit ```` directive fences
   - the `links.yaml` and `sources.yaml` project files

   The visual marker is the only way to put a figure in a Markdown manuscript,
   and the only place it is documented is a comment in
   `references/repository-boundary.md`.
2. **Image slots are Markdown-only, and nothing says so.**
   - `publication_build.py` skips image-slot handling when
     `source_mode == "tex"`.
   - `feature-article` requires TeX, so magazine features cannot use slots.
   - A TeX project that adds `image-slots.yaml` gets misleading
     `RK_VALIDATION_ORPHAN_IMAGE_DECLARATION` errors telling it to add a
     manuscript sentinel. That sentinel would never render.
3. **The composition audit can be skipped silently.** `reportkit check` audits
   only when `composition-brief.json` or `editorial-brief.json` exists. A
   declared project without one passes with zero diagnostics.
   (`reportkit init` with target flags already scaffolds a brief, so this
   affects projects created without those flags, or ones whose brief was
   deleted.)
4. **Unresolved images are never surfaced at delivery.** `build-report.json`
   records `unresolved_image_slots`, but `reportkit status` ignores them. An
   agent can deliver a draft with `IMAGE NEEDED` placeholders without
   mentioning them.
5. **SKILL.md is missing loop commands and references.**
   - The loop omits `doctor`, even though AGENTS.md requires it before
     promising a PDF.
   - The Review step omits `inspect`, and nothing mentions `diagnose` for
     build failures.
   - SKILL.md never links `licensing.md`, `accessibility-tagging.md`, the
     visual marker, `sources.yaml`/`links.yaml`, or `brand:` overrides (only
     `venture` accepts brand overrides).
   - `\source{...}` guidance conflicts with image-slot credits, which come
     from the manifest.

## Decisions

- **D1.** The `primitives` context slice gains a `markdown_forms` key,
  generated from engine constants. Tests check every example in it against the
  live parsers, so it cannot drift from the code. The SKILL.md stop rule
  admits "primitives and Markdown forms".
- **D2.** Image slots stay Markdown-only; there is no public TeX image-slot
  command in this change.
  - In a direct-TeX project, `check` reports one error,
    `RK_IMAGE_SLOTS_TEX_MODE`, when `image-slots.yaml` exists or the main
    `.tex` file contains an uncommented `REPORTKIT-IMAGE` marker.
  - In TeX mode, `check` drops the misleading `RK_VALIDATION_*IMAGE*`
    diagnostics.
  - Docs route TeX authors to their target's own figure primitives, such as
    `openingvisual` with `\imagecredit`.
- **D3.** `check` reports the warning `RK_COMPOSITION_BRIEF_MISSING` for a
  declared target with no brief. Its remediation names `reportkit init` with
  target flags.
- **D4.** `status` adds `unresolved_images` (a list) and `image_caveat`
  (a string or null), both read from the latest build report. At delivery,
  the `next_step` reason tells the agent to name the unresolved slots.
- **D5.** SKILL.md changes:
  - adds a Preflight (`doctor`) row;
  - adds `inspect` to Review and `diagnose` for build failures;
  - adds a photograph and image-slot guideline;
  - adds an image-slot exception to the `\source` rule;
  - links the new `references/markdown-authoring.md`, plus `licensing.md` and
    `accessibility-tagging.md`.

## Out of scope

- A public TeX image-slot command (an alternative to D2; revisit if TeX
  formats need rights-tracked replaceable images).
- Scaffolding `image-slots.yaml` in `init`. The parser rejects an empty
  manifest with `RK_VALIDATION_IMAGE_MANIFEST_SYNTAX`, so a stub would break
  `check`.
- Image roles in composition briefs.
- Running the composition audit for Markdown before the first build. Today,
  `status` audits the generated TeX after a build, by design (spec §4.7).
- Gating `reportkit build` on `RK_IMAGE_SLOTS_TEX_MODE`. The loop runs `check`
  before `build`.
