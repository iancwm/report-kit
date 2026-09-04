# Contributing

## One-time setup: enable the pre-commit acceptance check

```bash
git config core.hooksPath .githooks
```

This points git at `.githooks/pre-commit`, which runs
`scripts/acceptance_check.sh` automatically before any commit that touches
`latex_templates/**` or `python_scripts/**` — it compiles the legacy and
visual-grammar acceptance tests and checks their logs for known failure
signatures (see `references/known-fixes.md`).

It is not enabled automatically by any script in this repo; the `git
config` command above is a one-time, explicit opt-in per clone, so hook
installation stays a visible convention rather than a script silently
rewriting your git config.

If `pdflatex` isn't installed on your machine, the check warns and allows
the commit rather than blocking it — see `references/font-setup.md` to set
up a TeX toolchain locally.

## Before tagging a release

Run the acceptance check directly and confirm it passes:
```bash
bash scripts/acceptance_check.sh
```
Then do a fresh-clone dry run: clone the repo into a scratch directory,
run `shell_scripts/bootstrap.sh`, and confirm `reportkit_doctor.py`
reports `MODE: FULL BUILD` before tagging.
