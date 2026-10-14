# Task K: final reconciliation

- **Prerequisites:** J `complete` with `runtimeAcceptance` `PASS`.

## Work

1. Verify: `main` equals the source, or is a proven additive descendant classified as `COORDINATOR.md` requires (stop if it is not); the alpha.14 tag is a lightweight ref at the source; the release and its two assets match the frozen hashes; every other tag and release matches the baseline.
2. Secrets and privacy scan of the records.
3. Records PR (only `agent-work/release-alpha14/` and a `docs/PILOT-HISTORY.md` "Pilot 8" entry) with divergence proof. `classify_divergence` is expected to report `protected_change` only for the frozen files under `agent-work/release-alpha14/`; any other protected path stops the landing.
4. After independent review and the owner's go-ahead, land it with a local `git merge --no-ff` under the coordinator's no-reply identity, pushed as a fast-forward (never GitHub's merge API), following `COORDINATOR.md` "Commands that move refs". Verify GitHub marks the PR merged.

Record K `complete` before the merge; report the merge and a fresh check of `main` and the release afterwards.

## Result

`results/K.md`.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha14-records`.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
