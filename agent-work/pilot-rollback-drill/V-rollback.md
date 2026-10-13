# Task V: rollback and verification

- **Prerequisites:** J `failed`.
- **Read first:** `AGENTS.md`, `PLAN.md` "Rollback" and "V: rollback verification", `CONTRACT.md`.

## Work

1. Read the actual state of the drill release (drafts included) and tag, and follow the matching row of the rollback matrix in `CONTRACT.md`.
2. Give the owner one deletion at a time, with the exact link. After the owner reports each one done, verify it through the API before giving the next.
3. Final verification:
   - the release API returns 404 for the drill tag, and no release (drafts included) carries that tag;
   - `git ls-remote` shows no drill tag;
   - both drill download URLs return 404;
   - the full tag and release lists equal `R-baseline.json` exactly;
   - alpha.12's digests and downloaded ZIP are unchanged;
   - `main` is unchanged, and immutable releases are still off.
4. Switch off the check-ins.
5. Write the drill verdict.
6. Records divergence. Prove the records descend from the source, list their changed paths with the documented commands (no inherited `GIT_*` variables), and run `classify_divergence` with the frozen batch's paths. Expect `protected_change` only for frozen files under `agent-work/pilot-rollback-drill/`. The spec treats that as expected only after runtime acceptance passed, which is not true here; record this as a pilot finding.
7. Open the records PR (this directory plus a `docs/PILOT-HISTORY.md` entry), with a secrets check and the divergence proof. Get an independent review, and merge on the owner's go-ahead.
8. Record V `complete` before the merge, because records cannot prove their own merge. Report the merge commit and a fresh `main` check afterwards, outside the records. Do not call the workflow reconciled until that check passes.

If any verification fails, record V `failed`, stop and report; K stays blocked.

## Result

`results/V.md`: the state found, each deletion and its verification, the final verification, the drill verdict, and the records PR.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/rollback-drill-records`.

## Forbidden

- Any change to a release or tag other than the drill items.
- Merging the records PR without review and the owner's go-ahead.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
