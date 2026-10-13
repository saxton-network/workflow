# Task K: final reconciliation

- **Prerequisites:** J `complete` with `runtimeAcceptance` `PASS`.

## Work

1. Verify the tag, the release, and `main` agree with the deployed source.
2. Check the records for secrets.
3. Open the records PR (only `agent-work/pilot-alpha11/` and a `docs/PILOT-HISTORY.md` entry), with divergence proof of its changed paths from `git --no-replace-objects -c core.commitGraph=false diff --no-renames --no-relative --ignore-submodules=none --name-only -z <source> <records head>`, run with no inherited `GIT_*` variables. The helper is expected to report this as a protected change, because the records add frozen configuration files; that is recorded as a pilot finding, not a stop.
4. Independent review of the records PR; merge on the owner's go-ahead; recheck `main`.

## Result

`results/K.md`: final refs, release state, divergence proof, PR and review, pilot findings.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha11-records`, and nothing under `agent-work/pilot-alpha11/` is ever committed to the implementation or fix branch.

## Forbidden

Changing the release or tag; merging the records PR without review and the owner's go-ahead.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
