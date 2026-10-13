# Task J: live deployment (human gate)

- **Prerequisites:**
  - R `complete` with `PASS`;
  - the owner's explicit "y" to the concrete preview, which confirms they are available to delete within 30 minutes.
- **Read first:** `AGENTS.md`, `PLAN.md` "Live preview", `CONTRACT.md`.
- **The preview states:**
  - the source and fingerprint;
  - the declared deviation and the expected-failure signature;
  - the commands, effects and exposure, including that the drill stays public until the owner deletes it;
  - the stop conditions, the rollback and the retry boundary;
  - the question "Approve, and I am available now to delete within 30 minutes? (y/n)".
- **No-go:** if the owner does not answer y with availability, do not dispatch; J stays `pending`.
- **Approval record:** the coordinator writes the approval to `results/J-approval.md`, records it (`in_progress`), and confirms the helper shows `READY`, which is a handoff only.

## Work

1. Recheck `origin/main`, that the drill tag and release are absent (drafts included), the immutable-releases setting, and every frozen file hash.
2. Dispatch exactly the frozen inputs. Find the single new run; if its `head_sha` is not the source, cancel it and go to the rollback.
3. Schedule the two read-only check-ins (T+30 minutes, T+24 hours).
4. Run acceptance checks 1–4 in the order `CONTRACT.md` gives, stopping at the first failure. Compare the outcome with the expected-failure signature.
5. Stop. Record J `failed` with `runtimeAcceptance: "FAIL"`. Tell the owner which items to delete, with their links.

## Result

`results/J.md`, containing:
- `drill: true`;
- the approval reference and the rechecks;
- the run ID and `head_sha`;
- each check's outcome;
- whether the failure matched the signature.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/rollback-drill-records`.

## Forbidden

- A second dispatch.
- Any other inputs.
- Recording J `complete`.
- Asking the owner to act on anything other than drill items.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
