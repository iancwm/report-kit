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

The guide renderer has its own locked Python environment. To build the
publication, first use the `data-engineering-guide` branch (or a worktree for
it), then run:
```bash
bash data_engineering_guide/scripts/setup.sh
bash data_engineering_guide/scripts/combine.sh
```

`main` carries the renderer and its tests; it intentionally does not carry the
publication manuscript or diagram fragments.

## Before tagging a release

Run the acceptance check directly and confirm it passes:
```bash
bash scripts/acceptance_check.sh
```
Then do a fresh-clone dry run: clone the repo into a scratch directory,
run `shell_scripts/bootstrap.sh`, and confirm `reportkit_doctor.py`
reports `MODE: FULL BUILD` before tagging.
