# Troubleshooting

## Recover the publication state

Every command reloads the target and intent from the consumer project. After a context reset, run:

```bash
reportkit status --source-root <publication-project> --json
```

Follow the returned `next_step`. Target choice, source mode, request, build report, and review state are stored with that project.

## Check the build environment

On a fresh Debian/Ubuntu host, run `scripts/setup_tex.sh` once before authoring or building. It installs TeX and fonts and compiles editorial and institutional LuaLaTeX smoke documents. On an existing installation, run `scripts/setup_tex.sh --check` to compile the smoke documents without installing packages.

Run `reportkit doctor --require full-build` from the consumer project's pinned Python environment before promising a compiled PDF. Without `--require`, read and report the actual `MODE:` line:

- **FULL BUILD** means the required TeX engines and fonts work.
- **SOURCE BUILD + FIGURES** means TeX is available but a required font is missing.
- **SOURCE BUILD** means the host can prepare source but cannot compile it.

Windows and hosts without the native toolchain can use `scripts/reportkit_container.py` with the pinned image digest. See [docker-workflow.md](docker-workflow.md) and [font-setup.md](font-setup.md).

## Build and diagnose

Build through the project CLI so source-mode selection, target checks, composition audits, engine choice, diagnostics, rendering, and the build manifest share one path:

```bash
reportkit build --source-root <publication-project> --json
```

The declared look selects the required TeX engine. If the diagnostic is `RK_ENGINE_DOWNGRADE`, install or repair the required engine and keep the declared look. Read the diagnostic's `next_step` and the build `.log` before changing source. A failed build is evidence to fix its reported cause, not to remove a theme or substitute a different target.

## Review the output

Render the pages that changed, then inspect every rendered page before delivery:

```bash
reportkit render --source-root <publication-project> --pages 1 --json
reportkit review --source-root <publication-project> --visual-review done
```

Check for clipped text, overlapping labels, broken figures, missing sources, poor page breaks, and meanings carried only by color. When the host cannot view the rendered pages, record `visual_review=unavailable` and state that in delivery.

## Engine developers

Raw engine calls are for isolated TeX-engine debugging. Normal publication builds use `reportkit build`.

```bash
lualatex -interaction=nonstopmode -halt-on-error report.tex
```

Use the engine required by the selected theme. Repeat a raw compile only when checking references or captions, and inspect the `.log` after a failure.

## Environment notes

Some cloud execution sandboxes reset their filesystem between sessions. Keep the source and state in the consumer project and reload them with `reportkit status` at the beginning of a new session.
