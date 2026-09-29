---
name: reportkit
description: Create polished PDFs with ReportKit: technical-report, equity-research, executive-brief, feature-article, book, and presentation. Choose a structure and visual theme, then build and review.
---

# ReportKit

ReportKit is the publication engine. Keep each publication in a consumer project outside this clone. Its CLI persists the target on disk and restates the target and next step on each command.

## The loop

| Step | Command | Result |
| --- | --- | --- |
| Select | `reportkit context --slice quickstart --json` | Match the request to a structure × look. |
| Lock | `reportkit target set --source-root <project> --publication-type <T> --theme <H> --source-mode <tex or markdown> --request "<verbatim request>"` | Saves `publication.yaml` and `.reportkit/intent.json`. |
| Scaffold | `reportkit init <project> --publication-type <T> --theme <H> --source-mode <tex or markdown>` | Creates the project for the chosen target. |
| Author | `reportkit context --source-root <project> --slice primitives --json` | Load the selected target’s authoring grammar. |
| Check | `reportkit check --source-root <project> --json` | Runs target and composition checks. |
| Build | `reportkit build --source-root <project> --json` | Builds Markdown or direct TeX through the target gates. |
| Review | `reportkit render --source-root <project> --pages 1 --json`; then `reportkit review --source-root <project> --visual-review <done or unavailable>` | Render pages and record the manual review. |
| Deliver | `reportkit status --source-root <project> --json` | Recover the saved state and quote its TARGET line. |

After a reset or context compaction, start with `reportkit status --source-root <project> --json` and follow its `next_step`.

## Select the publication

`publication_type` is the **structure**: page grammar and authoring roles. `theme` is the **look**: type, color, and spacing. Choose a supported pair from this table.

| Requested format | Structure × look | Source mode | Engine | Worked example | Composition brief | Read next |
| --- | --- | --- | --- | --- | --- | --- |
| Technical report or guide | `technical-report` × `default` or `technical` | TeX or Markdown | pdfLaTeX | `latex_templates/examples/career_guide_en/` | `latex_templates/examples/career_guide_en/composition-brief.json` | [Diagrams and algorithms](references/diagrams-and-algorithms.md) |
| Equity research | `equity-research` × `institutional-research` | TeX or Markdown fragments | LuaLaTeX | `latex_templates/examples/equity-research/` | `latex_templates/examples/equity-research/composition-brief.json` | [Equity research guide](references/institutional-research-theme.md) |
| Executive decision brief | `executive-brief` × `executive` or `institutional-research` | TeX or Markdown | LuaLaTeX | `latex_templates/examples/executive-brief/` | `latex_templates/examples/executive-brief/composition-brief.json` | [Executive brief guide](references/executive-brief-authoring.md) |
| Magazine feature | `feature-article` × `editorial` | TeX for full composition; Markdown supports the opening only | LuaLaTeX | `latex_templates/examples/editorial-feature/` | `latex_templates/examples/editorial-feature/composition-brief.json` | [Feature article guide](references/feature-article-authoring.md) |
| Book or handbook | `book` × `default`, `technical`, or `editorial` | TeX or Markdown | pdfLaTeX for default/technical; LuaLaTeX for editorial | `latex_templates/examples/book/` | `latex_templates/examples/book/composition-brief.json` | [Book guide](references/book-authoring.md) |
| Consulting or venture deck | `presentation` × `executive` or `venture` | TeX or Markdown | LuaLaTeX | `latex_templates/examples/executive-presentation/` | `latex_templates/examples/executive-presentation/composition-brief.json` | [Presentation guide](references/presentation-authoring.md) |

If more than one pair plausibly fits, ask which format the user intends. The alias resolver can map requests such as “magazine” to `feature-article/editorial`; confirm that mapping with the user when intent is uncertain.

## Stop rules

- The build refuses an undeclared target. Declare it; do not accept the default.
- If LuaLaTeX is missing, fix the environment; keep the theme.
- Use only primitives listed by `reportkit context --slice primitives` for your target.
- If you cannot view rendered pages, say so in the delivery message.

## Write for the decision

- Establish the question, scope, evidence, method, and material assumptions before stating conclusions.
- Separate facts, interpretation, uncertainty, and recommendation. Never invent citations, data, or spurious precision.
- Make the executive summary a short narrative: problem, strongest evidence, conclusion, and implication.
- Choose visuals to answer a reader’s question. Cite every figure and diagram with `\source{...}`; a conceptual visual may use `Conceptual diagram.` as its source.
- Use callouts only when the meaning matters. Keep supporting explanation in the main prose, and put full citations in the publication’s source section.

## References

| Topic | Reference |
| --- | --- |
| Technical reports | [Visual grammar](references/visual-grammar.md), [diagrams and algorithms](references/diagrams-and-algorithms.md), [charts](references/charts.md) |
| Equity research | [Institutional-research theme](references/institutional-research-theme.md) |
| Executive briefs | [Executive-brief authoring](references/executive-brief-authoring.md) |
| Feature articles | [Feature-article authoring](references/feature-article-authoring.md) |
| Books | [Book authoring](references/book-authoring.md) |
| Presentations | [Presentation authoring](references/presentation-authoring.md) |
| Callouts and image slots | [Callouts and image slots](references/callouts-and-image-slots.md) |
| Setup and troubleshooting | [Troubleshooting](references/troubleshooting.md), [font setup](references/font-setup.md), [container workflow](references/docker-workflow.md) |
| Commands, schemas, and repository boundary | [Agent contract](references/agent-contract.md), [repository boundary](references/repository-boundary.md) |
