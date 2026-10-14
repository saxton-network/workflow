# Task A: identify the candidate

- **Prerequisites:** none.
- **Base:** `84d826a40b8f8567439ab15eb270a1a752f92a82` (`main`).
- **Read first:** `PLAN.md`, `CONTRACT.md`.

## Work

1. Fetch; record the `main` head, which is the candidate.
2. List the commits since `v0.1.0-alpha.12` (`c7ad3c3`), grouped by merge, with PR numbers. Expected: PRs #15–#21.
3. Confirm Validate CI is green on the candidate.

No code changes. If `origin/main` is no longer `84d826a`, stop and report: the main freeze has not started, but an unexpected merge needs the owner's attention.

## Result

`results/A.md`: the candidate SHA, the commit list and the CI run. The coordinator's evidence record carries `candidateSha` and `taskStatus: "complete"`.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha13-records`.

## Forbidden

Any change to the repository's code, docs or workflows.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
