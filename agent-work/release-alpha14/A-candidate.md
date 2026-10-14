# Task A: identify the candidate

- **Prerequisites:** none.
- **Base:** `02c771a7c7d71e2303c186d0c150e903a524e949` (`main`).
- **Read first:** `PLAN.md`, `CONTRACT.md`.

## Work

1. Fetch; record the `main` head, which is the candidate.
2. List the commits since `v0.1.0-alpha.13` (`84d826a`), grouped by merge, with PR numbers. Expected: PRs #22, #24 and #25.
3. Confirm Validate CI is green on the candidate.

No code changes. If `origin/main` is no longer `02c771a`, stop and report: the main freeze has not started, but an unexpected merge needs the owner's attention.

## Result

`results/A.md`: the candidate SHA, the commit list and the CI run. The coordinator's evidence record carries `candidateSha` and `taskStatus: "complete"`.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha14-records`.

## Forbidden

Any change to the repository's code, docs or workflows.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
