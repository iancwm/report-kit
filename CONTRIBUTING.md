# Contributing

## One-time setup: enable the pre-commit acceptance check

```bash
git config core.hooksPath .githooks
```

This points git at `.githooks/pre-commit`, which runs
`scripts/acceptance_check.sh` automatically before any commit that touches
`latex_templates/**` or `python_scripts/**`.

It is not enabled automatically by any script in this repo; the `git
config` command above is a one-time, explicit opt-in per clone, so hook
installation stays a visible convention rather than a script silently
rewriting your git config.

If `pdflatex` isn't installed on your machine, the check warns and allows
the commit rather than blocking it — see `references/font-setup.md` to set
up a TeX toolchain locally.

For a strict local gate, use:
```bash
bash scripts/acceptance_check.sh --require-tex
python3 python_scripts/reportkit_doctor.py --require full-build
```

## Before tagging a release

Run the acceptance check directly and confirm it passes:
```bash
bash scripts/acceptance_check.sh
```
Then do a fresh-clone dry run: clone the repo into a scratch directory,
run `shell_scripts/bootstrap.sh`, and confirm `reportkit_doctor.py`
reports `MODE: FULL BUILD` before tagging.

## What belongs in this repository

report-kit is a reusable publication engine: LaTeX classes/styles, Python
tooling, shell scripts, docs, and small generic examples. A publication built
with it — manuscript, figures, assets, `publication.yaml`, build output, QA
logs, and the final PDF — belongs in a **separate consumer project**, never in
this repository. Full details: [references/repository-boundary.md](references/repository-boundary.md).

1. **Do not store full books or reports in report-kit.** If a change adds a
   real publication's manuscript, fragments, or assets to this repo (tracked
   or not), it belongs in a consumer project instead.
2. **Do not create long-lived content branches in report-kit.** A branch that
   exists to carry a publication's content should be its own repository. See
   [references/migrating-content-branches.md](references/migrating-content-branches.md)
   for how to move one out.
3. **Do not hard-code project titles, paths, assets, or manuscript structure
   into reusable tooling.** `publication_pipeline/scripts/publication_build.py`
   once defaulted `--title` to one specific book's name, with its header,
   footer, and PDF subject hard-coded alongside it — exactly what this rule
   forbids. Identity now comes from the consumer project's `publication.yaml`.
   Any new script or macro should take a publication's specifics as
   input, never assume them.
4. **If a publication reveals a reusable need, propose a toolkit issue or
   patch here** — a new CLI flag, a new `publication.yaml` key, a new
   validation rule, a new diagram primitive — rather than working around the
   gap with a one-off script or hard-coded value inside the publication
   project.
