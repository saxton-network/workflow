# Plan: release v0.1.0-alpha.13 through the Workflow v3 deployment graph (Pilot 6)

Status: revision 3, approved by the owner on 2026-10-14 with owner decisions 1–7. It applies the independent plan review's findings PR1–PR25 over three rounds; the third round approved. The reviewer was a separate, read-only agent; the model observed in its transcript differs from the coordinator's.

## Goal

There are two goals:

- **Package the fixes.** Publish `v0.1.0-alpha.13`, which packages everything merged since `v0.1.0-alpha.12` (`c7ad3c3`).
- **Use the newer rules live.** Do it through the full deployment graph, so the rules merged after Pilot 5 (PRs #20 and #21) are used live for the first time:
  - approval records;
  - commands that move refs;
  - the repair-round reset;
  - the reviewer's observed model;
  - plan clarifications;
  - the pre-dispatch recheck and dispatch-error rules;
  - `liveStateChanged` on a failed attempt.

Where the procedure, the helper or the docs get in the way, that is a pilot finding: recorded and reported, not patched during the run.

## The live change

Publish `v0.1.0-alpha.13` as a GitHub prerelease with `.github/workflows/release.yml`, from `main`.

- **A prerelease.** It is never "Latest". `v0.1.0-alpha.12` and every other release stay published and unchanged.
- **Packaging.** `release.yml` packages `main` HEAD with `git archive`. The review reproduced alpha.12's published ZIP from `c7ad3c3`, and built the alpha.13 ZIP twice with identical bytes. Readiness can therefore freeze the exact artifact hash; R computes it itself.
- **Speed.** The run takes about 15 seconds. It creates the tag about 8 seconds in. A dispatch cannot be recalled, and a cancel will almost never beat the tag step.

## Content of the release

These are the seven merges since `v0.1.0-alpha.12`. PRs #17 to #21 each have a durable review record on the pull request. #15 is test only and has no such record (Pilot 4 finding 6). #16 holds records that were reviewed during Pilot 4's own records review.

- **#15:** test only. It has never reached a published release, because the drill's release was rolled back.
- **#16:** the Pilot 4 rollback-drill records (about 1,700 lines) and its `PILOT-HISTORY.md` entry.
- **#17:** the helper keeps a live task `GATED` after a failed attempt until there is fresh readiness, with its task-view message and tests. The spec names "stopped after verified rollback" and drills. The coordinator records findings before repair, and keeps durable review records. `RELEASING.md` covers rollback order and API checks.
- **#18:** the helper closes the live gate after a mid-run stop or a non-PASS acceptance. One line each was added to the coordinator guide and the spec.
- **#19:** the Pilot 5 history.
- **#20:** `docs/ADOPTING.md` with a tested gate template. Also: approval records, the repair-round reset, reviewer model checks, rules for commands that move refs, and the helper exiting quietly on a closed pipe.
- **#21:** the threat-model guard-validator rule, plan-drift rules and live-attempt rules. The helper does not offer a rollback when a failed attempt records `liveStateChanged: false`.

There are about 2,400 changed lines in all. The ZIP carries every pilot record, including the owner's public GitHub username and the history of the public adopter repository `saxton-network/site`.

## Deployment authority

`authority_remote = "origin"`, `authority_ref = "refs/heads/main"`, as `AGENTS.md` and `docs/RELEASING.md` declare.

## Task graph (workflow ID `release-alpha13`)

| Task | Kind | What it does | Depends on |
| --- | --- | --- | --- |
| A | implementation | Identify the candidate: the current `main` head. No code changes; output the candidate SHA. Validate CI must be green on it. Branch: `pilot/alpha13-records`. | — |
| B | independent_review | Release review. See the B section below. | A complete |
| C | repair (conditional) | Fixes B's findings through an ordinary PR, merged on the owner's go-ahead (see C below). The same reviewer re-reviews. | B findings |
| R | release_readiness | Read-only checks and the frozen batch (below). | B passed |
| J | live_deployment (human gate) | The owner's explicit y/n; one dispatch; runtime acceptance. | R complete |
| V | other, `required_status = {J = "failed"}` | After a failed attempt that may have published something: read the actual state, give the owner the rollback deletions one at a time, verify the baseline, and land the records. | J failed |
| K | final_reconciliation | Verify refs and the release, and land the records. | J complete with runtime acceptance PASS |

There is no authority-promotion task: `main` already holds the candidate, as in Pilot 4, and the review confirmed this graph validates.

Before task A starts, the coordinator does three things on the records branch:

- compiles the scaffold: this plan, `CONTRACT.md`, `manifest.toml`, the task files and `results/README.md`;
- validates it with the helper;
- has it reviewed independently (`results/scaffold-review.md`).

## B: release review

- **Reviewer.** A separate agent, pinned to a different model from the one that built every change under review (the coordinator's model, named in each commit's co-author trailer). The coordinator checks the observed model in the reviewer's own transcript in every round.
  - The model is recorded in words in `results/B-n.md`, with `model: null` in the evidence.
  - A review that turns out to be on the builder's model is a deviation, not independence.
- **Additional review.** This release review is on top of the per-PR reviews already done. It covers:
  1. The candidate is exactly `main`, and contains only merged, reviewed changes since `c7ad3c3`.
  2. The release as a whole, against `docs/THREAT-MODEL.md`:
     - the combined helper behaviour across PRs #17, #18, #20 and #21;
     - the full test suite on Python 3.11, 3.12 and 3.13;
     - docs consistent with each other and with the code.
  3. Nothing private in the ZIP: no tokens or keys, no email addresses other than the no-reply trailer, no local machine paths, no session links in shipped files, and no private repository names.
  4. `CONTRACT.md`.
- **Verdict.** `passed` or `findings`.

## C: repair (only if B finds something)

- **Making and landing the fix.** The fix is an ordinary PR, reviewed by the same reviewer. It is merged on the owner's go-ahead, following `COORDINATOR.md` "Commands that move refs".
- **New candidate.** The candidate becomes the new `main` head, the merge commit. The C record's `candidateSha` is that head, and B re-reviews exactly that SHA.
- **Helper version.** If the repair changes `scripts/agent-task.py`, the coordinator merges `main` into the records branch before running the helper again.
- **Another round.** For a second round, B goes back to `findings` and C to `pending` in the same records commit.
- **Contract changes.** `CONTRACT.md` may change only before R, and each change is recorded.

## Main freeze

Nothing else merges into `main` from R until one of these:

- J's runtime acceptance passes;
- V has verified a rollback;
- after a proven `liveStateChanged: false`, the owner says how to continue. If the owner chooses a retry, the freeze continues into the new readiness cycle.

This follows the earlier pilots' precedent, because `release.yml` packages `main` HEAD. Until then, the only permitted merge is the records PR in the proven-`false` case.

- **By agreement only.** GitHub cannot enforce the freeze.
- **How a breach is detected:** the pre-dispatch recheck, the run's `head_sha` check, and the "`main` still equals the source" acceptance check.
- **After the freeze.** The records PR is an ordinary reviewed merge.

## Readiness checks (R)

- **Source.**
  - `origin/main` equals the source: `gitDivergence` `identical: true`, proven in a non-shallow clone.
  - `bash scripts/validate-repository.sh` passes at the source in a clean worktree.
  - Validate CI is green on the source.
- **Name is free.** No tag `v0.1.0-alpha.13` (API ref and `git ls-remote`), and no release or draft with that name. Drafts are read through the authenticated release list, and the identity that read them is recorded.
- **Rollback is possible.** Both are recorded in `results/R-settings.json`:
  - immutable releases are off;
  - no ruleset blocks tag creation or deletion (`GET /repos/saxton-network/workflow/rulesets` is empty, as in Pilot 4).
- **Tools.**
  - Workflow dispatch, run reads and job-step reads are proven available.
  - Run cancel is available but not exercised.
  - This session cannot delete a release or tag; the owner does any deletion.
  - The local git version and the GitHub identity used are recorded.
- **Reproducible ZIP.**
  - `git archive --format=zip --prefix=workflow-v0.1.0-alpha.13/ <source>` is built twice, and the two builds are byte-identical.
  - The same command at `c7ad3c3` reproduces alpha.12's published ZIP digest.
- **Expected `.sha256` line.** It is made exactly as `release.yml` makes it: `sha256sum workflow-v0.1.0-alpha.13.zip`, in the ZIP's directory. It must match `^[0-9a-f]{64}  workflow-v0\.1\.0-alpha\.13\.zip\n$`.
- **Baseline** (`results/R-baseline.json`):
  - every tag with its target;
  - every release, drafts included, with ID, tag, flags and publish time;
  - alpha.12's asset digests;
  - the latest `release.yml` run ID, so that "exactly one new run" can be checked.
- **Frozen batch.** The `agent-work/release-alpha13/…` files are committed on the records branch before R hashes them.
  - `deploymentSourceSha`: the source.
  - `deployableArtifactSha256`: the local ZIP's SHA-256.
  - `deploymentConfiguration`, each with its SHA-256:
    - `.github/workflows/release.yml`;
    - `agent-work/release-alpha13/results/R-dispatch-inputs.json` (ref `main`, `release.yml`, version `v0.1.0-alpha.13`, `prerelease: true`);
    - `agent-work/release-alpha13/results/R-expected-checksum.txt`;
    - `agent-work/release-alpha13/results/R-settings.json`;
    - `agent-work/release-alpha13/CONTRACT.md`.
  - `validators`: `scripts/validate-repository.sh`, `scripts/check-release-version.sh`, `scripts/agent-task.py` and `scripts/tests/test_agent_workflow.py`, read at the source.
  - `installedScripts`: none.
  - `rollbackArtifact`: identity `github-release-v0.1.0-alpha.12`, provenance `agent-work/release-alpha13/results/R-rollback-alpha12.md`. That file holds alpha.12's tag target and verified asset digests.
  - `deploymentTargets` (mode `null`):
    - the release page `https://github.com/saxton-network/workflow/releases/tag/v0.1.0-alpha.13`;
    - the two asset download URLs;
    - the tag ref `https://api.github.com/repos/saxton-network/workflow/git/ref/tags/v0.1.0-alpha.13`.

## Contract (`CONTRACT.md`)

### Accepted unknowns

- **Runner tools.** The runner's git and zlib build the published ZIP. A hash mismatch fails acceptance, even if the files match.
- **Release notes.** These are generated by GitHub (`--generate-notes`) and not frozen. They will list PRs #15–#21 by title and contributor, with a compare link.
- **Action versions.** Pinned by tag; covered by the ZIP hash check.
- **Website wording.** The labels of GitHub's delete controls are not frozen. Every deletion is verified through the API.

### Dispatch

- The pre-dispatch recheck runs seconds before the dispatch. Its output is read and must be clean before the dispatch is issued. The dispatch is a single tool call of its own, never batched with the recheck.
- **If the recheck fails:** dispatch nothing, leave J `in_progress`, stop and ask the owner. The helper may still show J `READY`, because the approval record is intact. That is not permission, and not a finding.
- **If the dispatch call errors, or no single new run appears:** never dispatch again. Re-list the runs for up to 2 minutes, then stop and ask the owner.
- **Waiting for the run.** Wait up to 12 minutes for it to finish; `release.yml` has a 10-minute limit. If it is still running after that, cancel it, wait until it is `completed`, and record J `failed`.

### Runtime acceptance

Checks run in order and stop at the first failure.

1. **The run.**
   - Exactly one new `release.yml` run since the baseline run ID.
   - `head_sha` equals the `main` tip recorded at the recheck.
   - Conclusion: success.
2. **The release.**
   - `v0.1.0-alpha.13` is published, is a prerelease, and is not latest.
   - It has exactly the two expected assets.
   - The ZIP's SHA-256 equals the frozen hash.
   - The `.sha256` asset bytes equal `R-expected-checksum.txt`.
   - The unpacked ZIP equals `git archive` of the source.
3. **Refs.**
   - The tag is a lightweight ref at the source.
   - alpha.12's digests, and every other tag and release, match the baseline.
   - `main` still equals the source.

### A run built from the wrong commit

If `head_sha` is not the source, the tag and release probably already exist. Cancel only if the run is still before its "Create release tag" step. In every case:

1. wait until the run is `completed`;
2. record J `failed`;
3. read the actual state, and follow the rollback matrix.

### Every failed attempt records `liveStateChanged`

**`false` only when all of the following hold**, with a one-line reason in `J.md`:

1. The run is `completed` with conclusion `failure`.
2. Its job-step list (`list_workflow_jobs`) shows "Create release tag at the validated commit" as skipped, or never started.
3. The tag API returns 404, and `git ls-remote --tags` shows no `v0.1.0-alpha.13`.
4. The authenticated release list, drafts included, shows no alpha.13 and otherwise equals the baseline.

Otherwise it is `true`. That includes a cancelled run, a run that stopped at or after the tag step, and anything still running. It is `null` only if the state cannot be read, and then it is treated as `true`.

### Rollback (V)

V runs only after J `failed` with `liveStateChanged` not `false`.

- **Run finished first.** V first makes sure the run is `completed`, cancelling and waiting if it is not.
- **Act only on what exists.** V reads the actual state and follows the matching row, deleting only what exists:

| State found | Owner deletes, one item at a time, each verified through the API before the next |
| --- | --- |
| No tag and no release, found after the run finished (for example a cancel before the tag step, or a failure at the tag step itself) | Nothing to delete. V verifies the baseline, records it, and is recorded `complete`. The end state is "stopped after verified rollback". The name alpha.13 is still not reused, because `liveStateChanged` was not proven `false`. |
| Tag only | The tag. |
| Draft release plus tag | The draft (through its own link), then the tag. |
| Draft release, no tag | The draft. |
| Published release plus tag (whether the run failed after publishing, or acceptance failed) | The release, then the tag. |

- **Links given to the owner.**
  - A published release: `https://github.com/saxton-network/workflow/releases/tag/v0.1.0-alpha.13`.
  - A draft: that draft's own `html_url`, with its release ID, read from the authenticated list. Drafts are not at the tag link.
  - The tag: the Tags page `https://github.com/saxton-network/workflow/tags`, in the row named exactly `v0.1.0-alpha.13`.
- **Order matters.** `docs/RELEASING.md` says deleting the tag first is understood to turn a release into a draft, but this has not been observed. Either way, V reads the actual state after each step and follows the matching row.
- **Never anything else.** The owner is never asked to act on any other release or tag. If anything other than alpha.13 items differs from the baseline, the coordinator stops and asks.
- **Final verification.**
  - The release API returns 404 for alpha.13, and no release or draft carries that tag.
  - `git ls-remote` shows no tag, and both download URLs return 404.
  - The full tag and release lists equal `R-baseline.json` exactly.
  - alpha.12's digests and ZIP are unchanged.
  - `main` is unchanged, immutable releases are off, and there are still no rulesets.
- **End state:** "stopped after verified rollback".
- **Check-ins.** After a failed attempt that left something public, the coordinator schedules one read-only check-in at T+30 minutes, and another at T+24 hours if items still exist. Each rereads the state and reminds the owner. They are switched off once V has verified.

### No rollback needed

When `liveStateChanged: false` is proven:

- V is recorded `failed`, with "rollback not needed" and the reason.
- K stays blocked. The end state is **"stopped; nothing published, proven"**.
- The coordinator asks the owner how to continue.
- The coordinator lands the records through a reviewed PR on the owner's go-ahead. That merge moves `main`, so a retry after it starts again from tasks A and B for the new `main` head. The owner chooses, at that go-ahead, whether to land the records before or after a retry. The expected `protected_change` is recorded as a deviation note, since the spec names only the success and verified-rollback cases.

### Retry boundary

- **One dispatch.** Any retry needs fresh readiness and a new approval.
- **Name reuse.** The name `v0.1.0-alpha.13` may be reused only after a proven `liveStateChanged: false`, meaning no tag or release ever existed. Once a tag or release has existed, even briefly or as a draft, the name is never reused; a retry is `v0.1.0-alpha.14`.

## Approval record (J)

`agent-work/release-alpha13/results/J-approval.md` follows `COORDINATOR.md` "Approval records":

- when the preview was shown, the exact question, and the owner's literal answer;
- the source and fingerprint;
- **approved actions:**
  1. the single dispatch, with `R-dispatch-inputs.json` and its SHA-256;
  2. a conditional run cancel, used only in these cases:
     - the run built the wrong commit and is still before its tag step;
     - it is still running after 12 minutes;
     - V finds it not `completed`;
- **owner actions under this approval:** the deletions in the rollback matrix, only if J failed with `liveStateChanged` not `false`;
- **not covered:** a retry, another version or source, any settings change, or any deletion by the coordinator;
- a statement that it is the coordinator's own account of a chat approval.

## Live preview (J), in plain language

- **What is published, from which commit and fingerprint.**
- **The single dispatch.**
- **The effects:**
  - a public tag;
  - a public prerelease with two files, and generated notes listing PRs #15–#21;
  - notifications to watchers.
- **Exposure:** public until deleted. The ZIP includes all pilot records and the owner's public username.
- **Timing:** about 15 seconds; it cannot be recalled once started.
- **The checks, and the stop conditions.**
- **The rollback:** the owner deletes, using exact links; the coordinator cannot.
- **The retry boundary.**
- **The main freeze.** Please do not create or delete any other release or tag until it ends.
- **"Latest."** alpha.13 will not show as "Latest".
- **Immutable releases.** Leave the immutable-releases setting off; if it were turned on, the release could not be rolled back.
- **The possible end states:** "complete"; "stopped after verified rollback"; or "stopped; nothing published, proven".
- **The question:** "Approve, and are you available to delete the release and tag within 30 minutes if it fails? (y/n)". A "y" without that availability is treated as "n".

## Expected helper behaviour

**Manifest statuses the coordinator sets:**

| Task | Status path |
| --- | --- |
| A | `pending` → `complete` |
| B | `blocked` → `passed`, or `findings` → C → re-review |
| C | `conditional`, unless B has findings |
| R | `blocked` → `complete` |
| J | `blocked` → `in_progress` (approval record) → `complete` or `failed` |
| V | `blocked` → `complete` or `failed` |
| K | `blocked` → `complete` |

**Labels the helper should show:**

| When | Expected |
| --- | --- |
| Before R completes | J `GATED` |
| After R `PASS`, before the approval record | J `PREVIEW` |
| After the approval record | J `READY`. This is a handoff only. |
| After a failed recheck (J left `in_progress`) | J may still show `READY`; V and K are not ready. Not a finding. |
| On success | J `DONE`, K `READY` |
| On failure with `liveStateChanged` `true` or `null` | J `GATED`, V `READY`, K never ready |
| On failure with `liveStateChanged: false` | J `GATED`. V is not ready, and its task view says no rollback is needed. K is never ready. |
| A mid-run stop | J is recorded `failed` with `runtimeAcceptance: "FAIL"`, never `blocked` or `pending`; then J shows `GATED`. |
| Repair rounds | B `findings`, then C ready. A second round needs B back to `findings` and C back to `pending`. |

Any other difference is a finding.

## Clarifications

Dated entries go here. A task file that makes a check stricter, or swaps in an equal or stronger proof, is recorded here before the task runs. The next independent review checks it, and the next owner preview lists it. Anything weaker or wider, or anything that changes the live batch, needs a revised plan and a new approval.

*(none yet)*

## Records

The coordinator keeps `agent-work/release-alpha13/` on `pilot/alpha13-records`. It holds:

- `PLAN.md`, `CONTRACT.md`, `manifest.toml`, the task files and `evidence.json`;
- `results/`:
  - `README.md`, `plan-approval.md` and `scaffold-review.md`;
  - `A.md`, `B-n.md` and `C-n.md`;
  - `R.md`, `R-baseline.json`, `R-settings.json`, `R-rollback-alpha12.md`, `R-dispatch-inputs.json` and `R-expected-checksum.txt`;
  - `J-approval.md` and `J.md`;
  - `K.md` or `V.md`.

The records PR adds only that directory and a `docs/PILOT-HISTORY.md` "Pilot 6" entry. It carries the divergence proof and a secrets scan. The expected `protected_change` covers only the frozen files under the workflow directory. The PR is independently reviewed and landed on the owner's go-ahead, with a local `--no-ff` merge pushed as a fast-forward. Every push follows `COORDINATOR.md` "Commands that move refs": the gate exits before the push, and the push uses an asserted literal SHA. Afterwards `main` and the release are rechecked. The records ship in the next release's ZIP.

## Owner decisions

1. Approve this plan.
2. A main freeze from R until one of these ("Main freeze"): runtime acceptance passes; a rollback is verified; or, after a proven `liveStateChanged: false`, you say how to continue.
3. Rollback means the owner deletes the release and tag on GitHub, through exact links, when asked. The coordinator cannot delete.
4. Name reuse: alpha.13 is reused only if nothing was ever created; otherwise a retry is alpha.14.
5. A ZIP hash mismatch fails acceptance even if the files match.
6. The release notes are GitHub's generated text, listing PRs #15–#21.
7. The run's records, including the owner's public username and the adopter-site history, ship in a later release ZIP after a secrets check.
8. Later:
   - the y/n on the live preview in J, with availability to delete within 30 minutes;
   - the go-ahead to merge the records PR;
   - if B finds anything, the go-ahead to merge the repair PR.

## Stop conditions

- B is not clean after two repair rounds.
- CI is red on the candidate.
- `main` moves unexpectedly.
- The readiness verdict is not `PASS`.
- Credentials are missing or interactive.
- The helper shows a gate state other than the expected table.
- Any dispatch or acceptance stop condition above.

## Out of scope

- Code changes during the run, other than a reviewed repair in C.
- Changes to the threat model or the spec during the run.
- Upgrading `saxton-network/site` to alpha.13, which is a later, separate workflow.
