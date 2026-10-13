# Task J: live deployment (human gate)

- **Prerequisites:** R `complete` with `readinessVerdict` `PASS`; the owner's explicit "y" to the concrete preview showing the actual source SHA and fingerprint (built from `PLAN.md` "Live preview").
- **Read first:** `CONTRACT.md`, `PLAN.md` "Live preview".
- The coordinator records the approval record (`taskStatus: "in_progress"`, approval reference, source, fingerprint) and confirms the helper shows `READY` before step 1. `READY` is a handoff only, not permission.

## Work

1. Recheck `origin/main`, tag and release absence, immutable-releases setting, and every frozen file hash.
2. Dispatch exactly the frozen inputs; find the single matching run (if there is not exactly one, stop); if its `head_sha` is not the source, cancel it.
3. Runtime acceptance: every check in `PLAN.md` under "Verification".
4. On the first failed check, stop and follow the rollback in `CONTRACT.md`.

## Result

`results/J.md`: approval reference, rechecks, run ID and `head_sha`, every acceptance check with its outcome, rollback if any.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha11-records`, and nothing under `agent-work/pilot-alpha11/` is ever committed to the implementation or fix branch.

## Forbidden

A second dispatch, any input other than the frozen ones, or retrying under the same version.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
