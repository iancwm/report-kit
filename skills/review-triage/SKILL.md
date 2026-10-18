---
name: reportkit-review-triage
description: Triage an external review of a rendered ReportKit PDF (from a person or a chatbot that saw only the PDF) against the project's source. Use when handed review findings, a "council" spec, or critique of a built PDF, before changing any file.
---

# ReportKit review triage

An external reviewer saw only the rendered PDF. Its findings are leads to confirm, not instructions to apply. Reviewers often misread extraction artifacts, assume the wrong source format, and prescribe fixes for a toolchain this project does not use.

## Ground rules

- Work inside this project. The engine is read-only reference; never edit it and never change the theme to fix a finding.
- Use only the primitives from `reportkit context --source-root . --slice primitives --json` (also copied to `.reportkit/context.json`). Ignore any suggested package, macro, or command that is not one of them.
- Honour the project's own agent instructions (`AGENTS.md` or equivalent) and editorial files. They define intentional devices and constraints the reviewer could not see.
- Do not hide behind the source check. `check` passing is not a passing visual review.

## Procedure

1. **Recover state.** Run `reportkit status --source-root . --json`. Note the target, source mode, and `next_step`. Read the project's editorial plan and claim/evidence files if present.
2. **Rebuild the baseline.** Build, then render the pages the findings cite (`reportkit render --source-root . --pages <n> --json`). Findings refer to the reviewer's PDF; confirm yours matches, or note the difference.
3. **Reproduce each finding.** Find the quoted text or visual in source and in your render. Record one verdict per finding:
   - `confirmed`: reproduced, cause located in a source file.
   - `not reproduced`: absent in the current build, or a text-extraction/OCR artifact.
   - `intentional`: a documented device or caveat (cite where it is documented).
   - `opinion`: taste, not a defect.
4. **Route each confirmed finding to a layer.**

   | Layer | Where it lives | Action |
   | --- | --- | --- |
   | content | manuscript chapters (Markdown) or the TeX body | Edit prose directly. |
   | structure | `manuscript/order.txt`, frontmatter, appendices | Reorder, add or remove files. |
   | markup | tables, callouts, headings, `fragments/fig-*.tex`, image slots | Rewrite with the target's primitives only. |
   | evidence | claim ledger, citations, limits/caveat sections | Fix through the evidence record first, then the prose. Never "soften" a claim to satisfy a reviewer. |
   | engine/theme | pagination, running headers, TOC, fonts, page numbers, spacing | Do not patch. Add to the upstream list. |

   If the cause is uncertain, route to `engine/theme` only after ruling out the project's own source.
5. **Fix in dependency order**: structure, then content and evidence, then markup. Rebuild after each batch; a fix can move page breaks and invalidate later findings.
6. **Verify.** Run `reportkit check --source-root . --json` and read every diagnostic's `remediation`. Build, render every page, and inspect the pages that changed plus their neighbours. If you cannot view rendered pages, say so; do not claim a visual pass.
7. **Report** in `review/triage.md` (create `review/`), one row per finding: ID, verdict, layer, action taken (file) or reason declined, verification page. Add an **Upstream** section listing engine/theme items with page evidence, ready to file against the engine. Do not commit unless asked.

## Judgement calls

- Two reviewers agreeing is not evidence. Only the source and the render are.
- A finding that is real but conflicts with a project constraint goes in the report as `declined`, with the constraint cited.
- Do not add content to answer "missing section" findings unless the editorial plan calls for it; flag it for the author instead.
- Leave unrelated defects you notice in the report under **Noticed, not fixed**.

## Expected finding format

Triage works best when findings carry: ID, page and verbatim quote, symptom, kind, likely layer, confidence, severity, and a one-line "done looks like". For findings missing these, infer them from the render and say so in the report.
