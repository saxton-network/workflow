# Plan: release v0.1.0-alpha.14 through the Workflow v3 deployment graph (Pilot 8)

Status: revision 2, approved by the owner on 2026-10-14 with owner decisions 1–8. It is modelled on the approved alpha.13 plan (`agent-work/release-alpha13/PLAN.md`); differences are called out. Revision 2 applies plan-review round 1 (M1–M3, L1–L5, N1–N3); round 2 approved it, and its two Lows and one Nit are applied here as clarifications that make the plan stricter.

## Goal

- **Package the fixes.** Publish `v0.1.0-alpha.14`, which packages everything merged since `v0.1.0-alpha.13` (`84d826a`).
- **Use the newest rules live.** In particular:
  - Readiness proves that the coordinator can read every piece of acceptance evidence with the client it will use at acceptance (Pilot 7 finding 1).
  - The helper keeps a live task `GATED` when the manifest records it `failed` (PR #25).

Where the procedure, the helper or the docs get in the way, that is a pilot finding: recorded and reported, not patched during the run.

## The live change

Publish `v0.1.0-alpha.14` as a GitHub prerelease with `.github/workflows/release.yml`, from `main`.

- **A prerelease.** It is never "Latest". `v0.1.0-alpha.13` and every other release stay published and unchanged.
- **Packaging.** `release.yml` packages `main` HEAD with `git archive`. Readiness builds the ZIP twice and reproduces alpha.13's published ZIP from `84d826a`, so it can freeze the exact artifact hash.
- **Speed.** Pilot 6's run took 16 seconds. The tag is created within those seconds; a dispatch cannot be recalled, and a cancel will not reliably beat the tag step (`docs/RELEASING.md` "Timing").

## Content of the release

These are the three merges since `v0.1.0-alpha.13`, 35 files and about 1,650 added lines in all. Each has a durable review record on its pull request.

- **#22:** the Pilot 6 records (`agent-work/release-alpha13/`) and the Pilot 6 history entry.
- **#24:** the Pilot 7 history entry. It covers the adopter upgrade, the failed acceptance and the verified rollback.
- **#25:** the deferred Pilot 6 and Pilot 7 findings:
  - the helper's manifest-`failed` gate, with tests;
  - README's four gate states;
  - RELEASING (drafts, timing, `published_at`);
  - RESULT-TEMPLATE;
  - the threat model's historical table;
  - WORKFLOW-SPEC (a manifest `failed` status closes the gate; the status is reset to `pending` when a new attempt starts);
  - ADOPTING (owner decisions next to rules, commit identity, evidence access, row form);
  - the coordinator's handover identity check.

The ZIP carries every pilot record. That includes the owner's public GitHub username, which was already in alpha.13. It also includes the public adopter repository's history as Pilot 7 describes it. The Pilot 7 entry mentions that a personal identity reached the site's history, but names neither the person nor the address.

## Deployment authority

`authority_remote = "origin"`, `authority_ref = "refs/heads/main"`, as `AGENTS.md` and `docs/RELEASING.md` declare.

## Task graph (workflow ID `release-alpha14`)

| Task | Kind | What it does | Depends on |
| --- | --- | --- | --- |
| A | implementation | Identify the candidate: the current `main` head (`02c771a7c7d71e2303c186d0c150e903a524e949` when this plan was written; any other merge before R restarts A and B). No code changes; output the candidate SHA. Validate CI must be green on it. Branch: `pilot/alpha14-records`. | — |
| B | independent_review | Release review. See the B section below. | A complete |
| C | repair (conditional) | Fixes B's findings through an ordinary PR, merged on the owner's go-ahead (see C below). The same reviewer re-reviews. | B findings |
| R | release_readiness | Read-only checks and the frozen batch (below). | B passed |
| J | live_deployment (human gate) | The owner's explicit y/n; one dispatch; runtime acceptance. | R complete |
| V | other, `required_status = {J = "failed"}` | After a failed attempt that may have published something: read the actual state, give the owner the rollback deletions one at a time, verify the baseline, and land the records. | J failed |
| K | final_reconciliation | Verify refs and the release, and land the records. | J complete with runtime acceptance PASS |

There is no authority-promotion task: `main` already holds the candidate, as in Pilots 4 and 6.

Before task A starts, the coordinator does three things on the records branch:

- compiles the scaffold: this plan, `CONTRACT.md`, `manifest.toml`, the task files and `results/README.md`;
- validates it with the helper at `main`;
- has it reviewed independently (`results/scaffold-review.md`).

Before its first commit, the coordinator checks `git config user.name` and `user.email` against the no-reply identity used for this repository's coordinator commits (`COORDINATOR.md` Startup step 10).

## B: release review

- **Reviewer.** A separate agent, pinned to a different model from the one that built every change under review. The coordinator checks the observed model in the reviewer's own transcript in every round.
  - The model is recorded in words in `results/B-n.md`, with `model: null` in the evidence.
  - A review that turns out to be on the builder's model is a deviation, not independence.
- **Additional review.** This release review is on top of the per-PR reviews already done. It covers:
  1. The candidate is exactly `main`, and contains only merged, reviewed changes since `84d826a`.
  2. The release as a whole, against `docs/THREAT-MODEL.md`:
     - the helper's behaviour after #25, replayed on the earlier pilot records;
     - the full test suite on Python 3.11, 3.12 and 3.13;
     - docs consistent with each other and with the code.
  3. Nothing private in the ZIP:
     - no tokens or keys;
     - no real email addresses other than the no-reply trailer (test fixtures such as `example.invalid` addresses are not real);
     - no personal names other than the owner's public username;
     - no local machine paths, and no session links in shipped files;
     - no private repository names.
  4. `CONTRACT.md`.
- **Verdict.** `passed` or `findings`.

## C: repair (only if B finds something)

- **Making and landing the fix.** The fix is an ordinary PR, reviewed by the same reviewer. It is merged on the owner's go-ahead, following `COORDINATOR.md` "Commands that move refs".
- **New candidate.** The candidate becomes the new `main` head, the merge commit. The C record's `candidateSha` is that head, and B re-reviews exactly that SHA.
- **Helper version.** If the repair changes `scripts/agent-task.py`, the coordinator merges `main` into the records branch before running the helper again.
- **Another round.** For a second round, B goes back to `findings` and C to `pending` in the same records commit.
- **Contract changes.** `CONTRACT.md` may change only before R, and each change is recorded.

## Main freeze

Nothing else merges into Workflow's `main` from R until one of these happens:

- J's runtime acceptance passes;
- V has verified a rollback;
- after a proven `liveStateChanged: false`, the owner says how to continue. If the owner chooses a retry, the freeze continues into the new readiness cycle.

Until then, the only permitted merge is the records PR in the proven-`false` case.

- **By agreement only.** GitHub cannot enforce the freeze.
- **How a breach is detected:**
  - the pre-dispatch recheck;
  - the run's `head_sha` check;
  - the "`main` still equals the source" acceptance check.
- **After the freeze.** The records PR is an ordinary reviewed merge.
- **The site is not frozen.** The site repository's `main` is not frozen: `release.yml` packages Workflow's `main` only.

## Readiness checks (R)

- **Source.**
  - `origin/main` equals the source. Record `gitDivergence` `identical: true`, proven in a non-shallow clone with no inherited `GIT_*` variables.
  - `bash scripts/validate-repository.sh` passes at the source in a clean worktree.
  - Validate CI is green on the source.
- **Name is free.** There is no tag `v0.1.0-alpha.14` (check the API ref and `git ls-remote`). There is no release or draft with that name. Drafts are read through the authenticated release list, and the identity that read them is recorded.
- **Rollback is possible.** Both are recorded in `results/R-settings.json`:
  - immutable releases are off;
  - no ruleset blocks tag creation or deletion (`GET /repos/saxton-network/workflow/rulesets` is empty).
- **Evidence access (new, Pilot 7 finding 1).** Readiness proves every read in the contract's "Evidence clients" table, on the latest earlier `release.yml` run and the alpha.13 release, with the client named there:
  - the primary client for every item;
  - the fallback client for every item that has one;
  - the `curl` downloads of alpha.13's ZIP and `.sha256`, with their bytes hashed against the known digests;
  - the release API's per-asset `digest` field for both alpha.13 assets, read through the connection;
  - `curl`'s remaining API allowance (`X-RateLimit-Remaining`), recorded together with the number of `curl` API requests acceptance will make.

  A read that readiness cannot prove is a stop condition. The job log is read once as a diagnostic, and is not required.
- **Tools.**
  - Workflow dispatch is proven available, but not exercised.
  - Run cancel is available but not exercised.
  - This session cannot delete a release or tag; the owner does any deletion.
  - The local git version and the GitHub identity used are recorded.
- **Reproducible ZIP.**
  - `git archive --format=zip --prefix=workflow-v0.1.0-alpha.14/ <source>` is built twice, and the two builds are byte-identical.
  - The same command at `84d826a` reproduces alpha.13's published ZIP digest, `e520b61c3c48572b73001d333b2c79499e33b3e5c19f34988d5be2f3e191d5d4`.
- **Expected `.sha256` line.** It is made exactly as `release.yml` makes it: `sha256sum workflow-v0.1.0-alpha.14.zip`, run in the ZIP's directory. It must match `^[0-9a-f]{64}  workflow-v0\.1\.0-alpha\.14\.zip\n$`.
- **Baseline** (`results/R-baseline.json`):
  - every tag with its target;
  - every release, drafts included, with ID, tag, flags and `published_at`;
  - alpha.13's asset digests;
  - the latest `release.yml` run ID, so that "exactly one new run" can be checked.
- **Frozen batch.** The `agent-work/release-alpha14/…` files are committed on the records branch before R hashes them.
  - `deploymentSourceSha`: the source.
  - `deployableArtifactSha256`: the local ZIP's SHA-256.
  - `deploymentConfiguration`, each with its SHA-256:
    - `.github/workflows/release.yml`;
    - `agent-work/release-alpha14/results/R-dispatch-inputs.json` (ref `main`, `release.yml`, version `v0.1.0-alpha.14`, `prerelease: true`);
    - `agent-work/release-alpha14/results/R-expected-checksum.txt`;
    - `agent-work/release-alpha14/results/R-settings.json`;
    - `agent-work/release-alpha14/CONTRACT.md`.
  - `validators`, read at the source:
    - `scripts/validate-repository.sh`;
    - `scripts/check-release-version.sh`;
    - `scripts/agent-task.py`;
    - `scripts/tests/test_agent_workflow.py`.
  - `installedScripts`: none.
  - `rollbackArtifact`: identity `github-release-v0.1.0-alpha.13`, provenance `agent-work/release-alpha14/results/R-rollback-alpha13.md`. That file holds alpha.13's tag target and verified asset digests.
  - `deploymentTargets` (mode `null`):
    - the release page `https://github.com/saxton-network/workflow/releases/tag/v0.1.0-alpha.14`;
    - the two asset download URLs;
    - the tag ref `https://api.github.com/repos/saxton-network/workflow/git/ref/tags/v0.1.0-alpha.14`.

## Contract (`CONTRACT.md`)

### Accepted unknowns

- **Runner tools.** The runner's git and zlib build the published ZIP. A hash mismatch fails acceptance, even if the files match.
- **Release notes.** These are generated by GitHub (`--generate-notes`) and not frozen. They will list PRs #22, #24 and #25 by title and contributor, with a compare link.
- **Action versions.** Pinned by tag; covered by the ZIP hash check.
- **Website wording.** The labels of GitHub's delete controls are not frozen. Every deletion is verified through the API.

### Evidence clients

This is decided before approval (Pilot 7 finding 1). The connection is the session's authenticated GitHub connection. `curl` sends its requests through the session's network proxy, which adds the session's GitHub credentials; it is a separate client from the connection (see the plan's 2026-10-14 clarification).

| Check | Item | Primary client | Fallback client |
| --- | --- | --- | --- |
| Run | Run list, `head_sha`, conclusion | connection | none |
| Run | Job-step list (for `liveStateChanged`) | connection | none |
| Release | Release by tag: title, draft, prerelease, assets, `published_at` | connection | `curl` (public API) |
| Release | Not latest (`/releases/latest` is not alpha.14) | connection | `curl` (public API) |
| Release | Release list, drafts included | connection | none |
| Release | Asset digests (the API `digest` field) | connection | none |
| Release | Asset bytes (ZIP and `.sha256`) | `curl` download | none |
| Release | Unpacked ZIP equals `git archive` of the source | local `unzip` and `diff -r` | none |
| Refs | Tag ref and its `object.type` | connection | `curl` (public API) |
| Refs | Tags and `refs/heads/main` | `git ls-remote` | none |

The rules:

- **When the fallback is used.** It is used only when the primary returns no evidence (an error, a timeout, or the item not yet visible).
- **Both clients answered.** Readiness reads both clients for every item that has a fallback, and records that they agree. At acceptance the fallback is read only when the primary returned nothing. If both were read, they must agree, and a disagreement is a FAIL.
- **The asset bytes.** For the ZIP, the bytes from `curl` and the API `digest` field must both match the frozen hash. For the `.sha256` asset, the bytes must equal `R-expected-checksum.txt`, and the API `digest` field must equal that file's SHA-256.
- **Nothing else substitutes.** No other client stands in for a missing read.
- **Diagnostic only.** The job log is diagnostic only.

### Dispatch

- **The recheck.** It runs seconds before the dispatch, and its output must be read clean before the dispatch is issued. With the evidence clients, it rereads the `main` tip, the tags, the release list including drafts, the settings, the frozen hashes, the rebuilt ZIP hash and the latest `release.yml` run ID. The dispatch is a single tool call of its own, never batched with the recheck.
- **If the recheck fails:** dispatch nothing, leave J `in_progress`, stop and ask the owner. The helper may still show J `READY`, because the approval record is intact. That is not permission, and not a finding.
- **If the dispatch call errors, or no single new run appears:** never dispatch again. Re-list the runs for up to 2 minutes, then stop and ask the owner.
- **Waiting for the run.** Wait up to 12 minutes for it to finish; `release.yml` has a 10-minute limit. If it is still running after that, cancel it, wait until it is `completed`, and record J `failed`.

### Runtime acceptance

Checks run in order and stop at the first failure.

**One acceptance window.** It is 10 minutes, starting when the run completes.
- **Read returned no evidence** (an error, a timeout, or evidence not yet visible): within the window, the read may be repeated with the same client, or its fallback.
- **Read returned evidence that fails the check:** that is a FAIL. It is never re-read to get a different answer.
- **No evidence by the end of the window:** the check fails.
- **Evidence obtained after a check has failed** never turns that check into a pass.
- **A repeated read is never a reason to dispatch again.**
- **What counts as evidence.**
  - `/releases/latest` returning 404, or naming another release, is evidence that alpha.14 is not latest; a 200 naming alpha.14 is a FAIL.
  - In the `liveStateChanged` proof, a tag-ref 404 is definitive evidence of absence, not "not yet visible".
  - A download that errors or is shorter than the API `size` is no evidence and may be retried. A full-size download with the wrong hash is a FAIL.

1. **The run.**
   - Exactly one new `release.yml` run since the baseline run ID.
   - `head_sha` equals the `main` tip recorded at the recheck.
   - Conclusion: success.
2. **The release.**
   - The release is titled `Workflow v0.1.0-alpha.14`, is published (not a draft), is a prerelease, and `/releases/latest` is not alpha.14.
   - It has exactly two assets, `workflow-v0.1.0-alpha.14.zip` and `workflow-v0.1.0-alpha.14.zip.sha256`.
   - The ZIP's SHA-256 (from the downloaded bytes) and the API `digest` field both equal the frozen hash.
   - The `.sha256` asset bytes equal `R-expected-checksum.txt`.
   - The unpacked ZIP equals `git archive` of the source.
   - `published_at` is recorded as the publish time; `created_at` is not used (`docs/RELEASING.md` "Evidence").
3. **Refs.**
   - The tag is a lightweight ref at the source: the ref's `object.type` is `commit`, and `git ls-remote` agrees.
   - alpha.13's digests, and every other tag and release, match the baseline.
   - `main` still equals the source (`git ls-remote origin refs/heads/main`).

### A run built from the wrong commit

If `head_sha` is not the source, the tag and release probably already exist. Cancel only if the run is still before its "Create release tag" step. In every case:

1. wait until the run is `completed`;
2. record J `failed`;
3. read the actual state, and follow the rollback matrix.

### Every failed attempt records `liveStateChanged`

It is `false` only when all of these hold, with a one-line reason in `J.md`:

1. The run is `completed` with conclusion `failure`.
2. Its job-step list shows "Create release tag at the validated commit" as skipped, or never started.
3. The tag ref returns 404 from both the connection and `curl`, and `git ls-remote --tags` shows no `v0.1.0-alpha.14`.
4. The authenticated release list, drafts included, shows no alpha.14 and otherwise equals the baseline.

Otherwise it is `true`. That includes a cancelled run, a run that stopped at or after the tag step, and anything still running.

It is `null` if any of these reads is missing or the clients disagree, and `null` is treated as `true`. Repeating a read is never used to turn `true` or `null` into `false`.

### Rollback (V)

V runs only after J `failed` with `liveStateChanged` not `false`.

- **Run finished first.** V first makes sure the run is `completed`, cancelling and waiting if it is not.
- **Act only on what exists.** V reads the actual state and follows the matching row, deleting only what exists:

| State found | Owner deletes, one item at a time, each verified through the API before the next |
| --- | --- |
| No tag and no release, found after the run finished | Nothing to delete. V verifies the baseline, records it, and is recorded `complete`. The end state is "stopped after verified rollback". The name alpha.14 is still not reused, because `liveStateChanged` was not proven `false`. |
| Tag only | The tag. |
| Draft release plus tag | The draft (through its own link), then the tag. |
| Draft release, no tag | The draft. |
| Published release plus tag | The release, then the tag. |

- **Links given to the owner.**
  - A published release: `https://github.com/saxton-network/workflow/releases/tag/v0.1.0-alpha.14`.
  - A draft: that draft's own `html_url`, with its release ID, read from the authenticated list.
  - The tag: the Tags page `https://github.com/saxton-network/workflow/tags`, in the row named exactly `v0.1.0-alpha.14`.
- **Order matters.** `docs/RELEASING.md` says deleting the tag first is understood to turn a release into a draft, but this has not been observed. Either way, V reads the actual state after each step and follows the matching row. A published release with no tag (after an out-of-order deletion) means deleting the release.
- **Never anything else.** The owner is never asked to act on any other release or tag. If anything other than alpha.14 items differs from the baseline, the coordinator stops and asks.
- **Final verification.**
  - The release API returns 404 for alpha.14, and no release or draft carries that tag.
  - `git ls-remote` shows no tag, and both download URLs return 404.
  - The full tag and release lists equal `R-baseline.json` exactly.
  - alpha.13's digests and ZIP are unchanged.
  - `main` is unchanged, immutable releases are off, and there are still no rulesets.
- **End state:** "stopped after verified rollback".
- **Check-ins.** After a failed attempt that left something public, the coordinator schedules one read-only check-in at T+30 minutes, and another at T+24 hours if items still exist. Each one rereads the state and reminds the owner. They stop once V has verified.

### No rollback needed

When `liveStateChanged: false` is proven:

- V is recorded `failed`, with "rollback not needed" and the reason.
- K stays blocked. The end state is **"stopped; nothing published, proven"**.
- The coordinator asks the owner how to continue, and lands the records through a reviewed PR on the owner's go-ahead.
  - That merge moves `main`, so a retry after it starts again from tasks A and B. The owner chooses, at that go-ahead, whether to land the records before or after a retry.
  - The expected `protected_change` is recorded as a deviation note.

### Retry boundary

- **One dispatch.** Any retry needs fresh readiness and a new approval. J's manifest status is reset to `pending` when that cycle starts (`WORKFLOW-SPEC.md`).
- **Name reuse.** The name `v0.1.0-alpha.14` may be reused only after a proven `liveStateChanged: false`. Once a tag or release has existed, even briefly or as a draft, a retry is `v0.1.0-alpha.15`.

## Approval record (J)

`agent-work/release-alpha14/results/J-approval.md` follows `COORDINATOR.md` "Approval records". It records:

- when the preview was shown, the exact question, and the owner's literal answer;
- the source and fingerprint;
- **approved actions:**
  1. the single dispatch, with `R-dispatch-inputs.json` and its SHA-256;
  2. a conditional run cancel, used only when:
     - the run built the wrong commit and is still before its tag step;
     - it is still running after 12 minutes;
     - V finds it not `completed`;
- **owner actions under this approval:** the deletions in the rollback matrix, only if J failed with `liveStateChanged` not `false`;
- **not covered:** a retry, another version or source, any settings change, or any deletion by the coordinator;
- a statement that it is the coordinator's own account of a chat approval;
- any dated plan clarifications in force.

## Live preview (J), in plain language

- **What is published:** the commit, the fingerprint and the three PRs it packages.
- **The single dispatch.**
- **The effects:**
  - a public tag;
  - a public prerelease with two files, and generated notes listing PRs #22, #24 and #25;
  - notifications to watchers.
- **Exposure:** public until deleted. The ZIP includes all pilot records and the owner's public username.
- **Timing:** about 15 seconds; it cannot be recalled once started.
- **The checks:** which tool reads each one, and the stop conditions.
- **If GitHub's read tools fail.** Acceptance has 10 minutes. If GitHub's read tools or the download tool still cannot read the evidence by then, that counts as a failed check, and I will ask you to delete the release even if it was correct. Readiness proves beforehand that every tool can read what it needs.
- **The rollback:** the owner deletes, using exact links; the coordinator cannot.
- **The retry boundary.**
- **The main freeze.** Please do not create or delete any other release or tag, or merge into Workflow's `main`, until it ends.
- **"Latest."** alpha.14 will not show as "Latest".
- **Immutable releases.** Leave the setting off; if it were turned on, the release could not be rolled back.
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
| J's manifest status set to `failed` | J `GATED`. With no failed live record, the task view says "manifest records this live task as failed" (new in #25). With a failed record, it says "the latest live attempt failed". |
| A mid-run stop | J is recorded `failed` with `runtimeAcceptance: "FAIL"`; then J shows `GATED`. |
| Repair rounds | B `findings`, then C ready. A second round needs B back to `findings` and C back to `pending`. |

Any other difference is a finding.

## Clarifications

Dated entries go here. Two kinds of change are recorded here before the task runs:

- a task file that makes a check stricter;
- a task file that swaps in an equal or stronger proof.

The next independent review checks each entry, and the next owner preview lists it. Anything weaker or wider, or anything that changes the live batch, needs a revised plan and a new approval.

- **2026-10-14, during R, before the contract is hashed (a correction of fact, nothing weakened).** The plan described `curl` as making unauthenticated public requests. Readiness found that the session's network proxy adds the session's GitHub credentials to `curl`'s requests: the rate limit is 15,000 per hour, and an authenticated-only endpoint answers. `curl` is still a separate client from the connection (a different program and request path), so every rule about primary and fallback clients and agreement is unchanged. The contract's wording is corrected to match. The next independent review is the records review; the next owner preview lists this entry.

## Records

The coordinator keeps `agent-work/release-alpha14/` on `pilot/alpha14-records`. It holds:

- `PLAN.md`, `CONTRACT.md`, `manifest.toml`, the task files and `evidence.json`;
- `results/`:
  - `README.md`, `plan-approval.md` and `scaffold-review.md`;
  - `A.md`, `B-n.md` and `C-n.md`;
  - `R.md`, `R-baseline.json`, `R-settings.json`, `R-rollback-alpha13.md`, `R-dispatch-inputs.json` and `R-expected-checksum.txt`;
  - `J-approval.md` and `J.md`;
  - `K.md` or `V.md`.

The records PR adds only that directory and a `docs/PILOT-HISTORY.md` "Pilot 8" entry.

- **Proof and scan.** It carries the divergence proof and a secrets scan. The expected `protected_change` covers only the frozen files under the workflow directory.
- **Landing.** It is independently reviewed and landed on the owner's go-ahead: a local `--no-ff` merge under the coordinator's no-reply identity, pushed as a fast-forward. Every push follows `COORDINATOR.md` "Commands that move refs". A merge through GitHub's merge API is not used, because it authors the commit with the owner's account email.
- **Afterwards.** `main` and the release are rechecked. The records ship in the next release's ZIP.

## Owner decisions

1. Approve this plan.
2. A main freeze on Workflow from R until one of these happens: runtime acceptance passes, a rollback is verified, or, after a proven `liveStateChanged: false`, you say how to continue.
3. Rollback means the owner deletes the release and tag on GitHub, through exact links, when asked. The coordinator cannot delete.
4. Name reuse: alpha.14 is reused only if nothing was ever created; otherwise a retry is alpha.15.
5. A ZIP hash mismatch fails acceptance even if the files match.
6. The acceptance read rules (Contract, "Evidence clients" and "Runtime acceptance"):
   - each check uses the named tool, with a fallback only where the table lists one;
   - there is one 10-minute window;
   - a read outage that lasts the whole window fails the check, and starts the rollback even for a correct release.
7. The release notes are GitHub's generated text, listing PRs #22, #24 and #25.
8. The run's records, including the owner's public username, ship in a later release ZIP after a secrets check.
9. Later:
   - the y/n on the live preview in J, with availability to delete within 30 minutes;
   - the go-ahead to merge the records PR;
   - if B finds anything, the go-ahead to merge the repair PR.

## Stop conditions

- B is not clean after two repair rounds.
- CI is red on the candidate.
- `main` moves unexpectedly.
- The readiness verdict is not `PASS`, including any evidence read that readiness cannot prove.
- Credentials are missing or interactive.
- The helper shows a gate state other than the expected table.
- Any dispatch or acceptance stop condition above.

## Out of scope

- Code changes during the run, other than a reviewed repair in C.
- Changes to the threat model or the spec during the run.
- Upgrading `saxton-network/site` to alpha.14 and putting its v2 live, which is a later, separate workflow.
