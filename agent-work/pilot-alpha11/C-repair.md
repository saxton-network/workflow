# Task C: repair (conditional)

- **Prerequisites:** B `findings`.
- **Base:** the reviewed candidate. **Branch:** `pilot/alpha11-fix`, descending from it.
- **Owned paths:** the same as task A.

## Work

Fix each in-scope finding from the latest B result, with a test that fails before and passes after. Then B re-reviews the repaired commit.

## Result

`results/C-<n>.md`: repaired candidate commit, findings addressed, checks.

## Forbidden

Anything outside the findings; changes to fingerprint computation, the threat model, the spec, or the release workflow.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
