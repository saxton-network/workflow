# Task C: repair (conditional)

- **Prerequisites:** B `findings`.
- **Base:** the reviewed candidate. **Branch:** `pilot/alpha11-fix`, descending from it.
- **Owned paths:** the same as task A.
- **Read first:** as for task A, plus the latest B result.

## Work

Fix each in-scope finding from the latest B result, with a test that fails before and passes after. Then B re-reviews the repaired commit. Only one repair cycle is allowed: if the re-review still has findings, the run stops.

## Validation

- Baseline `bash scripts/validate-repository.sh` at the reviewed candidate, before edits.
- New tests fail on the reviewed candidate and pass on the repaired commit (Python 3.12).
- `bash scripts/validate-repository.sh` passes on Python 3.11, 3.12 and 3.13; Validate CI green on the pushed repaired commit.

## Result

`results/C-<n>.md`: repaired candidate commit, findings addressed, checks.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha11-records`, and nothing under `agent-work/pilot-alpha11/` is ever committed to the implementation or fix branch.

## Forbidden

Anything outside the findings; changes to fingerprint computation, the threat model, the spec, or the release workflow.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
