# Callouts and replaceable image slots

## Choose a callout by reader need

Use a callout when the reader should be able to locate and apply one discrete
principle, decision, risk, assumption, limitation, tip, evidence caveat, or
deliverable independently of the surrounding prose. Keep the explanation
that connects the box to the argument in ordinary paragraphs.

| Reader need | Callout |
| --- | --- |
| A rule or reusable lesson | `principle` |
| A choice and its rationale | `decisionpoint` |
| A question the work investigates | `researchproblem` |
| A condition the analysis relies on | `assumption` |
| A material downside or exposure | `redflag` |
| A qualification about evidence | `evidencenote` |
| A limit on interpretation or scope | `limitationnote` |
| A practical next step | `tipnote` |
| An output the reader should produce | `deliverablenote` |

Do not box routine paragraphs, every list item, numerical evidence better
shown in a table or chart, or text just to fill a page. ReportKit sets no
callout quota. A feature article's `featuresidebar` and an executive brief's
exhibits serve different composition needs; choose those when their article or
evidence layout is intended.

The heading can use the semantic default or a concise replacement. A
replacement keeps the environment's semantic colour and appearance:

```reportkit redflag
title: Weak
content: The estimate depends on one supplier renewing its contract.
```

```reportkit tipnote
title: Strong
content: Compare the renewal date with the last three procurement cycles.
```

Omit `title` to print the semantic default:

```reportkit principle
content: Confirm the inspection interval against the equipment manual.
```

Keep supporting explanation outside the boxes. In direct TeX, the old braced
form remains available as a semantic label followed by a suffix, for example
`\begin{redflag}{Supplier exposure}`.

## Declare an image slot

Use a real image when it clarifies an object's appearance, a place, or an
observed state that prose or a semantic diagram cannot convey as well. If a
suitable licensable image is available, put it at the declared local path,
record its source and terms, and inspect the crop and legibility. ReportKit
builds do not fetch remote images.

Declare one record per slug in the consumer project's `image-slots.yaml`:

```yaml
images:
  pump-housing:
    purpose: Show the inspection point on the pump housing
    caption: Inspection point on the pump housing.
    alt: A pump housing with its inspection point marked.
    aspect_ratio: landscape
    path: assets/images/pump-housing.jpg
    source: https://example.org/local-source-record
    creator: Example author
    license: CC BY 4.0
    attribution: Example author, CC BY 4.0
    restrictions: Do not crop out the inspection marker.
```

The aspect presets are `wide` (16:9), `landscape` (4:3), `square` (1:1), and
`portrait` (3:4). Refer to the slot on its own manuscript line:

```markdown
[[REPORTKIT-IMAGE:img:pump-housing]]
```

If an image is not ready, keep the declaration and leave the file absent. A
draft build prints a neutral `IMAGE NEEDED: pump-housing` placeholder with the
intended subject and exact replacement filename. Adding the image at
`assets/images/pump-housing.jpg` and rebuilding replaces the placeholder
without manuscript edits. Final/release checks reject unresolved slots.

Record truthful source, creator, licence, attribution, and restrictions for
every supplied image. Use an explicit pending value while rights are being
confirmed; pending rights keep the slot unresolved. Never infer a licence or
present a placeholder as documentary evidence. The engine's generic fixtures
use only locally created graphics.
