# Task C: repair (conditional)

- **Prerequisites:** B `findings`, set in the manifest before dispatch.

## Work

1. Fix each in-scope finding in an ordinary PR from a branch off the candidate. The same reviewer reviews it; the owner gives the go-ahead to merge.
2. Merge following `COORDINATOR.md` "Commands that move refs". The new `main` head (the merge commit) is the new candidate.
3. If the repair changed `scripts/agent-task.py`, merge `main` into `pilot/alpha13-records` before running the helper again.
4. `CONTRACT.md` may change only before R; record each change.

For a second round, the coordinator sets B back to `findings` and C back to `pending` in the same records commit.

## Result

`results/C-n.md`: the PR, the new `main` head (`candidateSha`), and the checks.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha13-records`.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
