# ReportKit callout titles and image slots implementation plan

**Status:** Implementation complete in merged PR #54 (`f6293d4`) · verification pending · 24 September 2026
**Spec:** `docs/superpowers/specs/2026-09-24-reportkit-callout-titles-and-image-slots-spec.md`
**Goal:** Make semantic callouts usable with default or replacement headings, and give Markdown publications declared image slots that render supplied assets or conspicuous draft placeholders.

## Execution model

Use four agents with separate file ownership. Agents A and B can start together. C starts after B publishes the image declaration and validation interface. D can prepare guidance and fixtures immediately, but regenerates contract docs and completes native visual acceptance only after A–C land. One integrator reviews the interfaces, runs the complete gate, and resolves cross-stream defects with the owning agent.

| Stream | Owner | Primary files | Handoff |
| --- | --- | --- | --- |
| A. Callout contract | Agent A | `latex_templates/reportkit-boxes.sty`, `python_scripts/reportkit/registry.py`, `python_scripts/reportkit/authoring_ir.py`, `python_scripts/reportkit/tex_renderer.py`, callout and registry tests | Exact TeX and Markdown title syntax plus updated context records |
| B. Image declaration and validation | Agent B | new `python_scripts/reportkit/image_slots.py`, `python_scripts/reportkit/publication_validation.py`, `python_scripts/reportkit/cli.py` (`check` path only), `publication_pipeline/scripts/validate_publication.py`, validation and declaration tests | Typed slot records, diagnostics, profile-aware validation API |
| C. Image rendering and build | Agent C | new image TeX module, `publication_pipeline/scripts/publication_build.py`, `publication_pipeline/scripts/render_visuals.py`, build/render tests, build-report schema | Supplied image, placeholder, source mapping, build-report records |
| D. Guidance and acceptance | Agent D | `SKILL.md`, hand-written authoring references, generic fixture files, fixture/visual acceptance tests | Authoring examples and visually reviewed default/institutional outputs |

No agent edits another stream's files during parallel work. If an interface needs to change, the owning agent publishes the revised contract before dependent work proceeds. Generated reference sections are written once by the integrator with `reportkit docs --write` after A's metadata is final; D reviews the result. Do not hand-edit generated inventories.

## Interface checkpoint before dependent work

Freeze these choices in a short implementation note or commit before C renders slots and D finalizes examples:

1. **Callouts:** The nine single-title environments and `evidence`, `limitation`, `tip` accept no argument, `[replacement]`, or legacy `{suffix}`. `[replacement]` prints only that heading; `{suffix}` prints the semantic default followed by the suffix. `metric` is unchanged. Reject simultaneous `[replacement]{suffix}` explicitly. Empty `[]` resolves to the default or emits an actionable error; it never prints a blank heading. Record the exact xparse signature and argument names in source metadata. A likely shape is `o g`; the registry must learn the optional braced `g` specifier, and the safe renderer must emit it only for the legacy field. `title:` in a fenced Markdown callout means replacement, not legacy suffix.
2. **Image slots:** Use one consumer-owned `image-slots.yaml` with an `images:` mapping keyed by slug, and a standalone `[[REPORTKIT-IMAGE:img:<slug>]]` manuscript line. Each record names `purpose`, `caption`, `alt`, `aspect_ratio` (`wide` 16:9, `landscape` 4:3, `square` 1:1, `portrait` 3:4), `path` (`assets/images/<slug>.<supported extension>`), `source`, `creator`, `license`, `attribution`, and `restrictions`. Use the same proportions in the placeholder and image frame. A missing file is a draft placeholder. Present assets need concrete rights/credit values; any pending rights state remains unresolved for final/release.
3. **Validation result:** B exposes a typed slot lookup and an unresolved-slots list to C. `reportkit check` and `reportkit build` share validation; draft permits a declared missing file with a warning, while `final` and `release` profiles fail on missing files or pending rights. All other invalid declarations fail in every profile. The existing `REPORTKIT-VISUAL` contract remains untouched.
4. **Build report:** C records each used image slug, declaration path, asset state (`supplied` or `placeholder`), replacement path, and source location, plus an unresolved count/list. The PDF placeholder visibly includes `IMAGE NEEDED: <slug>`, purpose, and exact replacement filename.

If the current profile resolver has no `final` profile, implement the release gate for `release` and document how consumers select it; do not invent a second profile silently. Keep one declaration per used slug, reject duplicate or orphan declarations, and keep `img` and `fig` namespaces separate.

## Stream A — flexible semantic callout titles

- [x] Change all nine single-title environments and three aliases to the checkpoint syntax. Preserve the existing colour, font, spacing, breakability, and reserve-space behaviour. Pass the resolved heading into the existing callout box so replacement titles never acquire a category prefix.
- [x] Handle legacy `{title}` explicitly, including aliases; never let the braced value fall into body prose. Make simultaneous title forms and malformed/empty values deterministic.
- [x] Update source-adjacent `<reportkit-contract>` metadata and `parse_xparse_signature` for optional braced arguments; update the existing xparse specifier invariant and regenerate generated references.
- [ ] Confirm `reportkit context --json` reports both optional title forms accurately.
- [x] Update safe directive validation/rendering so `title: Weak` produces `\begin{redflag}[Weak]`, a no-title directive produces `\begin{redflag}`, and user text remains TeX escaped. Reject unknown fields and legacy/replacement collisions in directives.
- [ ] Add focused TeX and Python tests for no title, override, legacy suffix, aliases, empty title, and `metric` isolation. Compile under default and institutional themes; extract PDF text to rule out doubled labels.

**Exit:** All callout forms compile; directive output and context metadata agree with the TeX interface.

## Stream B — image declaration and validation

- [x] Implement the `image-slots.yaml` parser using the repository's supported YAML subset. Normalize to typed records; reject duplicate slugs, duplicate manuscript uses, missing declarations, orphan declarations, unknown aspect ratios, missing required metadata, and malformed sentinel lines with source locations.
- [x] Require paths to be relative, contained under `assets/images/`, slug-matched, and of a supported raster/vector extension. Check symlinks by resolved path as well as textual `..`/absolute paths. Support PNG, JPEG, and PDF; exclude SVG because no local conversion path is available.
- [x] For supplied assets, validate concrete source, creator, license, attribution, and restrictions data; explain what needs fixing in each diagnostic. For missing assets, retain the declaration as an unresolved draft slot and report its intended path. Never infer rights or fetch an image.
- [x] Thread profile awareness through both `reportkit check` and build validation. Release/final selection rejects unresolved slots before conversion; draft continues with warnings. Preserve all diagram sentinel and fragment validation behaviour.
- [ ] Add table-driven validation tests for safe/unsafe paths, symlink escape, malformed metadata, missing file, duplicate/orphan slug, supplied rights data, and profile gates.

**Exit:** A consumer can validate slot declarations without Pandoc or TeX, and C can query the validated records directly.

## Stream C — image rendering and build integration

- [x] Add a small TeX image unit loaded by the generated Markdown build preamble, using existing renderer hooks for page anchoring, caption, and source treatment. Do not modify `reportkit.cls`. Keep it non-floating, near its first reference, with natural image aspect ratio and no default crop. Fit within the preset frame; render the missing state at the declared proportions with the required visible placeholder text.
- [x] Extend Pandoc post-processing in the canonical build path to replace only standalone image sentinels. Escape all declaration text and paths before generating TeX. Maintain generated-line/source maps for image units and leave `REPORTKIT-VISUAL` replacement untouched.
- [x] Update the standalone `render_visuals.py` path to use the shared sentinel renderer.
- [x] Stage supplied images through the existing asset copier, record hashes through the existing asset report, and add image-slot state and unresolved counts to `build-report.json` and its schema. Missing draft assets render as placeholders. Replacement requires only adding the file at the declared path and rebuilding.
- [ ] Add pipeline tests that build one supplied and one missing slot, inspect generated TeX and report JSON, and confirm that adding the file changes the state to supplied without manuscript edits. Add a regression build for a diagram sentinel in the same manuscript.

**Exit:** Both slot states build successfully in draft; supplied/placeholder state is visible in the PDF and machine-readable report.

## Stream D — authoring guidance and visual acceptance

- [x] Expand `SKILL.md` and the publication authoring reference with a concise callout choice table: principle, decision, research problem, assumption, risk, evidence caveat, limitation, tip, deliverable; explain why ordinary prose, whole lists, numerical evidence, and page filler remain unboxed. Set no quota. Distinguish callouts from feature-article sidebars and executive-brief exhibits.
- [x] Provide fenced `reportkit` examples, including `redflag` with `title: Weak`, `tipnote` with `title: Strong`, and a no-title example. Show supporting explanation outside the box. Document the legacy TeX suffix separately.
- [x] Document the image decision, declaration fields, local sourcing/rights recording, supplied image checks, placeholder meaning, exact replacement workflow, and `--profile release` gate. State that builds never download images and engine fixtures contain no third-party imagery.
- [x] Add a realistic callout pair to the generic Markdown manuscript fixture and a generic image fixture with a locally created graphic and one absent path.
- [ ] After A–C land, compile every callout form under default and institutional themes and build the mixed image fixture. Extract heading and placeholder text, inspect source mapping and placement, and render the relevant pages for visual review at a useful DPI. Check colour, overflow, frame proportions, caption/source treatment, and proximity to introductory text.

**Exit:** Examples match the working API and native PDF review supports the spec's appearance and placement claims.

## Integration gate

- [x] Integrate A–D in the shared feature branch. Resolve interface drift with the file owner; avoid parallel edits to `publication_build.py` or generated docs.
- [x] Run `reportkit docs --write` and review the generated diff. Generated rows now show optional `title` and `legacy_suffix`, while `metric` retains label/value.
- [ ] Run `reportkit docs --check --json` and `reportkit context --json`.
- [ ] Run focused tests and the repository test suite, `scripts/acceptance_check.sh --require-tex`, `reportkit check`, combined draft/release builds, `reportkit inspect`, and page rendering for the acceptance fixtures. A release build with a missing image must fail with an actionable diagnostic; the same draft build must produce a PDF and unresolved report entry.
- [ ] Verify existing consumer-style `REPORTKIT-VISUAL` manuscripts and legacy braced callouts continue to build. Review generated PDFs for both themes before marking this complete.

**Done when:** Every acceptance item in the spec is demonstrated by tests, extracted PDF text, build reports, and visual inspection, with no changes to the underlying `reportkit` class or publication-specific assets in the engine.
