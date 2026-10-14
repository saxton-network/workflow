# Task C: repair (conditional)

- **Prerequisites:** B `findings`, set in the manifest before dispatch.

## Work

1. Fix each in-scope finding in an ordinary PR from a branch off the candidate. The same reviewer reviews it; the owner gives the go-ahead to merge.
2. Merge with a local `--no-ff` merge under the coordinator's no-reply identity, following `COORDINATOR.md` "Commands that move refs" (never GitHub's merge API). The new `main` head (the merge commit) is the new candidate.
3. If the repair changed `scripts/agent-task.py`, merge `main` into `pilot/alpha14-records` before running the helper again.
4. `CONTRACT.md` may change only before R; record each change.

For a second round, the coordinator sets B back to `findings` and C back to `pending` in the same records commit. If B is not clean after two repair rounds, stop and report to the owner.

## Result

`results/C-n.md`: the PR, the new `main` head (`candidateSha`), and the checks.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha14-records`.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
