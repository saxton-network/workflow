# Task P: authority promotion

- **Prerequisites:** B `passed` for the exact candidate; Validate CI green on it.
- **Target:** `origin` `refs/heads/main`.

## Work

1. `git fetch origin`; prove `origin/main` is an ancestor of the candidate with no inherited `GIT_*` variables, `GIT_GRAFT_FILE=/dev/null git --no-replace-objects -c core.commitGraph=false -c advice.graftFileDeprecated=false merge-base --is-ancestor <origin/main> <candidate>` (as `agent-work/EVIDENCE-MANIFEST.md` documents).
2. Non-force fast-forward: `git push origin <candidate>:refs/heads/main`.
3. Fetch again and verify `origin/main` equals the candidate.
4. Merge `main` into `pilot/alpha11-records` without force, so later gate checks run the reviewed helper.

## Result

`results/P.md`: pre- and post-push refs, ancestry proof, push output.

## Records

Hand the result content to the coordinator. Only the coordinator commits to `pilot/alpha11-records`, and nothing under `agent-work/pilot-alpha11/` is ever committed to the implementation or fix branch.

## Forbidden

Force pushes, merge commits on `main`, rebases, or anything other than the exact reviewed commit. If the push is refused or `main` moved, stop.

## Stop boundary

Stop at the end of this task and hand the result to the coordinator. Do not start another task.
