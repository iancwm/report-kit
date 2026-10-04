# Markdown authoring and project files

Markdown sources accept a small set of ReportKit forms besides ordinary
Markdown. `reportkit context --source-root <project> --slice primitives --json`
lists them under `markdown_forms`, next to the target's TeX primitives. Raw
TeX is disabled in Markdown; trusted TeX lives only in `fragments/`.

## Markdown forms

### Directives

A fenced `reportkit` block calls a primitive listed for your target. Values
are plain text:

```reportkit redflag
title: Supplier exposure
content: The estimate depends on one supplier renewing its contract.
```

Add `fragment: <name>.tex` to include a trusted file from `fragments/`
unchanged. Callout choice and titles are covered in
[Callouts and image slots](callouts-and-image-slots.md).

### Visual markers

Put a diagram or chart in a Markdown manuscript with a marker on its own line:

```markdown
[[REPORTKIT-VISUAL:fig:process-flow]]
```

Write the figure in `fragments/fig-process-flow.tex`, for example a
`diagram` environment with `caption` and `source` options. Use each slug
once. Chart images come from `rkv.save_figure` ([charts](charts.md)).

### Image slots

Use an image slot for a photograph or an observed state that prose or a
diagram cannot show:

```markdown
[[REPORTKIT-IMAGE:img:pump-housing]]
```

Declare the slot in `image-slots.yaml` and put the file at
`assets/images/pump-housing.<png|jpg|jpeg|pdf>` when it exists. A draft
build shows an `IMAGE NEEDED` placeholder until then. The fields, aspect
ratios, and rights rules are in
[Callouts and image slots](callouts-and-image-slots.md#declare-an-image-slot).
`reportkit status` lists unresolved slots as `image_caveat`; repeat that
text when you deliver.

## Project files

Optional files at the project root. `reportkit check` validates them.

`links.yaml` names external links. `type` is one of `citation`,
`documentation`, `repository`, `dataset`, `further_reading`, or
`interactive_resource`. In a Markdown project, trusted fragments in `fragments/`
reference a link with `\RKLink{<key>}`; a direct-TeX project does not generate
the link macros and uses `\href` directly.

```yaml
links:
  field-survey-data:
    url: https://example.org/survey
    label: Field inspection survey
    type: dataset
```

`sources.yaml` records the evidence behind the publication and which chapter
uses it:

```yaml
sources:
  field-survey:
    type: dataset
    title: Field inspection survey
    file: data/survey.csv
    links:
      - field-survey-data
chapters:
  - id: findings
    title: Findings
    purpose: Report what the inspection found
    sources:
      - field-survey
```

`image-slots.yaml` declares image slots; see above. Bibliography files are
covered in [Bibliography and contents](bibliography-and-contents.md).

## Brand overrides

A top-level `brand:` section in `publication.yaml` sets an organisation's
colours, logo, and display font. Only themes that opt in accept it; today
that is `venture`. Other themes reject it.

```yaml
brand:
  primary: "#0B3D91"
  secondary: "#F2A900"
  logo: assets/logo.pdf
  display_font: Inter
```

Colours must be six-digit `#RRGGBB` values. The logo must be an existing
file inside the project.

## Direct TeX projects

Visual markers and image slots are Markdown-only. A direct-TeX project,
including every `feature-article`, places figures with its target's
primitives and local files. Record the source and licence of every
photograph you include. If a TeX project contains `image-slots.yaml` or an
uncommented `[[REPORTKIT-IMAGE:...]]` marker, `reportkit check` fails with
`RK_IMAGE_SLOTS_TEX_MODE`.
