# ReportKit Code Quality and Dependency Remediation

**Status:** Draft v0.1 — findings verified against the tree; phase sequencing
and the Phase 2 scope should receive review before execution. Four scoping
decisions are resolved (see *Resolved decisions*); three questions remain open.
**Baseline:** `main` at `83a5e83`, ReportKit v1.9.3, contract v1.0.0.
**Source:** a full-repository code quality review covering folder structure,
modularity, documentation, and dependency management. Every item below was
verified in this tree — by file:line, by executing the code, or by static
analysis where the toolchain was unavailable. Nothing here is inherited from
another repository or assumed from convention.
**Scope of this document:** engine-internal quality only. It changes no
publication content, no diagram DSL, no visual output, and no schema. Two
items (§A, §P) are user-visible interface changes and are called out as such.

## How to read this

For each item: **Evidence** is what was found in this tree, with the file:line
or the command run. **Verdict** states whether it is a defect, a gap, or
acceptable-but-costly. **Fix** is the concrete change. **Verification** is how
we will know it landed.

Items marked **verified by execution** were reproduced by running the code in
this container. Items marked **verified statically** could not be executed
here — this container has no TeX installation — and rest on reading the
control flow.

## What is already good

Recorded so the remediation does not erode it:

- `toolchain/` is the strongest part of the repository. `Dockerfile` pins its
  base by digest, sources apt from a frozen `snapshot.debian.org` timestamp,
  and pins all twelve apt packages exactly. `requirements.lock` is a
  hash-verified transitive closure. `toolchain.lock.json` declares the whole
  environment and `reportkit/toolchain.py:resolved_toolchain` **verifies it at
  runtime** — apt versions, Python versions, font SHA-256s, and a fingerprint
  over the lock itself. The declared fingerprint matches the computed one
  (`6e0fc8ea…`, verified by execution), and CI enforces it.
- The contract tests genuinely bind LaTeX to Python
  (`tests/test_agent_contract.py:495` ties `version.py` to `reportkit.cls`).
- `cli.py` is well factored: one `_run_*` per command, a parser builder, a
  sixteen-line `main`.
- Near-zero dead code — an AST sweep of the whole tree found two unreferenced
  definitions.
- Docstrings explain *why*, not *what*. `reportkit_viz.apply_theme` and
  `publication_build.template_files` are models of the form.
- Test names are descriptive enough to stand without docstrings. This is
  correct and should not be "fixed".

## Resolved decisions

Settled before drafting; they shape the phases below.

1. **Scope:** all findings, banded by phase, with structural work explicitly
   deferred rather than dropped.
2. **`bootstrap.sh`: retire, not repair** (§A). Its copy-files-into-workdir
   model is superseded by `--source-root`.
3. **Packaging: dev-tooling only** (§K). A `pyproject.toml` carrying pytest
   and lint configuration. The repository stays a git clone, not a
   pip-installable distribution, and the CLI facade stays stdlib-only.
4. **`SKILL.md`: the generated contract may move to `references/`** (§P).

## Summary

| § | Item | Verdict | Phase |
|---|---|---|---|
| A | `bootstrap.sh` crashes, then reports success | **Defect** — verified by execution | 0 |
| B | Four LaTeX escapers that disagree | **Defect** — verified by execution | 0 |
| C | No documented dependency install path | **Gap** — zero `pip install` in README/SKILL/CONTRIBUTING | 0 |
| D | `LICENSE` referenced but absent | **Defect** — GPL compliance | 0 |
| E | `output.directory` accepted then ignored | **Defect** — silent no-op | 1 |
| F | Orphaned venv; `build-all.sh` cannot target a project | **Defect** | 1 |
| G | Doctor diagnoses missing deps without remediation | **Gap** | 1 |
| H | Dependency declarations unsynchronized; `requirements.in` orphaned | **Gap** | 1 |
| I | No dependency staleness or vulnerability signal | **Gap** | 1 |
| J | Dead code and a byte-identical duplicate file | **Cleanup** | 1 |
| K | No packaging manifest; 17 `sys.path` sites | Acceptable-but-costly | 2 |
| L | Duplicated helpers: version probes, YAML preamble, TeX input list | Acceptable-but-costly | 2 |
| M | `build()` is 318 lines | Acceptable-but-costly | 2 |
| N | `reportkit_viz.py` is 1716 lines, outside the package | Acceptable-but-costly | 2 |
| O | Three script directories, split by language not purpose | Acceptable-but-costly | 2 |
| P | 68% of `SKILL.md` is a generated table | Acceptable-but-costly | 2 |
| Q | Docstring gaps on package public API | Cleanup | 2 |

---

# Phase 0 — Broken for new users

Everything in this phase is reachable by following the documented quick start.
Ship as one PR; each item is independently testable.

## A. `bootstrap.sh` crashes at step 5, then prints success

**Evidence.** *Verified by execution.* Reproducing the script's copy step
(`shell_scripts/bootstrap.sh:85-86`) into a scratch directory and running its
step 5 (`bootstrap.sh:157`) exactly as written:

```
$ python3 reportkit_doctor.py
Traceback (most recent call last):
  File "reportkit_doctor.py", line 22, in <module>
    from reportkit.diagnostics import diagnostic_envelope, make_diagnostic
ModuleNotFoundError: No module named 'reportkit'
EXIT: 1
```

`PYTHON_REQUIRED=(reportkit_doctor.py reportkit_viz.py)` copies the two
modules but not the `reportkit/` package both import
(`reportkit_doctor.py:22`, `reportkit_viz.py:51`). The script predates the
package and was never updated when it landed.

Three compounding failures:

1. **It reports success anyway.** `set -uo pipefail` (`bootstrap.sh:40`) omits
   `-e`, and the doctor call is unchecked, so `== bootstrap complete ==`
   prints after the crash.
2. **`SKILL.md` documents the broken command.** Quick start (`SKILL.md:26-31`)
   ends with `cd <report-directory> && python3 reportkit_doctor.py`.
3. **The copied TeX set is stale.** *Verified statically.* `LATEX_REQUIRED`
   (`bootstrap.sh:79`) lists nine files. `reportkit.cls:40` unconditionally
   `\input`s `reportkit-options.tex`, which at `reportkit-options.tex:18`
   `\input`s `reportkit-publication-registry.def`; `reportkit.cls:64`
   requires `reportkit-grammar`. None of those three are in the list, so
   `\documentclass{reportkit}` cannot load even past the crash.

A further latent fault: the copied doctor resolves `REPO_ROOT`
(`reportkit_doctor.py:19`) to the *work directory's* parent, which has no
`toolchain/toolchain.lock.json`, so `resolved_toolchain` would report
`TOOLCHAIN: mismatch` unconditionally. Moot while item 1 crashes first.

**Verdict.** Defect, and the model is superseded. `SKILL.md`'s long-form path
(`SKILL.md:45-48`) already uses `<clone>/reportkit build --source-root …`,
which runs from the clone and has none of these problems. Maintaining two
setup models is what let this one rot unnoticed.

**Fix.** Retire `shell_scripts/bootstrap.sh`. Its three remaining jobs move:

| `bootstrap.sh` step | New home |
|---|---|
| 1. Boundary refusal (work dir inside clone) | `reportkit init` — same refusal, same message |
| 2. Copy core files into work dir | **Dropped.** `--source-root` needs no copy |
| 3. Install Libertinus fonts to `TEXMFLOCAL` | `reportkit init --install-fonts`, or documented in `references/font-setup.md` |
| 4. Scaffold `manuscript/` … `publication.yaml` | `reportkit init` |
| 5. Run the doctor | `reportkit doctor`, unchanged |

This adds one command, `reportkit init`, to a registry that currently holds
nine (`doctor`, `context`, `check`, `build`, `diagnose`, `inspect`, `package`,
`analyse-history`, `docs` — verified against `reportkit.registry.COMMANDS`).
It is an additive contract change: contract minor version to 1.1.0, registry
and `docs --check` regenerated, `schemas/` updated.

Rewrite `SKILL.md`'s Quick start around `reportkit init` + `reportkit build
--source-root`, deleting the copy-and-cd model entirely. Remove
`shell_scripts/` (it holds only this file) and README §5.

**Verification.** A test that scaffolds into `tmp_path` via `reportkit init`,
asserts the boundary refusal for an inside-the-clone target, and asserts the
scaffold contents. `scripts/acceptance_check.sh` gains a fresh-clone dry run
so the documented quick start is exercised, not just described — this is the
gap that let §A survive.

## B. Four LaTeX escapers that disagree

**Evidence.** *Verified by execution.*

| Location | Escapes |
|---|---|
| `publication_pipeline/scripts/publication_build.py:136` `tex_escape` | 10 chars including `~` `^` |
| `python_scripts/reportkit/authoring.py:149` `_tex_escape` | 8 chars, **no** `~` `^` |
| `authoring.py:167` (inline, for URLs) | 3 chars: `%` `#` `&` |
| `python_scripts/license_metadata.py:10` `INVALID_URL_LATEX_RE` | reject-list `[\\{}$^~_]` |

```
input 'A~B^C_D'
authoring._tex_escape → 'A~B^C\_D'
build.tex_escape      → 'A\textasciitilde{}B\textasciicircum{}C\_D'
```

**Verdict.** Defect, with two distinct failure modes. `render_links_tex`
(`authoring.py:153`) validates the *URL* carefully but escapes the *label*
with the weaker escaper. A label containing `~` renders as a non-breaking
space — silently wrong output. A label containing `^` reaches text mode and
fails the build with `Missing $ inserted`.

**Fix.** One `tex_escape` in `reportkit/` (natural home: a new
`reportkit/latex.py`, or `authoring.py` if a new module is unwanted), covering
the full ten-character set. `publication_build.py` imports it rather than
redefining. The URL escaper stays separate — URLs have genuinely different
rules — but moves beside it with a docstring stating why the two differ.
`license_metadata.INVALID_URL_LATEX_RE` stays a validator, not an escaper,
and gains a comment pointing at the escaper it complements.

**Verification.** A parametrized test over all ten metacharacters asserting
every call site produces identical output; a `render_links_tex` test with a
label containing `~` and `^`.

## C. No documented way to install the Python dependencies

**Evidence.** Every `pip install` in the tree:

| Location | Installs | Into |
|---|---|---|
| `toolchain/Dockerfile:38` | `toolchain/requirements.lock` | `/opt/reportkit/.venv` |
| `publication_pipeline/scripts/setup.sh:6` | `publication_pipeline/requirements.txt` | `publication_pipeline/build/.venv` |
| `scripts/acceptance_check.sh:85` (an error string) | `tests/requirements.txt` | `build/.venv-tests` |

Zero in `README.md`, `SKILL.md`, or `CONTRIBUTING.md`. README's entire Setup
section defers to SKILL.md's Quick start, which has no pip step.

**Verdict.** Gap, and the one that makes §G's silence expensive. Outside
Docker, a reader following the documentation never installs matplotlib, numpy,
pandas, or PyMuPDF; they get a degraded `MODE: SOURCE BUILD` with no stated
remedy.

**Fix.** One install step in `SKILL.md` Quick start and `README.md` Setup,
naming `toolchain/requirements.lock` as the supported pinned set and
`tests/requirements.txt` as the test-only addition. `CONTRIBUTING.md` gains
the contributor variant. Three requirements files is acceptable if the entry
point is singular; four venv locations is not (see §F).

**Verification.** Item §A's fresh-clone dry run follows the documented steps
verbatim and reaches `MODE: FULL BUILD`.

## D. `LICENSE` is referenced but does not exist

**Evidence.** `README.md:128` and `references/licensing.md:8` both point at
`` `LICENSE` `` for GPL-3.0-or-later. `metadata/licenses.yml:1` declares
`software_license: GPL-3.0-or-later`. `git ls-files | grep -i '^LICENSE'`
returns nothing.

**Verdict.** Defect. For a GPL project distributed by git clone, the licence
text is a distribution requirement, not a nicety.

**Fix.** Add the GPL-3.0-or-later text as `LICENSE`.

**Verification.** Extend `tests/test_licensing.py` to assert the file named by
`metadata/licenses.yml` exists and is non-empty.

---

# Phase 1 — Wrong, misleading, or unenforced

## E. `output.directory` is accepted, validated, and then ignored

**Evidence.** `config.resolve_output` (`reportkit/config.py:423`) has zero
callers — confirmed by an AST sweep of the whole tree. But `output` is in
`SECTIONS` (`config.py:43`) and `KNOWN` (`config.py:42`), so it validates as a
recognized key. `resolve_roots` (`publication_build.py:303`) consults only
`--output-root`, defaulting to `<source-root>/build`.

**Verdict.** Defect. A consumer who sets `output.directory` passes `reportkit
check` cleanly and has the value silently discarded.

**Fix.** Decide one way and make the code say so. Either wire `resolve_output`
into `resolve_roots` as the default beneath `--output-root`, or remove
`output` from `SECTIONS`/`KNOWN` so `check` rejects it with the existing
unknown-key diagnostic. Wiring it up is preferable — it is a documented-shaped
feature a consumer would reasonably expect — but either resolves the silence.

**Verification.** A test asserting the chosen behaviour: honoured with correct
precedence, or rejected by name.

## F. Pipeline wrapper scripts: an orphaned venv and an unusable `build-all.sh`

**Evidence.** Two independent defects in `publication_pipeline/scripts/`.

*The venv is never found.* `setup.sh:4` creates
`publication_pipeline/build/.venv`. `publication_build.py:561` looks for the
renderer at `output_root / ".venv" / "bin" / "python"`, where `output_root`
defaults to `<source-root>/build` and `source_root` defaults to
`publication_pipeline/example_publication`. The two paths cannot coincide.
The build silently falls back to `sys.executable` (`publication_build.py:563`).

*It also writes into the engine clone*, which `CONTRIBUTING.md` rule 3 and
`references/repository-boundary.md` forbid. `acceptance_check.sh:85` suggests
a fourth venv, `build/.venv-tests`, in the same place.

*`build-all.sh` cannot target a project.* `build-all.sh:4` does not forward
`"$@"`, so `--source-root` cannot be passed and it can only ever build the
bundled example. It also calls `publication_build.py` directly while its
siblings `combine.sh:4` and `build-section.sh:8` go through `./reportkit` —
the interface `README.md:88` calls "the stable command interface". It is
undocumented in `publication_pipeline/README.md`, which documents only
`combine.sh`. Separately, `build-section.sh:3` rejects more than two arguments
while advertising `[build options]`.

**Verdict.** Defect in both cases. The wrappers are pre-`--source-root`
legacy that the facade superseded.

**Fix.** Delete `build-all.sh`, `build-section.sh`, `combine.sh`, and
`render-visuals.sh`; `./reportkit build --mode {sections,section,combined}`
covers all four, and `publication_pipeline/README.md` already presents the
facade as canonical. Rewrite `setup.sh` to take the target venv path as an
argument defaulting **inside the consumer project**, matching
`publication_build.py:561`, and document `REPORTKIT_PDF_PYTHON` as the
override. Same correction for `acceptance_check.sh:85`'s suggested path.

**Verification.** A test asserting `setup.sh`'s default venv path equals the
path `publication_build.py` probes — the invariant that broke.

## G. The doctor diagnoses missing dependencies without saying how to fix them

**Evidence.** `reportkit_doctor.py:140-144` checks matplotlib, numpy, and
pandas and downgrades the reported mode when they are absent. For fonts it
prints actionable remediation (`reportkit_doctor.py:203`: `apt-get install -y
texlive-fonts-extra`). For Python packages the `MODE: SOURCE BUILD` branches
(`reportkit_doctor.py:205-209`) print no install command and name no
requirements file.

**Verdict.** Gap. The cheapest high-value fix in this document.

**Fix.** Add the install line to both degraded branches, naming
`toolchain/requirements.lock`. Carry the same string in the `--json`
envelope's diagnostic so agent callers get it too.

**Verification.** A test asserting the remediation string appears in both the
text and JSON outputs when a dependency is absent.

## H. Dependency declarations are unsynchronized, and `requirements.in` is orphaned

**Evidence.** Six places declare Python or apt dependency versions:
`toolchain/requirements.in` (6 packages), `toolchain/requirements.lock` (23,
hash-pinned), `toolchain/toolchain.lock.json` `python_packages` (6),
`publication_pipeline/requirements.txt` (1), `tests/requirements.txt` (2), and
the `Dockerfile`'s apt pins. PyMuPDF's version is declared in four of them;
matplotlib's in three.

`toolchain/requirements.in` is referenced by **nothing** — not the Dockerfile,
not CI, not any script or document. No `pip-compile` step is recorded
anywhere. It looks like the source of truth and editing it has no effect.

All declarations currently agree (matplotlib 3.10.6, numpy 2.3.3, pandas
2.3.2, PyMuPDF 1.28.2, pytest 8.3.4, jsonschema 4.25.1 — verified). Nothing
keeps them that way. `CONTRIBUTING.md`'s release checklist covers the
acceptance check and a fresh-clone dry run but says nothing about refreshing
pins.

The `Dockerfile` ↔ `toolchain.lock.json` duplication is a separate case and
is **already defended**: `resolved_toolchain` verifies apt versions, Python
versions, and font hashes at runtime, and the fingerprint is enforced in CI.
That duplication is belt-and-braces, not a defect — leave it.

**Fix.** Either document the regeneration command in `CONTRIBUTING.md` and add
a CI check that `requirements.in` ⊆ `requirements.lock` and agrees with
`toolchain.lock.json`, or delete `requirements.in` and declare
`requirements.lock` + `toolchain.lock.json` the source of truth. Whichever is
chosen, add a test asserting the overlapping version declarations agree.

**Verification.** A test that parses all declaring files and asserts every
package named in more than one carries the same pin. Deliberately skewing one
must fail it.

## I. No dependency staleness or vulnerability signal

**Evidence.** No `.github/dependabot.yml`, no Renovate config, no
`pip-audit`/`safety` step in `contract-ci.yml`, no SBOM. `.github/` contains
only `workflows/contract-ci.yml`.

**Verdict.** Gap, made sharper by how good the pinning is. A hash-pinned
`snapshot.debian.org` toolchain will sit unchanged and unexamined
indefinitely; that is the point of it. `pillow==12.3.0`, `numpy==2.3.3`, and
the Debian snapshot are all frozen, and nothing will report a CVE against
them.

**Fix.** Dependabot on `toolchain/requirements.lock` and the Dockerfile, plus
a non-blocking `pip-audit` step in CI. Keep it advisory: a CVE alert should
open a PR for a human to evaluate against the fingerprint, never auto-bump a
lock that CI verifies by hash.

**Verification.** Dependabot opens a PR against a deliberately outdated pin on
a scratch branch.

## J. Dead code and a byte-identical duplicate file

**Evidence.**
- `python_scripts/career_guide_en_make_figures.py` and
  `latex_templates/examples/career_guide_en/make_figures.py` are byte-identical
  (`diff` returns clean). Only the misplaced copy — in a tooling directory — is
  documented, at `README.md:80`.
- `reportkit/registry.py:345` `_declared_python_primitives`: 37 unreferenced
  lines.
- `reportkit_doctor.py:97` re-inserts `ROOT` into `sys.path` inside
  `check_vector_export`, after the module already imported from `reportkit` at
  line 22. Redundant, and it runs on every call.

**Fix.** Delete the `python_scripts/` copy (the example belongs beside its
`report.tex` and `figures/`) and the README line. Delete
`_declared_python_primitives` and the redundant `sys.path` insert.

**Verification.** The AST sweep used for this review, added to CI as a
"no unreferenced private definitions" check, or simply covered by the ruff
config from §K.

---

# Phase 2 — Structural

Deferred deliberately. None of it is broken; all of it is friction that
produced the Phase 0 and Phase 1 defects. Sequence after Phase 1 lands.

## K. No packaging manifest; 17 `sys.path.insert` sites

**Evidence.** No `pyproject.toml`, `setup.py`, `setup.cfg`, `pytest.ini`, or
`tox.ini` anywhere. Seventeen `sys.path.insert` sites re-derive the import
root by hand, with three different relative depths:

```
tests/test_licensing.py:6                        parents[1] / "python_scripts"
publication_pipeline/tests/test_log_gate.py:4    parents[2] / "python_scripts"
publication_pipeline/tests/test_validation.py:7  parents[1] / "scripts"
```

Plus two bespoke `importlib.util.spec_from_file_location` loaders
(`publication_build.py:64,78`) to reach `reportkit` and `license_metadata.py`
by path. This is what forces `# noqa: E402` on nearly every import block, and
`parents[1]` vs `parents[2]` is a live class of mistake.

There is also **no linter or type-checker configuration** despite the codebase
being fully type-annotated and CI already running five gates. Ruff would have
caught §J's dead code and §K's import ordering.

**Verdict.** Acceptable-but-costly. Per the resolved decision, the fix is
dev-tooling configuration only.

**Fix.** One `pyproject.toml` at the root carrying `[tool.pytest.ini_options]
pythonpath = ["python_scripts", "publication_pipeline/scripts"]` and a ruff
configuration. **No `[project]` table, no `pip install -e .`, no
console_scripts entry point** — the git-clone distribution model and the
stdlib-only CLI facade are unchanged, and `./reportkit` stays the executable.
Delete the 17 path inserts and both dynamic loaders. Add ruff to
`contract-ci.yml`.

**Risk.** `publication_build.py`'s loaders exist partly so the script runs
standalone via `python3 publication_build.py`. Confirm whether that invocation
is still supported before deleting them; if it is, one shared bootstrap helper
replaces both rather than removing them outright.

## L. Duplicated helpers

Three instances of the same shape — one behaviour, N hand-maintained copies —
and the direct cause of §A and §B.

**Evidence.**

*Version probes, 3 copies.* `publication_build.version_line:140` (returns
`"not found"`), `toolchain._version_line:38` (returns `None`),
`reportkit_doctor.check_executable:38` (returns a tuple). Same subprocess
call, same first-line-of-stdout-or-stderr parse, three return conventions.

*YAML parser preamble, 2 copies.* `config._parse_yaml:94` and
`config._parse_subset:136` share roughly ten lines of copy-pasted tab and
indentation validation. The docstring at `config.py:137` honestly explains why
the *grammars* stay separate; the *tokenizer* need not be. The stdlib-only
constraint is legitimate — no PyYAML appears in any requirements file.

*TeX input list, 4 copies.* `publication_build.template_files()` globs it
correctly with an excellent docstring; `acceptance_check.sh:90+` handles it
correctly by hand; `tests/conftest.py:60` uses TEXINPUTS; `bootstrap.sh:79`
hand-lists it and is stale (§A). The repository already solved this once.

**Fix.** One `version_line` in `reportkit/toolchain.py`. One shared tokenizer
under the two YAML grammars. After §A retires `bootstrap.sh`, `template_files()`
becomes the single TeX input list and `acceptance_check.sh` consumes it.

## M. `build()` is 318 lines

**Evidence.** `publication_build.py:314`, the longest function in the
repository by a factor of two, carrying validation, config, staging, Pandoc,
two TeX passes, the log gate, page rendering, and PDF inspection. Two repeated
shapes dominate: roughly twelve `print(..., file=sys.stderr); return <code>`
preflight failures, and roughly nine copies of an identical five-line failure
epilogue that sets `status`, `diagnostics`, and `finished_at`, writes the
report, and returns.

**Verdict.** Acceptable-but-costly. The cost is testability: the only way to
exercise the gate-failure path today is to run an entire build.

**Fix.** A `_fail(report, diagnostics, code)` helper collapsing the nine
epilogues, then split preflight (validate → config → resolve target) from the
compile stages. Target roughly a quarter of current length with each stage
independently testable. Same shape at smaller scale in
`scripts/visual_qa_equity_research.py:188` (180 lines) and
`reportkit/context.py:100` (149 lines).

## N. `reportkit_viz.py` is 1716 lines and sits outside the package

**Evidence.** The largest file in the repository — theming, figure primitives,
formatters, roughly fourteen chart types, annotations, palette validation, a
demo builder, and a CLI in one flat module. It sits beside the `reportkit/`
package and imports back into it (`reportkit_viz.py:51`), a direction the
comment at line 45 flags as open question 8.

`apply_theme` (`reportkit_viz.py:88`) rebinds 25 module globals. Its docstring
is excellent and explains the late-binding mechanism honestly. The consequence
stands: theme state is process-global, so it is not thread-safe and two themes
cannot coexist in one process.

**Fix.** Move to `reportkit/viz/` split by concern — `theme.py`, `figure.py`,
`formatters.py`, `charts/`, `cli.py`. Keep `reportkit_viz.py` as a
re-exporting shim for one release, since `import reportkit_viz as rkv` is the
documented public interface in `SKILL.md` and every generated chart example.
Add a "not thread-safe" note to `apply_theme`'s docstring; do not attempt to
remove the global state in this pass.

## O. Three script directories, split by language rather than purpose

**Evidence.** `scripts/`, `shell_scripts/`, and `publication_pipeline/scripts/`.
README documents the first two as §5 and §7, but the split is by language —
and `scripts/` holds both `.sh` and `.py`, while `shell_scripts/` holds
exactly one file. `publication_pipeline/scripts/` mixes library modules
(`publication_validation.py`) with entry points (`validate-publication.py`),
using both `snake_case.py` and `kebab-case.py` in one directory.
`python_scripts/` holds a package plus four loose modules of differing
maturity.

**Fix.** After §A removes `shell_scripts/` and §F removes the four wrappers,
two directories remain: `scripts/` (repository maintenance: acceptance,
contract, visual QA) and `publication_pipeline/scripts/` (pipeline entry
points). Move `publication_validation.py` into the `reportkit` package, where
its callers already live, and normalize the remaining filenames to
`snake_case`. Move `license_metadata.py` and `publication_config.py` into the
package, leaving shims only if the import paths are part of the contract.

## P. 68% of `SKILL.md` is a generated table

**Evidence.** The generated section (`SKILL.md:328-482`) is 39 KB of the
file's 57 KB. It contains 94 argument descriptions that restate the parameter
name title-cased — `` `sort` (option, optional=False) — Sort. `` — tripling
row width for no information. The signature column already carries it. The
LaTeX `options` rows ("Capability-map layout keys") *are* informative; the
Python chart rows are not.

**Fix.** Per the resolved decision: move the generated contract to
`references/primitive-contract.md`, linked from `SKILL.md`, returning
`SKILL.md` to roughly 330 readable lines. Update
`reportkit/documentation.py:69` `generated_documents` and the `docs --check`
gate to write and verify the new path. Separately, teach the generator to omit
a description that is a title-cased restatement of the parameter name.

**Risk.** `SKILL.md` is the Claude entry point. This assumes an agent will
follow a reference link when it needs an exact signature. If that proves
unreliable in practice, the fallback is trimming the generator in place and
keeping the table inline.

## Q. Docstring gaps on package public API

**Evidence.** Undocumented public functions: `reportkit/toolchain.py` (5 of 5),
`reportkit/documentation.py` (4 of 4), `reportkit/manifest.py` (2 of 2).
`toolchain.resolved_toolchain:96` implements a four-state
`pinned`/`unverified`/`mismatch`/`unavailable` ladder whose semantics are
documented nowhere, in a 50-line function, behind a one-line module docstring.

Test files lacking docstrings are **not** in scope — their names carry the
specification and that is the right choice.

**Fix.** A short docstring on each public function in those three modules.
`resolved_toolchain` gets the status ladder written out explicitly: what each
state means and what transitions between them.

---

# Open questions

1. **`reportkit init` scope (blocks §A).** Should `init` install fonts, or
   only scaffold and refuse boundary violations, leaving fonts to
   `references/font-setup.md`? Font installation writes to `TEXMFLOCAL`
   (normally `/usr/local/share/texmf`), which needs root — `bootstrap.sh:105`
   does this unguarded today. A CLI command that silently requires root is
   worse than a documented manual step.
2. **Is standalone `python3 publication_build.py` still supported (affects
   §K)?** If yes, the dynamic loaders become one shared bootstrap helper
   instead of being deleted.
3. **Contract version for §A.** Adding `init` is additive, suggesting
   1.0.0 → 1.1.0. But retiring `bootstrap.sh` removes a documented entry
   point, which reads as breaking for anyone scripting against it. Confirm
   whether `bootstrap.sh` was ever part of the machine contract or only the
   human quick start — `references/agent-contract.md` should settle it.

# Non-goals

- No change to the diagram DSL, visual output, or any `latex_templates/` file
  beyond what §A's retirement touches.
- No change to `schemas/` except the additive `init` command in §A.
- No removal of the `Dockerfile` ↔ `toolchain.lock.json` duplication: it is
  verified at runtime and in CI, and the redundancy is deliberate.
- No attempt to remove `apply_theme`'s global state (§N) — documented debt,
  correct for a CLI, and out of scope here.
- No new test-coverage mandate. Test naming and structure are good; the
  additions specified are targeted at the specific invariants that broke.

# Acceptance criteria

Phase 0 is done when a fresh clone, following only `SKILL.md`'s Quick start,
reaches `MODE: FULL BUILD` and compiles the example publication — verified by
a dry run in `scripts/acceptance_check.sh`, not by inspection.

Phase 1 is done when every dependency version declared in more than one file
is asserted equal by a test, the doctor names its remedy in both output
formats, and `reportkit check` no longer accepts a key it ignores.

Phase 2 has no single gate; each section is independently shippable and should
be sequenced by whichever is blocking other work at the time.
