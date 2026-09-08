# ReportKit vNext — Implementation Plan

**Status:** Implementation in progress. Phase 1 machine interface and the
authoring/QA extensions below are landed locally; supersedes the sequencing and priorities in the
vNext spec; that document remains the source of *intent*, this one the source of
*work*.
**Last updated:** 2026-09-07

**Plans:** [2026-09-06-reportkit-vnext-ai-publication-system-spec.md](../specs/2026-09-06-reportkit-vnext-ai-publication-system-spec.md)
**Reconciles with:** [2026-09-06-reportkit-tooling-hardening-design.md](../specs/2026-09-06-reportkit-tooling-hardening-design.md)

---

## Why this document exists

`TODOS.md` has carried the same instruction since the vNext spec was written:
*"substantial overlap with the tooling spec; reconcile before starting Phase 1."*
This is that reconciliation, and it found two problems that make the vNext spec
unexecutable as written.

**First, most of vNext Phase 1–2 already shipped.** The tooling-hardening spec
is marked *Approved, implementation slice landed*, and its A/B/C/D/E sections
produced section builds, PDF inspection, atomic page rendering with a contact
sheet, `build-report.json`, `reportkit.lock`, the strict log gate, static
validation, and the environment doctor. An agent starting at vNext "Phase 1,
item 5: chapter builds" would rebuild `--mode section`.

**Second, the spec's factual premises do not describe this repository.** It
assumes `engine: lualatex`, a `src/book.tex`, and hand-written
`src/chapters/07-streaming.tex`. None of those exist. The real pipeline is
Pandoc-rendered Markdown compiled by `pdflatex` with no bibliography pass, and
the class has no `\chapter` at all. Section 2 corrects this in full.

What survives reconciliation is smaller and sharper than the spec's 17 sections
suggest: **there is no unified CLI, no `context` command, and the diagnostics
report log-line numbers instead of source locations.** That is the real Phase 1,
and Section 4 specifies it.

---

## 1. Reconciliation audit

Every vNext section against the working tree. "Done" means do not build it
again; "Partial" means extend the named file; "Gap" means genuinely absent.

| vNext § | Capability | Verdict | Where it lives today |
|---|---|---|---|
| §2 | `reportkit doctor` | **Done** | `python_scripts/reportkit_doctor.py` — three modes, `--require full-build` |
| §2 | `reportkit build` | **Done** | `publication_pipeline/scripts/publication_build.py --mode section\|combined\|sections` |
| §2 | `reportkit check` | **Done** | `publication_pipeline/scripts/publication_validation.py` — 15 checks over order/sentinels/fragments/labels |
| §2 | `reportkit inspect` | **Partial** | `publication_pipeline/scripts/inspect_pdf.py` — media-box overflow, page count, link count, metadata |
| §2 | **unified CLI** | **Gap** | Seven entry points, three incompatible import styles, two unimportable filenames |
| §2 | `reportkit package` | **Gap** | No release-packaging step exists |
| §3 | `reportkit context` | **Gap** | Does not exist in any form |
| §4 | `publication.yaml` | **Partial** | `python_scripts/publication_config.py` — flat strings, 10 known keys, `title` required |
| §5 | structured diagnostics | **Partial** | `publication_pipeline/scripts/check-build-log.py` — 7 coarse kinds, **log**-line numbers, no severity, no ownership |
| §6 | chapter builds | **Done** (renamed) | `--mode section`; the class has no `\chapter` — see §2.3 |
| §7 | PDF inspection | **Partial** | As §2 above; no bookmarks, fonts, dimensions, or blank-page checks |
| §8 | page rendering + contact sheet | **Done** | `publication_pipeline/scripts/render_pdf_pages.py` — atomic via tempdir + `os.replace`, 150 DPI, `index.html`, `pages.json` |
| §9 | build manifest | **Partial** | `build-report.json` (`schema_version: 1`) + `reportkit.lock`; missing `pdf_sha256`, `profile`, `commit`, figure/table counts |
| §10 | source/manuscript model | **Gap** | Publication-side; not started |
| §11 | link registry | **Gap** | Not started |
| §12 | visualization registry | **Partial** | Prose table at `SKILL.md:58-78`; not machine-readable, and duplicated against the `.sty` files by hand |
| §13 | publication skill | **Partial** | `SKILL.md` exists and is good, but still prescribes banned `pdftoppm` at `:304` |
| §14 | agent guardrails | **Done** | `references/repository-boundary.md` + `CONTRIBUTING.md` rules 1–4, enforced in three places |
| §15 | build history | **Gap** | `build_id` is computed and then discarded |

**Score:** 6 done, 6 partial, 6 gaps. The spec's four-phase sequencing does not
survive this; Section 4 re-sequences around what is actually missing.

---

## 2. Corrections to the spec's premises

Each of these would send an implementer to a file that does not exist.

### 2.1 The engine is `pdflatex`, not `lualatex`

`publication_build.py:218`:

```python
engine = os.environ.get("REPORTKIT_TEX_ENGINE", "pdflatex")
```

Two fixed passes, no `latexmk`, no CLI flag. `lualatex` appears only in
`tests/conftest.py`, which skips when it is absent. The class is deliberately
dual-engine (`reportkit.cls:11-24` guards `fontenc`/`inputenc`/`libertinust1math`
behind `\ifPDFTeX`, with a comment recording the v1.2.1 bug where loading both
math paths clobbered `\times`). vNext §3's `engine: lualatex` would silently
change the rendering engine of every existing publication.

**Correction:** `engine` is configurable, defaults to `pdflatex`, and any
`context` output must report the resolved value rather than assert one.

### 2.2 There are no `.tex` chapter files

vNext §5's example diagnostic points at `src/chapters/07-streaming.tex`. The
repository has no `src/`. Authors write `manuscript/NN-name.md`; Pandoc renders
each to a *generated* `body-NN.tex` in the output directory
(`publication_build.py:206-211`), with `[[REPORTKIT-VISUAL:fig:<slug>]]`
sentinels replaced inline by `fragments/fig-<slug>.tex`.

**Correction:** diagnostics arrive addressed to generated files. Mapping them
back to authored files is real work, not a formatting detail — see W3.

### 2.3 "Chapter" is "section"

`reportkit.cls:7` loads `article`. The class tops out at `\section`/
`\subsection`. `reportkit-longform.sty:17` already makes every H1 a page break:

```latex
\pretocmd{\section}{\clearpage}{}{}
```

**Correction:** use "section" throughout. `reportkit build --section <id>` — the
capability vNext §6 asks for — is `--mode section`, which has existed since the
tooling spec's A3.

### 2.4 There is no bibliography pass

No `biber` or `bibtex` invocation exists in any build path;
`references/troubleshooting.md:60` advises against `biblatex`+`biber` because
biber is absent from the target TeX Live.

**Correction:** keep `undefined_citation` and `bibliography_warning` as
diagnostic categories — the existing gate already matches those log patterns, so
they cost nothing — but build no bibliography pipeline. If a publication needs
citations, that is its own spec.

### 2.5 `dist/manifest.json` violates the repository boundary

vNext §9 puts the manifest at a repo-relative `dist/`. `references/repository-boundary.md`
is explicit that build artefacts belong to the consumer project, reached via
`--output-root` (default `<source-root>/build`), and `.gitignore` root-anchors
`/output/` to enforce it.

**Correction:** the manifest stays at `<output-root>/combined/build-report.json`,
with history under `<output-root>/history/`.

### 2.6 §12's "promote repeated patterns into primitives" is already the contract

vNext presents this as a new policy. It is the established one, and it has been
executed: `reportstate`, `reportcompare`, and `reporttimeline` were added by the
tooling spec's C2 with the full contract — a semantic environment, a case in
`latex_templates/examples/visual_grammar_acceptance_test.tex`, a rendered-geometry
regression test, and a row in `SKILL.md`'s primitive table.

**Correction:** §12's job is not to establish the policy but to make the registry
*machine-readable* so `context` can serve it and drift can be detected. See W4.

---

## 3. Design decisions

### D1 — Stdlib only

No Typer, no Pydantic, no PyYAML, despite vNext §2 and §4 naming them.
`publication_config.py:4-6` states the constraint deliberately:

> *"This reads the flat `key: value` subset that `metadata/licenses.yml` already
> uses, so no YAML dependency enters the engine."*

`git clone && python3 …` must keep working with zero install. The repository has
no `pyproject.toml`, no `setup.py`, and no `console_scripts`; releases are git
tags (`README.md:104-107`). The `argparse` subcommand pattern at
`reportkit_viz.py:1411` is the in-repo precedent to follow.

PyMuPDF stays the single third-party dependency, pinned in
`publication_pipeline/requirements.txt`, used only by the inspect/render commands
and resolved through the consumer project's venv exactly as today
(`publication_build.py:257-259`).

### D2 — The CLI is a facade, not a rewrite

Every command delegates to code that already works. `reportkit build` calls
`publication_build.build()`; `reportkit check` calls `validate_publication()`;
`reportkit inspect` calls `inspect()`. The existing shell wrappers
(`combine.sh`, `build-section.sh`) and the direct `python3 …publication_build.py`
invocation documented at `SKILL.md:40-42` keep working unchanged. Nothing is
deprecated in Phase 1.

### D3 — Nested `publication.yaml`, with the flat form still valid

A file that declares none of the section keys (`publication`, `document`,
`profiles`, `validation`, `output`) is read as the current flat form and mapped
onto `publication:`. `publication_pipeline/example_publication/publication.yaml`
and every consumer's existing file keep working with no edit. This is what makes
the schema change safe to ship without coordinating consumer repositories.

### D4 — Engine ships schemas; publications ship data

vNext §10 (source/manuscript model) and §11 (link registry) describe files that
live in the *consumer* project. The engine provides the schema, the validator,
and the LaTeX macro; it never provides the data, and no fixture beyond
`example_publication/` may grow to hold any. This is the only reading compatible
with `references/repository-boundary.md` guardrail 1.

---

## 4. Phase 1 — the machine interface

Seven work items. W7 is independent and should land first; W1 gates the rest.

### W1 — Make the Python importable

The single structural blocker. Today there are three incompatible import styles:

1. `publication_build.py:32-34` — `sys.path.insert(0, REPO_ROOT / "python_scripts")` then bare imports with `# noqa: E402`.
2. `publication_build.py:21` and `validate-publication.py:9` — bare `from publication_validation import …`, working only because the script's own directory is on `sys.path`. **This breaks the moment either file is imported rather than executed.**
3. `publication_pipeline/tests/test_log_gate.py:4-7` — `importlib.util.spec_from_file_location`, because `check-build-log.py` is not a valid Python identifier.

**Do:**

- Create `python_scripts/reportkit/` — `__init__.py`, `cli.py`, `config.py`,
  `diagnostics.py`, `context.py`, `registry.py`, `manifest.py`. Stdlib only.
- Add an executable `reportkit` shim at repo root: resolve the repo root, put
  `python_scripts/` on `sys.path`, call `reportkit.cli.main()`.
- Rename `check-build-log.py` → `check_build_log.py`. Update its three call
  sites: `publication_build.py:236`, `.githooks/pre-commit` (via W5), and
  `test_log_gate.py:4` (which can then use a plain import).
- Fold `validate-publication.py` into `reportkit check`; update
  `.githooks/pre-commit:19` to call the CLI.
- Move `publication_config.py` into the package, leaving a one-line re-export at
  the old path so `publication_build.py:34` keeps working.

**Acceptance:** `python3 -c "import reportkit.cli"` succeeds with only
`python_scripts/` on the path; no `sys.path` mutation remains in
`publication_pipeline/scripts/`; `test_log_gate.py` uses a plain import.

### W2 — `config.py`: nested schema with a legacy fallback

**Do:** a subset-YAML loader — nested mappings by indentation, scalars typed as
`str`/`int`/`bool`, `- ` lists. No anchors, no flow style, no multi-line
scalars; anything unsupported is a parse error naming the line, matching the
existing loader's strictness.

Schema:

```yaml
publication:
  title:              # required
  subtitle: author: language:
document:
  main: class: engine:
profiles:
  draft:              # any key above, overriding it
  release:
validation:
  fail_on_undefined_refs: fail_on_missing_assets:
  overfull_hbox_threshold: underfull_badness_threshold:
output:
  directory:
```

Preserve from `publication_config.py`: `REQUIRED = ("title",)`,
`resolve_identity()`'s override-merge (CLI and `REPORTKIT_*` env beat the file),
`slugify()`, the computed defaults (`subtitle←title`, `version←"draft"`,
`left_header←f"REPORTKIT / {title.upper()}"`), and — importantly — the
**unknown key is a hard error** rule, now path-qualified so `document.engien`
fails naming `document`'s known keys rather than the whole flat set.

`validation.underfull_badness_threshold` supersedes
`check_build_log.DEFAULT_UNDERFULL_BADNESS = 4000` when set, so a publication can
tune its own gate without a CLI flag.

**Acceptance:** the current flat fixture loads unchanged and produces an
identical `resolve_identity()` result; a nested file round-trips; `--profile
release` overrides `version`; an unknown nested key fails with its dotted path;
a tab-indented file fails with a line number.

### W3 — `diagnostics.py`: the largest genuine gap

`check-build-log.py` classifies into seven coarse kinds (`fatal`, `undefined`,
`duplicate_label`, `overfull`, `underfull`, `ignored_error`, `allowlist`) and
reports `{"line": <log line number>, "kind": ..., "text": ...}`. There is no
severity, no source file, no measurement, and no ownership. Three capabilities
must be added.

**(a) Real source locations.** `-file-line-error` is already passed at
`publication_build.py:222` and then never parsed. Track the TeX log's
`(./file.tex … )` push/pop stack to attribute every diagnostic to a file, and
extract measurements from the messages that carry them:

```
Overfull \hbox (8.4pt too wide) in paragraph at lines 380--382
```

→ `amount_pt: 8.4`, `line: 380`, `line_end: 382`.

TeX wraps log output at 79 columns, so continuation lines must be joined before
matching or a message will be split mid-pattern.

**(b) Generated-file attribution.** Per §2.2, diagnostics name `body-NN.tex`,
which no author has ever edited. `render_markdown()` gains a sidecar
`body-NN.map.json`:

```json
{"source": "manuscript/04-streaming.md",
 "fragments": [{"start": 112, "end": 148, "slug": "retry-states",
                "path": "fragments/fig-retry-states.tex"}]}
```

Fragment spans are known exactly — the substitution happens line-for-line at
`publication_build.py:74-79` — so a diagnostic inside one maps back to a precise
line of an authored `.tex` fragment. **Markdown gets file-level attribution
only.** Pandoc does not emit a line map, and inventing one would be worse than
admitting the limit: an overfull box in prose reports
`manuscript/04-streaming.md` with no line, and that is the honest answer.

**(c) Ownership**, derived from `(type, file)`:

| Owner | Assigned to |
|---|---|
| `CONTENT` | anything in `manuscript/` or an unattributed `body-NN.tex`; undefined refs; duplicate labels |
| `STYLE` | anything in `reportkit*.cls`/`.sty`, including their pgfkeys `\PackageError`s |
| `ASSET` | `missing_asset`, `missing_font`, `missing_glyph` |
| `BUILD` | `latex_error`, `ignored_error` |
| `TOOLCHAIN` | warnings from third-party packages |

Categories are vNext §5's eleven **plus `ignored_error`**, which vNext omits and
the tooling spec named explicitly in A1 (`ignored error: Infinite glue shrinkage`
was one of the six defects that motivated the gate).

Preserve verbatim: the dated allowlist (`{pattern, reason, expires}`, expired
entries promoted to failures at `check-build-log.py:44-49`) and the per-project
override at `<source-root>/build-log-allowlist.json`.

**Acceptance:** a fixture log with a known overfull box in prose yields
`{"severity": "warning", "type": "overfull_hbox", "file":
"manuscript/01-fixture.md", "amount_pt": 8.4, "owner": "CONTENT"}`; the same box
inside a fragment yields `fragments/fig-fixture-flow.tex` **with a line number**;
a wrapped 79-column message is matched; both existing `test_log_gate.py` cases
still pass.

### W4 — `context.py` + `registry.py`

vNext §3's requirement is *"generate this from actual configuration rather than
maintaining duplicate documentation"*. Sources:

| Field | Derived from |
|---|---|
| `version` | `git describe --tags --always` (README: tags are authoritative), cross-checked against `\ProvidesClass` in `reportkit.cls:5` |
| `document.engine` | resolved config (W2), not asserted |
| `components.figures` | environment names parsed from `latex_templates/*.sty` + their pgfkeys families |
| `components.callouts` | `reportkit-boxes.sty:27-48` |
| `components.charts` | introspected from `reportkit_viz` |
| `commands` | introspected from the CLI's own argparse registry |

**The drift test is the point.** A test asserts the generated registry and
`SKILL.md`'s two hand-maintained inventories — the question→primitive table at
`:58-78` and the callout list at `:51` — name the same sets. Adding a primitive
without documenting it fails the build, and deleting one without updating
`SKILL.md` fails too. That is what makes "generate, don't duplicate" enforceable
rather than aspirational.

Note the registry must distinguish public names from compatibility aliases:
`reportkit-boxes.sty` defines thirteen environments, but three
(`evidence`, `limitation`, `tip` at `:46-48`) are aliases for the `*note` forms
and one is `metric`, leaving nine callouts. `SKILL.md:51` names those nine plus
`metric`. A naive count will fail the drift test for the wrong reason.

**Acceptance:** `reportkit context --json` lists the 19 diagram environments and
the 9 callouts plus `metric`, with aliases marked rather than counted; the drift
test fails when a primitive is added to a `.sty` and not to `SKILL.md`.

### W5 — The CLI facade

`doctor · context · check · build · diagnose · inspect · package`, each with
`--json` where vNext asks for it. `build` gains `--profile` and `--engine` (today
the engine is reachable only through `REPORTKIT_TEX_ENGINE`).
`--source-root`/`--output-root` keep their current defaulting on every command
that touches a publication — never into this repository.

`package` is the one new verb: take a passing combined build and assemble the
release set (PDF, manifest, `reportkit.lock`, page renders) under
`<output-root>/../output/`.

**Acceptance:** every subcommand runs against
`publication_pipeline/example_publication` with no arguments beyond
`--source-root`; `--help` on each names its delegate.

### W6 — Manifest and history

Extend `build-report.json` (bump `schema_version` to 2) with `pdf_sha256`,
`profile`, `commit`, `figures`, `tables`. Figures are countable without new
LaTeX: `reportkit-diagrams.sty:127` already emits
`\typeout{ReportKit diagram type: \rk@diagramtype}` on every `diagram`, which
also makes the stored-but-unread `type=` key load-bearing for the first time.

Copy each report to `<output-root>/history/<build-id>.json` — the `build_id`
(`f"{mode}-{stamp}"`) is already computed at `publication_build.py:219` and
currently discarded.

**Acceptance:** two consecutive builds leave two history files; `pdf_sha256`
matches `sha256sum` on the emitted PDF; `figures` equals the fixture's sentinel
count.

### W7 — Wire up the orphaned tests (do this first)

`publication_pipeline/tests/` is executed by nothing — not
`scripts/acceptance_check.sh`, not `.githooks/pre-commit`. Its three test files
have been running only when someone remembers to invoke pytest by hand.

**Do:** add the directory to `acceptance_check.sh:71`'s pytest invocation;
convert `test_validation.py` from `unittest.TestCase` to pytest so one runner
covers both suites; add the missing pandoc skip-guard to
`test_template_features.py`, which currently fails hard rather than skipping when
pandoc is absent.

**Acceptance:** `bash scripts/acceptance_check.sh` reports the pipeline tests;
the suite skips cleanly with no pandoc installed.

---

## 5. Phases 2–4

**Phase 2 — QA depth.** Extend `inspect_pdf.py` with the checks vNext §7 lists
and the tooling spec's D6 already authorised on PyMuPDF: bookmarks, font
metadata, page dimensions, blank-page detection, and near-margin content. Reuse
`tests/geometry.py`'s `word_boxes`, `node_rects`, and `stream_contains` rather
than writing new PDF-probing helpers. Keep the heuristics simple — vNext §8 says
so explicitly, and the tooling spec rules out pixel-diff regression testing
because font rendering varies by platform.

**Phase 3 — Authoring.** Engine-side schema and validator for the
source/manuscript model (§10) and link registry (§11), plus an `\RKLink{key}`
macro rendering by link class; the data files live in the consumer project per
D4. Update `SKILL.md`'s build section to route through the CLI, which also
retires the `pdftoppm` instruction at `:304`.

**Phase 4 — Self-improvement.** `reportkit analyse-history` over W6's history
directory: recurring diagnostic types, repeated allowlist entries, and
candidates for promotion into primitives. Cheap once W6 exists, worthless before.

---

## 6. Sequencing and verification

```
W7 (test wiring)  ── independent, land first

W1 (package) ──┬──> W2 (config) ─────┐
               ├──> W3 (diagnostics) ─┼──> W5 (CLI) ──> W6 (manifest)
               └──> W4 (context) ─────┘

Phase 2 after W5.  Phase 3 after W4 (needs the registry).  Phase 4 after W6.
```

Branch fresh from `main`. Do **not** use the `tooling` branch — see finding 7.

Every gate runs locally; hosted CI remains a non-goal, per the tooling spec.

```bash
bash scripts/acceptance_check.sh --require-tex
python3 -m pytest tests publication_pipeline/tests -q
./reportkit doctor --require full-build
./reportkit context --json
./reportkit build --source-root publication_pipeline/example_publication
./reportkit diagnose --json
```

The end-to-end proof is the last one run against a deliberately broken fixture:
widen a line in `manuscript/01-fixture.md` past the text block, rebuild, and
confirm the diagnostic reports `manuscript/01-fixture.md` with
`"owner": "CONTENT"` — not a line number in `publication.log`. If it still
reports a log line, W3 is not done.

Because W1 renames scripts the pre-commit hook calls, run the hook path
explicitly before merging:

```bash
git config core.hooksPath .githooks && git commit --dry-run
```

---

## 7. Risks

**The subset-YAML parser is the only genuinely new, error-prone code.** Every
other work item wraps or extends something that already works. Mitigate with a
round-trip fixture suite covering nesting depth, comments, quoted values,
booleans, and the legacy flat form, and keep the grammar deliberately small —
the moment it needs anchors or flow style, the right answer is to revisit D1
rather than grow the parser.

**The log parser is sensitive to TeX's 79-column wrapping.** A message split
across lines will not match. Join continuations before classifying, and fixture
a wrapped message.

**Renaming touches the commit hook.** `.githooks/pre-commit` is opt-in
(`CONTRIBUTING.md:12-16`), so a broken rename can pass unnoticed for anyone who
has not enabled it. The dry-run above is not optional.

---

## 8. Findings recorded, not fixed

Surfaced during the audit. None is in scope for Phase 1; each is real.

1. **No `LICENSE` file at repo root.** `README.md:86`,
   `references/licensing.md:8`, and the tooling spec `:501` ("The existing root
   `LICENSE` is not replaced or modified") all reference one, and
   `metadata/licenses.yml` declares `GPL-3.0-or-later`. The file is absent.
   Fix independently — it is a licensing defect, not a tooling one.
2. **`SKILL.md:304` prescribes `pdftoppm`**, which tooling-spec D6 explicitly
   bans ("No build step or documented workflow invokes `pdfinfo`, `pdffonts`,
   `pdftotext`, `pdfplumber`, or `pypdf`") and `TODOS.md:39` records as not
   installed. Fixed in Phase 3.
3. **`CHANGELOG.md:31` cites `VISUAL_GRAMMAR_SPEC.md`**, which is not in the
   tree.
4. **`--workers` is accepted and inert.** `publication_build.py:281` declares it;
   `--mode sections` loops serially at `:289-303`. `build-all.sh` passes
   `REPORTKIT_BUILD_WORKERS`. Either wire it up or remove the flag — the tooling
   spec's F2 says measure first.
5. **`render_visuals.py` duplicates `publication_build.render_markdown()`** with
   a divergent sentinel regex. One should be the library and the other its
   caller.
6. **Two independent log gates.** `check-build-log.py` and
   `acceptance_check.sh:105-110`'s four grep signatures (`Illegal unit of
   measure`, `Undefined control sequence`, `cannot be found`, `Emergency stop`)
   classify the same logs by different rules. W3 should absorb the signatures.
7. **`TODOS.md` P0-1 is stale.** It asks to re-cut `tooling` from `main` because
   it is behind. `git rev-list --left-right --count main...tooling` returns
   `34 0` — `tooling` has **no unique commits**, and
   `references/migrating-content-branches.md` already dispositions it as
   "Superseded and stale… then delete". Deleting it closes P0-1; vNext work
   branches fresh from `main` regardless.
8. **B8 tagging is already decided.** `references/accessibility-tagging.md`
   records a **no-go** with its spike log (`LaTeX Error: No support files for
   \DocumentMetadata found.`). vNext should not reopen it.
