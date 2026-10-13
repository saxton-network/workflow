# Task V: rollback and verification

`drill: true`. **Drill verdict: PASS.** All four drill conditions hold:

1. The injected check, and only that check, failed with the exact signature (`results/J.md`).
2. The run stopped there: J was recorded `failed` at check 4, before any deletion.
3. The rollback removed exactly the drill release and the drill tag.
4. Every tag and release equals the baseline exactly.

## State found (after the run reported `completed`)

A published release plus a tag. That is the expected row of the rollback matrix: delete the release, then the tag.

## Deletions, each verified before the next

| Step | Owner action | Coordinator verification |
| --- | --- | --- |
| 1 | Deleted the release through the direct link (reported 09:19Z) | `get_release_by_tag v0.0.0-drill.1` returns 404. The authenticated `list_releases` is back to the 12 baseline releases, no drafts. The ZIP download returns 404. The tag is still present at `92c51e6`. The page `/releases/tag/v0.0.0-drill.1` still returned 200 at this point, because GitHub shows a plain tag page while a tag exists. |
| 2 | Deleted the tag from the Tags page (reported shortly after) | See the final verification below. |

## Final verification (2026-10-13T09:19:53Z)

- **The drill is gone:**
  - no `refs/tags/v0.0.0*` in `ls-remote`;
  - the API returns 404 for the drill tag;
  - the release page and both download URLs return 404.
- **Tags:** the full `ls-remote --tags` output equals the readiness snapshot exactly (12 tags).
- **Releases:**
  - the public releases list, with every asset's ID, name, size and digest, equals `R-baseline.json` exactly (12 releases);
  - the authenticated `list_releases`, which includes drafts, shows the same 12, none of them drafts.
- **alpha.12:** its downloaded ZIP hashes to `8d93a574…a211ba6` and its `.sha256` asset to `3c253fa2…dd64`, both unchanged.
- **`main` and settings:** `main` = `92c51e6c69d7ed29ee6e879733ad4b801a82814e`; immutable releases are still off; rulesets are still `[]`.
- **What remains:** the Actions run record 38374361610 remains, as the contract allows; it is outside the baseline.

The two check-ins (`trig_01NRftaTTs4NTaSjLVqcZKWz`, `trig_019rjpjfjWYtXCLx2yGNG8gc`) were switched off with `update_trigger` `enabled: false` before either fired. The main freeze ended with this verification.

## Exposure

The drill release was public from 09:10:16Z until the owner deleted it at about 09:19Z. The tag was deleted moments later: it was gone by the 09:19:53Z verification. When the coordinator first read the release, before its own acceptance download, GitHub reported 0 downloads. Later downloads by others during the window cannot be ruled out.

## Records

This directory and a `docs/PILOT-HISTORY.md` entry are landed through a reviewed records PR. Records cannot prove their own merge, so V is recorded `complete` here, before the merge; the merge commit and a fresh `main` check are reported to the owner afterwards.
