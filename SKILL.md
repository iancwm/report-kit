---
name: reportkit
description: "Create designed publications with ReportKit: technical reports (technical-report), equity research (equity-research), executive briefs (executive-brief), magazine-style feature articles (feature-article), books (book), and consulting or venture slide decks (presentation)."
---

# ReportKit

Use ReportKit for evidence-led PDFs and slide decks whose structure and visual system should match the reader's decision. Work in a consumer publication directory outside this engine repository; see [repository boundaries](references/repository-boundary.md).

## Publication loop

Run commands from the publication directory. The CLI restates the target and next step; follow the returned `next_step` after each command.

| Step | Command | Result |
| --- | --- | --- |
| Select | `reportkit context --slice quickstart --json` | Target choices and capabilities |
| Lock | `reportkit target set --publication-type <type> --theme <theme> --source-mode <tex\|markdown> --request "<user request>"` | Declared target and intent |
| Scaffold | `reportkit init <publication-dir> --publication-type <type> --theme <theme> --source-mode <mode>` | Target starter and project structure |
| Author | `reportkit context --slice primitives --json` | Primitives for the selected target |
| Check | `reportkit check --json` | Source validation and composition diagnostics |
| Build | `reportkit build --json` | PDF and `build-report.json` |
| Review | `reportkit render --pages 1` then `reportkit review --visual-review done --json` | Rendered pages and review record |
| Deliver | `reportkit status --json` | Reconstructed project state |

## Choose structure and look

`document.publication_type` selects the publication structure; `document.theme` selects its visual system. Pick both before authoring, then choose a supported `document.source_mode`.

| Requested output | Structure (`publication_type`) | Look (`theme`) | Source mode; engine | Worked example; composition brief | Read next |
| --- | --- | --- | --- | --- | --- |
| General technical report, guide, or white paper | `technical-report` | `default` or `technical` | `tex` or `markdown`; both supported. Theme requires pdfLaTeX. | [Career guide](latex_templates/examples/career_guide_en/); [brief](latex_templates/examples/career_guide_en/composition-brief.json) | [Visual grammar](references/visual-grammar.md) |
| Institutional equity research | `equity-research` | `institutional-research` | `tex` supported; `markdown` fragments. Requires LuaLaTeX. | [Equity research](latex_templates/examples/equity-research/); [brief](latex_templates/examples/equity-research/composition-brief.json) | [Institutional research](references/institutional-research-theme.md) |
| Management decision brief | `executive-brief` | `executive` or `institutional-research` | `tex` or `markdown`; both supported. Both themes require LuaLaTeX. | [Executive brief](latex_templates/examples/executive-brief/); [brief](latex_templates/examples/executive-brief/composition-brief.json) | [Decision writing](references/callouts-and-image-slots.md) |
| Magazine feature or thought-leadership article | `feature-article` | `editorial` | `tex` required; `markdown` opening-only. Requires LuaLaTeX. | [Feature article](latex_templates/examples/editorial-feature/); [brief](latex_templates/examples/editorial-feature/composition-brief.json) | [Feature authoring](references/feature-article-authoring.md) |
| Book, handbook, or long-form guide | `book` | `default`, `technical`, or `editorial` | `tex` or `markdown`; both supported. Editorial requires LuaLaTeX; other themes require pdfLaTeX. | [Book](latex_templates/examples/book/); [brief](latex_templates/examples/book/composition-brief.json) | [Diagrams and algorithms](references/diagrams-and-algorithms.md) |
| Consulting or venture slide deck | `presentation` | `executive` or `venture` | `tex` or `markdown`; both supported. Both themes require LuaLaTeX. | [Executive deck](latex_templates/examples/executive-presentation/); [brief](latex_templates/examples/executive-presentation/composition-brief.json) | [Presentation authoring](references/presentation-authoring.md) |

The build refuses an undeclared target. Declare it; do not accept the default. If LuaLaTeX is missing, fix the environment; keep the theme. Use only primitives listed by `reportkit context --slice primitives --json` for your target. If you cannot view rendered pages, say so in the delivery message.

## Write for the decision

- Establish the question, scope, evidence, method, and material assumptions before conclusions.
- Separate facts, interpretation, uncertainty, and recommendation. Never invent citations, data, or precision.
- Make the executive summary a short narrative: problem, strongest evidence, conclusion, and implication.
- Use a semantic callout when a principle, decision, research problem, assumption, risk, caveat, limitation, tip, or deliverable needs emphasis. Keep ordinary prose, routine lists, and evidence tables out of boxes; see [callouts and image slots](references/callouts-and-image-slots.md).
- Give every figure and conceptual diagram a source and a plain-language description.

## Reference map

| Need | Reference |
| --- | --- |
| Technical-report, book, and brief visual choices | [Visual grammar](references/visual-grammar.md), [diagrams and algorithms](references/diagrams-and-algorithms.md), [charts](references/charts.md) |
| Equity research structure and theme | [Institutional-research theme](references/institutional-research-theme.md) |
| Feature-article rhythm and roles | [Feature-article authoring](references/feature-article-authoring.md) |
| Presentation composition and density | [Presentation authoring](references/presentation-authoring.md) |
| Exact primitive signatures | [Generated primitive contract](references/primitive-contract.md) and `reportkit context --json` |
| Build setup, engine errors, and page inspection | [Troubleshooting](references/troubleshooting.md), [font setup](references/font-setup.md), [Docker workflow](references/docker-workflow.md) |
| Agent, accessibility, and repository contracts | [Agent contract](references/agent-contract.md), [accessibility](references/accessibility-tagging.md), [repository boundary](references/repository-boundary.md) |

For documentation drift, run `reportkit docs --check --json`. For the registry, command arguments, and version policy, use `reportkit context --json`; the source contract is authoritative.
