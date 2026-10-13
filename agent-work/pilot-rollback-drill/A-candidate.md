# Task A: identify the candidate

- **Prerequisites:** none.
- **Base:** `92c51e6c69d7ed29ee6e879733ad4b801a82814e` (`main`).
- **Read first:** `PLAN.md`, `CONTRACT.md`.

## Work

1. Fetch; record the `main` head, which is the candidate.
2. List the commits since `v0.1.0-alpha.12` (`c7ad3c3`). Each must come from an independently reviewed, merged PR (expected: PR #15 only, test-only).
3. Confirm that Validate CI is green on the candidate.

No code changes. If `origin/main` is no longer `92c51e6`, list every commit since alpha.12 anyway, so B can review the whole list.

The coordinator's evidence record for A carries `candidateSha` equal to the candidate and `taskStatus: "complete"`; without it the live gate stays `GATED`.

## Result

`results/A.md`: the candidate SHA, the commit list with PR numbers, and the CI run.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/rollback-drill-records`.

## Forbidden

Any change to the repository's code, docs or workflows.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
