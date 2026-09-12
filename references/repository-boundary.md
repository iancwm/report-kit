# Repository boundary: engine vs. publication

ReportKit is a reusable publication **engine**. A publication built with it —
its manuscript, figures, assets, and final PDF — lives in a **separate
consumer project**, never in this repository.

Before editing anything, know which side of the line you are on:

- If you are changing a `.cls`/`.sty` file, a Python module under
  `python_scripts/` or `publication_pipeline/scripts/`, a shell script, or a
  reference doc — you are working **on the engine**. Nothing you write here
  may name a specific publication's title, path, assets, or manuscript
  structure.
- If you are writing prose, choosing figures, filling in `publication.yaml`,
  or looking at a build's PDF/QA output — you are working **on a
  publication**, in a different repository from this one.

## What lives where

| report-kit (this repo — the engine) | Consumer publication project |
|---|---|
| `latex_templates/` — `.cls`, `.sty` | `manuscript/` — Markdown + `order.txt` |
| `python_scripts/` — viz, doctor, licence/config loaders | `fragments/` — LaTeX diagram fragments |
| `publication_pipeline/` — build/validate/inspect harness | `assets/` — cover art, images, source data |
| `scripts/`, `.githooks/` | `figures/` — generated chart PDF/PNG |
| `references/`, `metadata/` | `publication.yaml` — title, author, version, identity |
| `tests/` — engine regression suites | `build/`, `output/` — build artefacts, QA logs, final PDF |
| `font_data/` | `reportkit.lock` — pinned engine ref + toolchain versions |

`publication_pipeline/example_publication/` is the one exception: a small,
generic fixture used by this repo's own tests and pre-commit hook to exercise
the harness. It is not a publication to build on, and it must never grow
book-specific content.

## Recommended consumer project structure

```text
my-publication/
  manuscript/          # 01-intro.md, 02-background.md, ... + order.txt
  fragments/            # fig-<slug>.tex, one per [[REPORTKIT-VISUAL:fig:<slug>]] sentinel
  assets/                # cover art, source data, anything referenced by name
  figures/              # generated chart PDF/PNG (reportkit_viz.py output)
  publication.yaml       # title (required), subtitle, author, version, ...
  build/                 # gitignored — compiler output, logs, page renders
  output/                # gitignored — final release PDF + QA manifest
  reportkit.lock         # written by publication_build.py on a passing build
```

Initialize this structure with `<report-kit-clone>/reportkit init
<publication-dir>` — it refuses to run if `<publication-dir>` resolves inside
the ReportKit clone.

## Guardrails

1. **Do not store full books or reports in report-kit.** A publication's
   manuscript, fragments, assets, or final PDF do not belong in this
   repository, tracked or gitignored-but-present. `.gitignore` root-anchors
   `/manuscript/`, `/fragments/`, `/assets/`, `/output/`, `/publication.yaml`,
   and `/reportkit.lock` at repo root for exactly this reason.
2. **Do not create long-lived content branches in report-kit.** A branch that
   exists to carry a publication's manuscript belongs in that publication's
   own repository instead. See [migrating-content-branches.md](migrating-content-branches.md).
3. **Do not hard-code project titles, paths, assets, or manuscript structure
   into reusable tooling.** `publication_build.py` reads identity from the
   consumer project's `publication.yaml` (via `python_scripts/publication_config.py`)
   precisely so this engine never again defaults `--title` to one book's name,
   as it once did.
4. **If a publication reveals a reusable need, propose a toolkit issue or
   patch against report-kit** — a new CLI flag, a new `publication.yaml` key,
   a new validation rule — rather than fixing it as a one-off inside the
   publication project.

## How the boundary is enforced, not just documented

- `publication_build.py --source-root <dir>` builds a project outside this
  repo; `--output-root` (default `<source-root>/build`) keeps every artefact
  there too. Neither defaults into this repository.
- `reportkit init` refuses to scaffold a publication directory that resolves
  inside the ReportKit clone.
- `.gitignore` blocks the publication directories from ever being committed
  here by accident.
- `.githooks/pre-commit` validates only `publication_pipeline/`'s own generic
  example — it has no path into a real publication's manuscript.
