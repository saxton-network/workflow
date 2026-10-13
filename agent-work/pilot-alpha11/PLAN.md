# Pilot plan: release v0.1.0-alpha.11 through the Workflow v3 deployment graph

Status: revision 3, approved by the repository owner on 2026-10-13, including the nine recommended owner decisions below. Reviewed independently before approval (initial review, then confirmation of revisions 2 and 3).

## Goal

Run the full Workflow v3 deployment graph once, for real, end to end: implementation, independent review, repair if needed, authority promotion, release readiness, human-approved live deployment, runtime acceptance, and final reconciliation. The coordinator records `agent-work/pilot-alpha11/evidence.json` and runs `scripts/agent-task.py` at every gate to confirm it reports what the spec says. Every place where the procedure, the helper, or the docs get in the way is a pilot finding, recorded and reported, not patched during the run.

## The live change

Publish `v0.1.0-alpha.11` of this repository as a GitHub prerelease with `.github/workflows/release.yml`.

- Reachable: the coordinator can perform and check it with the GitHub connection available in this session (workflow dispatch, run status, run cancel, release and asset reads).
- Low risk: a prerelease; `v0.1.0-alpha.10` stays published and unchanged.
- Observable: `git archive --format=zip --prefix=workflow-<version>/ <commit>` (git 2.43.0) reproduced the published ZIPs of alpha.10, alpha.9, alpha.5 and alpha.1 byte for byte, so readiness can freeze the exact artifact hash before anything is published.

## Content of the release

The three Low findings left open by the threat-model review of PR #12:

1. Protected-pattern bracket rule matches `fnmatch`: `[]` and `[!]` (unclosed in fnmatch) are rejected; `[]a]` and `[!]a]` (valid classes) are accepted.
2. A test that `ssh:///srv/app` (hostless, non-web scheme) stays accepted.
3. More known default ports: `scp` 22, `ftps` 990, `smb` 445, with docs updated.

## Deployment authority

`authority_remote = "origin"`, `authority_ref = "refs/heads/main"`, as `docs/RELEASING.md` says releases come from `main`. `AGENTS.md` does not yet name this repository's own deployment authority; that gap is recorded as a pilot finding (R12) and, for this run, the manifest plus `docs/RELEASING.md` are the declaration the owner approves.

## Contract: accepted unknowns (`CONTRACT.md`, R4)

Readiness cannot freeze these; each is a named exception with a bounded consequence:

1. **Runner tools.** `ubuntu-latest`'s git and zlib build the ZIP. Readiness freezes the locally built hash; the hash comparison is a live-only check. If the published ZIP hash differs from the frozen hash, runtime acceptance FAILS even if the extracted files match.
2. **Release notes.** `--generate-notes` text is written by GitHub and not frozen. Readiness previews it read-only if the API allows; otherwise it is accepted as unfrozen. With a direct fast-forward, the notes may only say "Full Changelog".
3. **Action versions.** `actions/checkout@v7.0.1` and `actions/setup-python@v6.0.0` are pinned by tag, not commit. Their effect is covered by the runtime ZIP-hash check.

## Task graph (workflow ID `pilot-alpha11`)

| Task | Kind | What it does | Depends on |
| --- | --- | --- | --- |
| A | implementation | Make the three fixes on branch `pilot/alpha11-impl` from `b2316d1`, with tests failing before and passing after. Output: candidate commit; Validate CI must be green on it. | — |
| B | independent_review | A separate reviewer reviews the exact candidate against `docs/THREAT-MODEL.md` (a different model or vendor if available; otherwise a separate agent, recorded as such). Verdict `passed` only when no in-scope finding, Low included, remains in the new code; otherwise `findings` (R11). | A complete |
| C | repair (conditional) | Fixes B's findings on branch `pilot/alpha11-fix`, descending from the candidate; the same reviewer re-reviews. | B findings |
| P | authority_promotion | After a fresh fetch, ancestry check, and green CI on the candidate: fast-forward `main` to the exact reviewed commit with a non-force push (`git push origin <sha>:refs/heads/main`); verify `origin/main` equals it. If refused or `main` moved, stop. | B passed |
| R | release_readiness | Read-only checks and frozen batch (below); verdict `PASS`, `FAIL`, or `UNKNOWN`. | B passed, P complete |
| J | live_deployment (human gate) | Owner's explicit y/n on the preview below; then the live batch and runtime acceptance. | R complete |
| K | final_reconciliation | Verify refs and release; record evidence; open the records PR (below). | J complete, runtime acceptance PASS |

Before task A starts, the scaffold (this plan, `CONTRACT.md`, `manifest.toml`, task files, `results/README.md`) is compiled on the records branch, validated with the helper, and independently reviewed (R10).

## Main freeze (R1)

From step P until J's runtime acceptance passes, or until any rollback is verified, nothing else is merged into `main`. The owner agrees to this as part of approving the plan.

## Release readiness checks (R)

- `origin/main` equals the source; `git merge-base --is-ancestor` proof recorded as `gitDivergence: {identical: true, authoritySha: <source>, otherSha: <fresh origin/main>}`.
- `bash scripts/validate-repository.sh` passes at the source; Validate CI is green on the source.
- Neither tag nor release (including a draft) named `v0.1.0-alpha.11` exists.
- Repository setting: immutable releases still off (so a release could be deleted).
- Tools (R9): workflow dispatch and run read proven available through the GitHub connection; run cancel available but not exercised (if it fails or comes too late, acceptance fails and rollback applies); the local git version used for the ZIP recorded. This session has no tool that deletes a release (the `gh` token is invalid), so rollback deletion is done by the owner (see J).
- Baseline recorded: all existing tags and releases, alpha.10's asset digests.
- Frozen batch:
  - `deploymentSourceSha`: the source.
  - `deployableArtifactSha256`: SHA-256 of the locally built `workflow-v0.1.0-alpha.11.zip`.
  - `deploymentConfiguration`: `.github/workflows/release.yml`; `agent-work/pilot-alpha11/results/R-dispatch-inputs.json` (ref `main`, workflow file, version `v0.1.0-alpha.11`, `prerelease: true`); `agent-work/pilot-alpha11/results/R-expected-checksum.txt` (the exact bytes the `.sha256` asset must have). Each with SHA-256.
  - `validators`: `scripts/validate-repository.sh`, `scripts/check-release-version.sh`, `scripts/agent-task.py`, `scripts/tests/test_agent_workflow.py`, with SHA-256.
  - `installedScripts`: none.
  - `rollbackArtifact`: identity `github-release-v0.1.0-alpha.10`, provenance the results file with its verified asset digests.
  - `deploymentTargets`: the release page and the two asset download URLs, mode `null`.

## Live preview (J), shown to the owner in plain language before the y/n (R6)

- **Source:** full commit SHA and frozen-batch fingerprint.
- **Commands:** through the GitHub connection, `actions_run_trigger` with `method=run_workflow`, `workflow_id=release.yml`, `ref=main`, `inputs={version: v0.1.0-alpha.11, prerelease: true}`. The run is the only `workflow_dispatch` run of `release.yml` on `main` created after the dispatch time; if there is not exactly one, stop. Read its `head_sha` at once; if it is not the source, cancel it with `actions_run_trigger` `method=cancel_workflow_run` and that run's ID.
- **Effects:** a public lightweight tag at the source, a public prerelease with two files and generated notes, notifications to repository watchers.
- **Exposure:** the repository is public; anyone may fetch the tag or files before any rollback, and a failed release stays public until the owner deletes it.
- **Verification (runtime acceptance, R7):** run concluded successfully with `head_sha` equal to the source; release is published, prerelease, not latest; exactly the two expected files; ZIP hash equals the frozen hash; `.sha256` bytes equal the expected bytes; unpacked ZIP equals `git archive` of the source; tag is a lightweight ref at the source; alpha.10's digests and all other tags and releases match the baseline; `main` still equals the source.
- **Stop conditions:** any recheck immediately before dispatch differs from readiness; run `head_sha` differs from the source (cancel); the run fails; any acceptance check fails.
- **Rollback (R5):** if the run fails before creating the tag, nothing was published. If the run fails or is cancelled after creating the tag but before the release, the owner deletes the tag only. If any acceptance check fails after publishing, the coordinator stops at once, records the failure, and asks the owner to delete the `v0.1.0-alpha.11` release and, separately, its tag on GitHub (deleting a release on the website leaves its tag; exact steps given). In every case the coordinator then verifies with the release API and `git ls-remote` that they are gone and that alpha.10 and all other tags and releases match the baseline.
- **Retry boundary (R5):** one dispatch. Once a `v0.1.0-alpha.11` tag has existed publicly, the name is never reused; a retry is `v0.1.0-alpha.12` with fresh readiness and a new approval.

Immediately before dispatch the coordinator rechecks `origin/main`, tag and release absence, immutable-releases setting, and every frozen file hash.

## Evidence records the gate needs (R2)

- B's final record carries `deploymentSourceSha` equal to the latest candidate: A's commit, or C's repaired commit after findings.
- No A or C record is appended after B's final `passed` record.
- R's record carries `readinessVerdict`, `deploymentSourceSha`, `frozenBatch`, `frozenBatchFingerprint`, and `gitDivergence` as above.
- The approval record for J has `taskStatus: "in_progress"`, `approvalReference`, `deploymentSourceSha`, and `frozenBatchFingerprint`.
- J's final record has `taskStatus: "complete"`, repeats those three, and adds `runtimeAcceptance`.

Every record and every gate check also records the helper's path and SHA-256 (R8).

## Expected helper behaviour

- Before R completes: live task `GATED`.
- After R `PASS`, no approval record: `PREVIEW`.
- After the approval record: `READY` (handoff only).
- K not ready without runtime acceptance `PASS`; ready with it.
- Known quirks, recorded as findings, not stop triggers: after J completes, `--all` and the task view show J as `PREVIEW`; after a repair, C shows "BLOCKED complete"; after a failed J attempt, the gate shows `PREVIEW` again for the same alpha.11 fingerprint, which is not permission to retry (the retry boundary applies).
- K's divergence check of the records PR will report a protected change, because the records add `R-dispatch-inputs.json` and `R-expected-checksum.txt`, which are frozen configuration files. This is expected after deployment and recorded as a pilot finding.

Any other difference is a finding and stops the run before any live step.

## Where records live (R8)

The coordinator keeps `agent-work/pilot-alpha11/` on branch `pilot/alpha11-records`. After P, it merges `main` into that branch (non-force, recorded) so the gate runs the reviewed helper. In K, the records PR adds only `agent-work/pilot-alpha11/` and a `docs/PILOT-HISTORY.md` entry; its divergence proof (changed paths limited to those) is recorded; it is independently reviewed, then merged by the coordinator on the owner's go-ahead; `main` is rechecked. Before it merges, the records are checked for secrets. The run is finished when that PR is merged. The records then ship as a worked example in later release ZIPs.

## Owner decisions

1. Approve this plan.
2. Main freeze from step P until the release is verified.
3. Allow the coordinator to update `main` by a non-force fast-forward push in P (outside its usual working branch). Undoing it later means adding a revert commit.
4. Rollback means the owner deletes the release and tag on GitHub if asked; the coordinator cannot delete releases in this session.
5. A retry after any public tag uses the next version number.
6. A ZIP whose hash differs from the frozen hash fails acceptance even if the files match.
7. Release notes may be the automatic "Full Changelog" text.
8. The reviewer is a separate agent on the same model unless a different one is available.
9. The run's records ship in later release ZIPs as a worked example, after a secrets check.
10. Later: a separate y/n on the live preview in J, and a go-ahead to merge the records PR in K.

## Stop conditions

- Review not clean after one repair cycle.
- CI red on the candidate.
- `main` moves unexpectedly, or the fast-forward push is refused.
- Readiness verdict is not `PASS`.
- Missing or interactive credentials for any step.
- The helper reports an unexpected gate state.
- Any live-step stop condition above.

## Out of scope

Deployments to systems outside this repository; changes to the threat model or the spec during the run.
