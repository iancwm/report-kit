# ReportKit Build Regression Remediation Specification

**Status:** Implemented on `main`; content-branch adoption pending

**Scope:** Shared ReportKit tooling on `main`

**Observed:** 2026-09-06 during the Data Engineering Guide combined build

## Problem Statement

The canonical guide build exposed two defects that make an otherwise useful
failure difficult to prevent and diagnose:

1. `reporttree` treats node labels as raw TeX. A normal identifier such as
   `event_date` therefore reaches a TikZ node with an unescaped underscore and
   fails with `Missing $ inserted`. The error is reported at
   `\end{reporttree}`, not at the label that caused it.
2. `guide-build.py` reports a failed TeX log inside its temporary
   `.<output>.run-*` directory. Its failure handler copies that directory to the
   stable output directory and removes the temporary directory, so the path in
   both stdout and `build-report.json` is invalid by the time a user sees it.

The observed guide build failed in the new partition-pruning figure. The other
eight instructional section builds completed successfully, so the first issue
is isolated to the tree-label contract rather than a general guide build
failure.

## Goals

- Provide a documented, TeX-safe way to place literal identifiers in semantic
  diagram labels.
- Preserve the existing ability to use deliberate TeX formatting in labels,
  including manual line breaks.
- Ensure every failed build report links to an artifact that still exists after
  the build process exits.
- Make both regressions executable acceptance cases on `main`.

## Non-goals

- Do not move manuscript or figure content onto `main`.
- Do not suppress TeX errors, weaken the strict log gate, or treat a failed
  first TeX pass as a successful build.
- Do not redesign the tree layout, change node spacing, or introduce a general
  Markdown parser inside TeX.
- Do not retain every temporary build directory indefinitely.

## Fix 1: Safe Literal Runs in Diagram Labels

### Decision

Add a small, documented inline macro to the shared diagram API:

```latex
\rkcode{event_date}
```

`\rkcode{...}` is for literal identifiers and short technical tokens used
inside a semantic label. It must render ordinary identifier characters such as
`_`, `-`, `.`, `/`, `:`, and `=` without requiring authors to know the TeX
escaping rules for underscores. Its result must remain safe when a primitive
stores the label for deferred rendering, as `reporttree` does. It is not a
general verbatim parser: `%`, `#`, braces, and backslashes are outside this
identifier-token contract.

The intended guide-side use is:

```latex
\root{\rkcode{event_date} = target}
```

This is deliberately an explicit literal run instead of automatic escaping of
all `\root`, `\branch`, and `\layer` arguments. Existing diagrams may use
intentional TeX, such as `\\` for a controlled line break; automatically
detokenizing every label would silently break that supported behavior.

### Implementation

1. Define the robust `\rkcode` macro in the shared ReportKit style layer that
   owns diagram text styling. Its implementation should use a literal-text
   mechanism (for example, a protected `\detokenize`-based implementation) and
   the established monospaced or technical-label font treatment.
2. Ensure the macro is protected while `reporttree` snapshots labels with
   `\protected@edef`; it must not expand into unsafe raw tokens during storage.
   Literal runs are display-only and must be excluded from the tree's
   control-sequence-based parent-reference lookup.
3. Document the macro and its purpose in [SKILL.md](../SKILL.md). Specify that
   a tree's comma-delimited child list remains structural input, not a direct
   label argument: use `\rkcode` in `\root{...}` or a branch label, rather
   than as an item in that list.
4. Add the literal-run example to the visual grammar acceptance fixture near
   the existing `reporttree` example.

### Compatibility Contract

- Existing plain-language labels continue to render unchanged.
- Existing raw TeX labels continue to work unchanged.
- `\rkcode` may be used in direct primitive label arguments whose values are
  ultimately rendered as node text, including tree roots and branch labels,
  architecture cards, flow steps, network nodes, and swimlane steps. It is not
  supported in a tree's comma-delimited child-list DSL.
- `\rkcode` is not a node identifier or a parent reference. Tree parent names
  remain simple unique DSL identifiers, as required by `\branch[parent]{...}`.

### Acceptance Criteria

- The visual grammar acceptance document compiles with
  `\root{\rkcode{event_date} = target}` and produces no `Missing $ inserted`
  error.
- A fixture covers a literal identifier with an underscore inside `\rkcode`.
- The existing manual-wrap example using `\\` still compiles and retains its
  line break.
- The macro is documented with an example and does not require a manuscript
  change on `main`.

## Fix 2: Stable Paths for Failed Build Artifacts

### Decision

Build errors must name the stable retained output path, never the transient
staging path. For a combined build, the first-pass log must be reported as:

```text
data_engineering_guide/build/combined/pass-1.log
```

For an isolated section build, it must be reported as:

```text
data_engineering_guide/build/isolated/<section>/pass-1.log
```

The failure handler may continue to stage atomically and clean up the temporary
directory after copying its artifacts to the stable output directory.

### Implementation

1. In `build_one`, compute each public artifact path from `output_dir` before
   invoking the command. Use that public path in `BuildFailure` messages and in
   `build-report.json`.
2. Preserve the existing temporary path only for internal process execution;
   do not expose it in user-facing messages, reports, or JSON diagnostics.
3. When a TeX pass fails, copy the pass log and generated TeX/source artifacts
   to `output_dir` before emitting the final error. Assert that the named log
   exists after the copy completes.
4. For failures before a log exists, report the stable
   `output_dir/build-report.json` path instead of inventing a log location.
5. Keep the successful-build atomic replacement behavior unchanged.

### Acceptance Criteria

- A controlled first-pass failure produces a non-zero exit code.
- Its console message and `build-report.json` contain only the stable output
  path for `pass-1.log`.
- That path exists and contains the original TeX command output after the
  process exits.
- No user-facing diagnostic contains `/.combined.run-` or
  `/.<section>.run-`.
- A successful combined build still writes its report and PDF through the
  existing atomic replacement path.

## Test Plan

Add focused tests rather than relying solely on a full guide build:

1. Extend `latex_templates/examples/visual_grammar_acceptance_test.tex` with
   literal technical text in a `reporttree` node and run the existing TeX
   acceptance command.
2. Add a unit or subprocess test for `guide-build.py` that injects a failing
   `pdflatex` command. It must assert the exit status, retained log content,
   stable path in the exception/report, and removal of the temporary path from
   user-facing diagnostics.
3. Run the existing Python test suite and strict log-gate tests.
4. In a content worktree after the main change lands, replace the failing tree
   label with `\rkcode{event_date}` and run the canonical combined guide build.
   This integration check belongs to the content branch and must not add its
   manuscript files to `main`.

## Rollout and Ownership

Implement and review this specification on `main` because both changes are
shared tooling behavior. After it lands, rebase the publication-content branch
onto `main`, adopt `\rkcode{event_date}` in the partition-pruning fragment,
and rerun the guide build. The known allowlisted longtable diagnostic, caption
`hypcap` warnings, and font-substitution warnings remain separate follow-up
items; this change must not expand their allowlist or hide them.
