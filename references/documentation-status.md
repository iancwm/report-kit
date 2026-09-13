# Documentation Status and PR Directive

Specs and plans are execution records, while `TODOS.md` is the current index
and open-work rollup. A pull request that changes implementation is incomplete
until its documentation status is synchronized.

## Required PR-creation workflow

When creating a PR against `main`, automatically do the following before the
PR is considered ready:

1. Identify the base branch and inspect `git log <base>..HEAD --oneline`,
   `git diff <base>...HEAD --name-only`, and working-tree changes.
2. Map changed files to affected specs and plans. Use their acceptance
   criteria and file/line evidence; do not infer status from commit messages
   alone.
3. Update every affected spec or plan's `**Status:**` and `**Last updated:**`
   lines. Record what landed, what remains, and any verification limits.
   Preserve older baselines as historical notes.
4. Update `TODOS.md`: the document row, the open-work rollup when applicable,
   and a dated history entry covering completed and remaining work.
5. Include the spec/plan and `TODOS.md` updates in the same PR. If no tracked
   spec or plan is affected, add a `TODOS.md` history note explaining why no
   status changed.
6. Run `git diff --check` and verify that every `TODOS.md` status row points to
   a real document and matches that document's current status.

This directive applies at PR creation time, not as a post-merge cleanup.
