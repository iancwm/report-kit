# Licensing model

ReportKit separates three things that travel together in a repository but do
not share one licence:

| Scope | Default terms |
|---|---|
| Source code and build tooling | GPL-3.0-or-later; see `LICENSE` |
| Original publication prose and diagrams | CC BY 4.0; see `CONTENT-LICENSE.md` |
| Code examples and third-party assets | The terms stated by their author or upstream source |

Contributors adding publication content should identify whether it is original
or adapted, provide the source and attribution for adaptations, and avoid
presenting third-party material as CC BY content. For a new font, image,
dataset, template, or code sample, add its licence and required attribution to
`THIRD-PARTY-NOTICES.md` and keep the notice close to the asset where practical.

The machine-readable defaults live in `metadata/licenses.yml`. Publication
builds validate that file and inject a rights notice into generated front
matter. A generated notice covers original content only; it does not relicense
code examples or third-party material.
