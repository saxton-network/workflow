# Task K: final reconciliation

- **Prerequisites:** J `complete` with `runtimeAcceptance` `PASS`.

## Work

1. Verify the tag, the release, and `main` agree with the deployed source.
2. Check the records for secrets.
3. Open the records PR (only `agent-work/pilot-alpha11/` and a `docs/PILOT-HISTORY.md` entry), with divergence proof of its changed paths.
4. Independent review of the records PR; merge on the owner's go-ahead; recheck `main`.

## Result

`results/K.md`: final refs, release state, divergence proof, PR and review, pilot findings.

## Forbidden

Changing the release or tag; merging the records PR without review and the owner's go-ahead.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
