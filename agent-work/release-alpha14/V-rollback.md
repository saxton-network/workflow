# Task V: rollback and verification

- **Prerequisites:** J `failed` with `liveStateChanged` not `false`.
- **Read first:** `CONTRACT.md` "Rollback (V)", `docs/RELEASING.md`.

## Work

1. Make sure the run is `completed` (cancel and wait if not).
2. Read the actual state (tag via API and `git ls-remote`; releases via the authenticated list, drafts included), with the clients `CONTRACT.md` "Evidence clients" names, and follow the matching row of the matrix.
3. Give the owner one deletion at a time with the exact link; after the owner reports it done, verify it through the API before the next. Never ask the owner to act on any other release or tag; if anything else differs from the baseline, stop and ask.
4. Keep the read-only check-ins that J scheduled running until the final verification; then switch them off.
5. Final verification as `CONTRACT.md` lists it; end state "stopped after verified rollback".
6. Records: divergence proof (`classify_divergence` is expected to report `protected_change` only for the frozen files under `agent-work/release-alpha14/`, which the spec allows after a verified rollback; any other protected path stops the landing), secrets scan, records PR (only `agent-work/release-alpha14/` and a `docs/PILOT-HISTORY.md` "Pilot 8" entry), independent review, the owner's go-ahead, landing with a local `--no-ff` merge under the coordinator's no-reply identity per `COORDINATOR.md` "Commands that move refs" (never GitHub's merge API). Record V `complete` before the merge; report the merge and a fresh check afterwards.

If any verification fails, record V `failed`, stop and report; K stays blocked.

## Result

`results/V.md`.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha14-records`.

## Forbidden

Any action on another release or tag; merging without review and the owner's go-ahead.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
