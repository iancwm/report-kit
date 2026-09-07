# Migrating content branches out of report-kit

Several branches in this repository carry an actual publication's manuscript
or build state. Per [repository-boundary.md](repository-boundary.md), none of
that belongs here going forward. This note records the branches that exist
today, what happens to each, and the extraction recipe — it does not delete
anything. Deleting a branch is a human decision; make it explicitly, after the
extraction below is verified, not as a side effect of reading this file.

## Branch disposition

| Branch | Carries | Disposition |
|---|---|---|
| `data-engineering-guide-content` | 13 manuscript files + 14 diagram fragments (3 commits ahead of `main`) | **Extract** to a new consumer repository — this is the one branch with real, unique publication content. |
| `data-engineering-guide` | An earlier cut of the build harness, superseded by `publication_pipeline/` on `main` | Superseded. Diff against `main` to confirm no unique commits, then delete. |
| `tooling` | An older script set, 19 commits behind `main` | Superseded and stale. Confirm no unique commits, then delete. |
| `backup/pre-split` | A pre-split snapshot, 22 ahead / 30 behind `main` | A backup of a since-superseded state. Confirm nothing unique is needed, then delete. |
| `origin/report/pwm-candidacy-verification` | A `reports/` directory with a single analysis PDF/report, 1 commit ahead of `main` | **Extract** the `reports/` content to a consumer repository (or discard, if the report is no longer wanted), then delete. |

Re-run `git log --oneline main..<branch>` and `git log --oneline <branch>..main`
before deleting anything — branch tips move, and this table is a snapshot.

## Extraction recipe

For a branch that carries real content (`data-engineering-guide-content`,
`origin/report/pwm-candidacy-verification`):

1. **Split the content out**, preserving history:
   ```bash
   git checkout <branch>
   git subtree split --prefix=<content-dir> -b extracted-content
   # or, for a cleaner result on a large history: git filter-repo --subdirectory-filter <content-dir>
   ```
2. **Create the new consumer repository** and pull the split history in:
   ```bash
   mkdir ../my-publication && cd ../my-publication && git init
   git pull /path/to/report-kit extracted-content
   ```
3. **Add the structure the harness expects** (see
   [repository-boundary.md](repository-boundary.md#recommended-consumer-project-structure)):
   move manuscript files into `manuscript/`, fragments into `fragments/`, add
   `assets/`, `figures/`, and a `publication.yaml` with at least a `title`.
4. **Build against a report-kit clone** to prove the extraction is complete:
   ```bash
   python3 <report-kit-clone>/publication_pipeline/scripts/publication_build.py \
     --mode combined --source-root . --output-root ./build
   ```
5. **Verify** the resulting PDF matches what the old branch produced (page
   count, diagnostics, content) and that `reportkit.lock` was written at the
   project root.
6. **Delete the old branch** in report-kit, locally and on `origin`, once the
   new repository is confirmed working and the team has switched over.

For a branch that is superseded tooling (`data-engineering-guide`, `tooling`,
`backup/pre-split`), skip straight to confirming no unique commits remain
(`git log --oneline main..<branch>`) and deleting it — there is nothing to
extract.

## Out of scope here

This note documents the recipe and the current branch inventory. It does not
perform any extraction or deletion — that is follow-up work for a human to
run and confirm, branch by branch.
