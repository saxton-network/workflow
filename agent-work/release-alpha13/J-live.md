# Task J: live deployment (human gate)

- **Prerequisites:** R `complete` with `PASS`; the owner's explicit "y" to the concrete preview, confirming availability to delete within 30 minutes. A "y" without that availability is "n".
- **Read first:** `AGENTS.md`, `PLAN.md` "Live preview (J)" and "Approval record (J)", `CONTRACT.md`.
- The coordinator writes `results/J-approval.md` as `COORDINATOR.md` "Approval records" and `PLAN.md` require, records J `in_progress`, and confirms the helper shows `READY` (a handoff only).

## Work

1. **Recheck, seconds before dispatch:** `origin/main` equals the source; no alpha.13 tag or release (drafts included); immutable releases off and no rulesets; every frozen file hash; the latest `release.yml` run ID. Read the output; if anything differs, dispatch nothing, leave J `in_progress`, stop and ask the owner.
2. **Dispatch** `R-dispatch-inputs.json` once, as a tool call of its own. If the call errors or no single new run appears, never dispatch again: re-list for up to 2 minutes, then stop and ask the owner.
3. **Wait** up to 12 minutes for the run to complete; if still running, cancel, wait for `completed`, record J `failed`.
4. **Wrong `head_sha`:** follow `CONTRACT.md` "A run built from the wrong commit".
5. **Runtime acceptance:** checks 1–3 of `CONTRACT.md`, stopping at the first failure.
6. **On failure:** make sure the run is `completed`; record J `failed` with `runtimeAcceptance: "FAIL"` and `liveStateChanged` per `CONTRACT.md` (with the one-line reason when `false`); tell the owner plainly what exists and what happens next.

## Result

`results/J.md`: the recheck, the run ID and `head_sha`, each check's outcome, and `liveStateChanged` on failure.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha13-records`.

## Forbidden

A second dispatch; any other input; any settings change; deleting anything.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
