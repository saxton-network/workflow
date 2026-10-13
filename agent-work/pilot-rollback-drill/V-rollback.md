# Task V: rollback and verification

- **Prerequisites:** J `failed`.

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
6. Open the records PR (this directory plus a `docs/PILOT-HISTORY.md` entry), with a secrets check and divergence proof. Get an independent review, merge on the owner's go-ahead, and recheck `main`.

## Result

`results/V.md`: the state found, each deletion and its verification, the final verification, the drill verdict, and the records PR.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/rollback-drill-records`.

## Forbidden

- Any change to a release or tag other than the drill items.
- Merging the records PR without review and the owner's go-ahead.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
