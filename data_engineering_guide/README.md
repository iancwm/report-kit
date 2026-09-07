# Data Engineering Guide build harness

The guide's manuscript and diagram fragments are maintained on the
`data-engineering-guide-content` branch. This checkout contains the reusable
tooling, a small fixture, and the release gate.

## Integration model

Build the publication from one assembled checkout:

1. Start from the current ReportKit tooling branch (or `main` after it lands).
2. Merge `data-engineering-guide-content` into that checkout.
3. Run `python3 scripts/validate-guide.py` from this directory.
4. Run `scripts/combine.sh` as the release build.

The content branch supplies `manuscript/`, `fragments/`, and editorial files;
this harness supplies `scripts/`, `templates/`, and the locked renderer. No
release claim is made from a checkout that contains only one half.

## Commands

```bash
bash scripts/setup.sh
python3 scripts/validate-guide.py
bash scripts/build-section.sh manuscript/01-introduction.md
bash scripts/combine.sh --version v1.0.0 --title "Data Engineering Guide" --author "ReportKit"
```

`combine.sh` is the canonical full-document build and is driven by
`manuscript/order.txt`. It validates the guide before Pandoc runs, compiles
twice with `-file-line-error`, applies the strict log gate, renders pages into
an atomic directory, and writes `build/combined/build-report.json`.

The isolated section command is an author-feedback loop, not a release
artifact. `requirements.txt` pins the one PDF-inspection dependency used by
the harness: PyMuPDF.
