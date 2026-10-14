# Task V: rollback and verification

- **Prerequisites:** J `failed` with `liveStateChanged` not `false`.
- **Read first:** `CONTRACT.md` "Rollback (V)", `docs/RELEASING.md`.

## Work

1. Make sure the run is `completed` (cancel and wait if not).
2. Read the actual state (tag via API and `git ls-remote`; releases via the authenticated list, drafts included) and follow the matching row of the matrix.
3. Give the owner one deletion at a time with the exact link; after the owner reports it done, verify it through the API before the next. Never ask the owner to act on any other release or tag; if anything else differs from the baseline, stop and ask.
4. Schedule the read-only check-ins (T+30 minutes; T+24 hours if items remain); switch them off once verified.
5. Final verification as `CONTRACT.md` lists it; end state "stopped after verified rollback".
6. Records: divergence proof, secrets scan, records PR (only `agent-work/release-alpha13/` and a `docs/PILOT-HISTORY.md` "Pilot 6" entry), independent review, the owner's go-ahead, landing per `COORDINATOR.md` "Commands that move refs". Record V `complete` before the merge; report the merge and a fresh check afterwards.

If any verification fails, record V `failed`, stop and report; K stays blocked.

## Result

`results/V.md`.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha13-records`.

## Forbidden

Any action on another release or tag; merging without review and the owner's go-ahead.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
