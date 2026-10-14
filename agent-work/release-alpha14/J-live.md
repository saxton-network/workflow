# Task J: live deployment (human gate)

- **Prerequisites:** R `complete` with `PASS`; the owner's explicit "y" to the concrete preview, confirming availability to delete within 30 minutes. A "y" without that availability is "n".
- **Read first:** `AGENTS.md`, `PLAN.md` "Live preview (J)" and "Approval record (J)", `CONTRACT.md`.
- The coordinator writes `results/J-approval.md` as `COORDINATOR.md` "Approval records" and `PLAN.md` require, records J `in_progress`, and confirms the helper shows `READY` (a handoff only).

## Work

1. **Recheck, seconds before dispatch:**
   - `origin/main` equals the source; record that tip, since the run's `head_sha` is compared with it;
   - the source worktree is clean;
   - no alpha.14 tag or release (drafts included);
   - immutable releases off and no rulesets;
   - every frozen file hash, and the fingerprint recomputed from the frozen data equals the approved one;
   - the local ZIP rebuilt from the source still has the frozen SHA-256;
   - alpha.13's asset digests and the rest of the baseline tag and release lists still equal `R-baseline.json`;
   - the latest `release.yml` run ID.

   Each read uses the client `CONTRACT.md` "Evidence clients" names. Read the output; if anything differs, dispatch nothing, leave J `in_progress`, stop and ask the owner.
2. **Dispatch** `R-dispatch-inputs.json` once, as a tool call of its own. If the call errors or no single new run appears, never dispatch again: re-list for up to 2 minutes, then stop and ask the owner.
3. **Wait** up to 12 minutes for the run to complete; if still running, cancel, wait for `completed`, record J `failed`.
4. **Wrong `head_sha`:** follow `CONTRACT.md` "A run built from the wrong commit".
5. **Runtime acceptance:** checks 1–3 of `CONTRACT.md`, stopping at the first failure, within its one 10-minute window and with its evidence clients. Evidence that fails a check is never re-read to get a different answer.
6. **On failure:** make sure the run is `completed`; record J `failed` (manifest and evidence) with `runtimeAcceptance: "FAIL"` and `liveStateChanged` per `CONTRACT.md` (with the one-line reason when `false`; a missing read or a client disagreement is `null`); tell the owner plainly what exists and what happens next. Unless `false` is proven, schedule the read-only check-ins now (T+30 minutes; T+24 hours if items remain); V switches them off.

## If `liveStateChanged: false` is proven

- Do not dispatch V. Record V `failed` with "rollback not needed" and the reason; K stays blocked.
- Ask the owner how to continue. If the owner chooses a retry, the main freeze continues into a new readiness cycle.
- Land the records as `K-reconcile.md` steps 2–4 describe (secrets scan, divergence proof, independent review, the owner's go-ahead, ref-move gates). The owner chooses whether to land them before or after a retry; landing them first moves `main`, so a retry then restarts at tasks A and B. Record the expected `protected_change` as a deviation note.
- End state: "stopped; nothing published, proven".

## Result

`results/J.md`: the recheck, the run ID and `head_sha`, each check's outcome, and `liveStateChanged` on failure.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha14-records`.

## Forbidden

A second dispatch; any other input; any settings change; deleting anything.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
