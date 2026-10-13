# Task J: live deployment (human gate)

- **Prerequisites:** R `complete` with `readinessVerdict` `PASS`; the owner's explicit "y" on the preview in `PLAN.md` ("Live preview").
- The helper reporting `READY` is a handoff only, not permission.

## Work

1. Recheck `origin/main`, tag and release absence, immutable-releases setting, and every frozen file hash.
2. Dispatch exactly the frozen inputs; find the single matching run; if its `head_sha` is not the source, cancel it.
3. Runtime acceptance: every check in `PLAN.md` under "Verification".
4. On the first failed check, stop and follow the rollback in `CONTRACT.md`.

## Result

`results/J.md`: approval reference, rechecks, run ID and `head_sha`, every acceptance check with its outcome, rollback if any.

## Forbidden

A second dispatch, any input other than the frozen ones, or retrying under the same version.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
