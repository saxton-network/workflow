# Pilot plan: rollback drill through the Workflow v3 deployment graph

Status: revision 3, approved by the owner on 2026-10-13 with all eight recommended decisions.

## Goal

Pilot 3 (`pilot-alpha11`) exercised only the success path. This pilot exercises the failure path live, once, on purpose. It covers:

- a runtime acceptance check that fails;
- the stop at the first failed check;
- a rollback that removes what was published;
- fresh verification that the rollback restored the known-good state;
- evidence for a failed live attempt;
- how the helper reports a failed attempt;
- how a workflow that ends in rollback lands its records.

The coordinator records `agent-work/pilot-rollback-drill/evidence.json` and runs `scripts/agent-task.py` at every gate. Wherever the procedure, the helper or the docs get in the way, that is a pilot finding: recorded and reported, not patched during the run.

## Drill verdict (review finding 5)

The deployment is expected to fail; the drill is what succeeds or fails. **The drill succeeds if and only if all of these hold:**

1. the injected check, and only that check, failed, with the exact signature defined below;
2. the run stopped there;
3. the rollback removed exactly the drill items;
4. V verified that every tag and release matches the baseline exactly.

Otherwise the drill fails, and each deviation is a finding. J's result file and the `PILOT-HISTORY.md` entry state `drill: true` and this verdict, so nobody later reads the record as an accidental failed release.

## The live change

Publish a drill prerelease `v0.0.0-drill.1` of this repository with `.github/workflows/release.yml`, from the current `main`. Runtime acceptance includes one declared, injected fault that must fail it. Then roll back by deleting the drill release and its tag.

- **Name.**
  - `v0.0.0-drill.1` passes `scripts/check-release-version.sh` and is plainly not a real release.
  - In SemVer it sorts below every real version. GitHub lists releases by creation date, though, so on the Releases page the drill appears newest, directly above alpha.12.
  - It is never reused. The next real release is still `v0.1.0-alpha.13`.
- **Never "Latest."** `release.yml` passes `--prerelease` because the frozen dispatch inputs say `prerelease: true`. The pre-dispatch hash check of those inputs keeps that from changing.
- **Known-good state.** `v0.1.0-alpha.12` stays the newest real prerelease and is never touched. It cannot be republished faithfully if lost, because `release.yml` packages `main` HEAD, which has moved on from `c7ad3c3`. That is why the rollback steps below use direct links only.

## The injected fault and the declared deviation (CONTRACT.md; review finding 1)

**Declared deviation from the readiness rules.** The spec says readiness executes every required validator and freezes a proven batch. This drill deliberately freezes one expectation that is known to be wrong. It is asserted locally in R, where it must fail as declared, and live in check 4, where it is expected to fail. The spec has no clause for a known failure, so this is a declared exception. Readiness `PASS` means every other check passed and the injected file differs from the correct one exactly as declared. It does not mean the batch is free of known failures. The owner approves this deviation (decision 6), and the preview states it.

- Readiness freezes two expected files:
  - `results/R-expected-checksum.txt`: the correct bytes, `<sha256>  workflow-v0.0.0-drill.1.zip\n`.
  - `results/R-expected-checksum-INJECTED.txt`: identical except that the 64-character hash is replaced by 64 zeros.
- **Readiness proves the fault locally.** On the disposable local ZIP, R runs the same comparison acceptance will run. The locally computed `.sha256` line must equal the correct file (PASS) and differ from the INJECTED file (FAIL). The only difference must be the hash field, meaning bytes 0–63. If not, readiness fails.
- **Runtime signature of the injected failure.** The published `.sha256` asset:
  - equals `R-expected-checksum.txt` byte for byte;
  - differs from `R-expected-checksum-INJECTED.txt` only in bytes 0–63.

  Any other result is a **real** failure, recorded as such: a published asset that differs from the correct file, a difference outside the hash field, or a missing asset. The rollback still happens, and the drill verdict is a fail.

## Task graph (workflow ID `pilot-rollback-drill`)

| Task | Kind | What it does | Depends on |
| --- | --- | --- | --- |
| A | implementation | Identify the candidate: the current `main` head. No code changes, because every change since `v0.1.0-alpha.12` (PR #15, test only) was already independently reviewed and merged. Output: candidate SHA; Validate CI must be green on it. Branch: `pilot/rollback-drill-records`. | — |
| B | independent_review | Separate reviewer, on a different model from the builder. Confirms the candidate is exactly the reviewed `main`, with only reviewed changes since `v0.1.0-alpha.12`. Also reviews `CONTRACT.md`: the declared deviation, the injected fault and its signature, and the rollback matrix and verification. Verdict `passed` or `findings`. | A complete |
| C | repair (conditional) | Fixes B's findings. `CONTRACT.md` may change only before R, and each change is recorded. After R the contract is frozen, and any change means rerunning R and getting a new approval. The same reviewer re-reviews. | B findings |
| R | release_readiness | Read-only checks and frozen batch (below), including the local proof of the fault. Verdict `PASS`, `FAIL` or `UNKNOWN`. | B passed |
| J | live_deployment (human gate) | Owner's explicit y/n on the preview, then dispatch, runtime acceptance, the expected failure and the stop. J is recorded `failed` at the stop, before any deletion. | R complete |
| V | other | Rollback and its verification; runs only after J `failed`. First the owner's deletion steps through the rollback matrix, each verified after the owner reports it done; then the exact-baseline verification, the evidence, and the records PR. | J `failed` (explicit `required_status`) |
| K | final_reconciliation | Declared because a deployment graph needs it; never becomes ready. | J complete |

No authority-promotion task: the source is already on `main`. The manifest still declares `authority_remote = "origin"` and `authority_ref = "refs/heads/main"`. The independent plan review confirmed that this graph validates with the current helper.

The scaffold (this plan, `CONTRACT.md`, `manifest.toml`, task files, `results/README.md`) is compiled on `pilot/rollback-drill-records`, validated with the helper, and independently reviewed before task A starts.

## Status transitions (review finding 4)

| Task | Statuses the coordinator sets, in order |
| --- | --- |
| A | `pending` → `complete` |
| B | `blocked` → `passed` (or `findings` → C → re-review → `passed`) |
| C | `conditional` throughout unless B finds something |
| R | `blocked` → `complete` |
| J | `blocked` → `pending` → `in_progress` (approval record) → `failed` |
| V | `blocked` → `complete`; or `failed` if verification fails, in which case stop and report |
| K | `blocked` throughout |

**J is always recorded `failed` with `runtimeAcceptance: "FAIL"`, never `complete`.** This includes an unexpected pass: if the injected check passes, the fault went undetected. That is a High finding, and the rollback still happens. Recording `complete` would strand V, and with `PASS` would make K ready, a path this pilot must never take.

## Main freeze

From task R until V has verified the rollback, nothing else is merged into `main`.

## Readiness checks (R)

- **Source and validation:**
  - `origin/main` equals the source (`gitDivergence: {identical: true}`);
  - `bash scripts/validate-repository.sh` passes at the source;
  - Validate CI is green on the source.
- **Name is free:** no tag and no release, draft included, named `v0.0.0-drill.1`.
- **Rollback is possible:** immutable releases are off, recorded in `results/R-settings.json`. If they were on, readiness fails.
- **Baseline.** `results/R-baseline.json` records the exact full lists:
  - every tag with its target;
  - every release (drafts included) with ID, tag, flags and publish time;
  - alpha.12's asset digests.
- **Local ZIP:** built with `git archive --format=zip --prefix=workflow-v0.0.0-drill.1/ <source>`; two builds must be byte-identical.
- **Fault:** the local proof of the injected fault (above).
- **Frozen batch:**
  - the source;
  - the local ZIP hash;
  - `release.yml`;
  - `results/R-dispatch-inputs.json`;
  - `results/R-expected-checksum.txt`;
  - `results/R-expected-checksum-INJECTED.txt`;
  - `results/R-settings.json`;
  - four validators, all at the source;
  - no installed scripts;
  - rollback identity `github-release-v0.1.0-alpha.12`, with provenance;
  - the drill release page and its two download URLs as targets.

  Only data files live under `agent-work/pilot-rollback-drill/`.

## Live preview (J), shown to the owner before the y/n

- **Source:** the full commit SHA and the frozen-batch fingerprint.
- **Deviation:** a plain statement that one check is rigged to fail on purpose, how, and what counts as the expected failure versus a real one.
- **Commands:**
  - One `actions_run_trigger` `run_workflow` call: `release.yml`, ref `main`, inputs `{version: v0.0.0-drill.1, prerelease: true}`.
  - The run must be the only new `release.yml` dispatch run. If its `head_sha` is not the source, cancel it, then follow the rollback matrix: a tag may already exist.
- **Effects:**
  - a public lightweight tag `v0.0.0-drill.1`;
  - a public prerelease with two files and generated notes, listed above alpha.12 on the Releases page;
  - notifications to watchers.
- **Exposure:**
  - The drill tag and files are public from publication **until the owner deletes them**; this session cannot remove them.
  - Anyone may download or keep a copy meanwhile.
- **Owner availability (review finding 3):** the question itself is "Approve, and I am available now to delete the drill release and tag within 30 minutes? (y/n)". A "y" that does not confirm availability is treated as "n".
- **Verification:** see V below.
- **Stop conditions:**
  - any pre-dispatch recheck differs from readiness;
  - the wrong `head_sha` (cancel, then the rollback matrix);
  - any result other than the exact injected signature, which is recorded as a real failure and still rolled back;
  - V finds anything other than the drill items changed.
- **Retry boundary:** one dispatch. `v0.0.0-drill.1` is never reused; a repeat is `v0.0.0-drill.2`, with fresh readiness and a new approval.

Immediately before dispatch, the coordinator rechecks:

- `origin/main`;
- that the drill tag and release are absent, drafts included;
- immutable releases;
- every frozen file hash, including the dispatch inputs with `prerelease: true`.

## Rollback (review findings 2 and 9)

The owner deletes on GitHub. For the release there is a direct link, and the owner should not browse the Releases list:

- release: `https://github.com/saxton-network/workflow/releases/tag/v0.0.0-drill.1`

A tag has no page of its own with a delete button. It is deleted from the Tags page (`https://github.com/saxton-network/workflow/tags`), in the row named exactly `v0.0.0-drill.1`. That will be the only tag starting with `v0.0.0`. Each step is verified before the next.

The coordinator first reads the actual state and follows the matching row, deleting only what exists:

| State found | Owner steps |
| --- | --- |
| No tag, no release (run failed before tagging) | Nothing to delete. V verifies. |
| Tag only (cancelled or failed after tagging) | Delete the tag. |
| Draft release plus tag | Delete the draft release, then the tag. |
| Draft release, no tag | Delete the draft. |
| Published release plus tag (expected) | Delete the release, then the tag. |

A draft release is not reachable at the `/releases/tag/...` link. For any draft, the coordinator reads that draft's own `html_url` and release ID from the releases list and gives the owner that exact link. The owner opens only that link, checks that the title is `Workflow v0.0.0-drill.1` and that the release ID matches the one the coordinator names, then deletes.

1. **Release.** Open the direct link, check that the page title says `v0.0.0-drill.1`, press Delete (trash icon), and confirm. The coordinator then checks that the release is gone, drafts included, and that the tag is still there.
2. **Tag.** On the Tags page, find the row named exactly `v0.0.0-drill.1`, open its "…" menu, choose "Delete tag", and confirm. GitHub's exact wording may differ (an accepted unknown); the coordinator gives the clicks it can see described at that point, and never asks the owner to act on any other row. The coordinator then checks that the tag is gone and that all other tags still equal the baseline.

If the owner deletes only the tag first, GitHub turns the release into a draft. The matrix then shows "draft release, no tag", and the owner deletes that draft through its own link.

**If anything other than a drill item differs from the baseline at any point:** stop, dispatch nothing further, and report exactly what changed. For alpha.12 that means its recorded tag SHA `c7ad3c3b1ae3e0a07d7af0322f0688e7d4533c9f` and its asset digests, so the owner can decide how to restore it. Recreating the alpha.12 tag at that commit is possible; republishing its files is not, as explained above.

**At the stop.** The coordinator tells the owner, in plain words, which two items to delete and gives the exact links, so the deletion does not depend on this session or its check-ins surviving.

**Follow-ups (review finding 3).** After dispatch, the coordinator schedules two one-shot, read-only check-ins, at T+30 minutes and T+24 hours. Each rechecks the drill release and tag, reminds the owner if they still exist, and records the result. They never change anything. After V's final check they are switched off (`update_trigger` with `enabled: false`; this session cannot delete triggers). A check-in that fires first is harmless, because it is read-only.

## V: rollback verification

- The drill:
  - the release API returns 404 for the drill tag;
  - no release, draft included, has that tag name;
  - `git ls-remote` shows no drill tag;
  - both drill download URLs return 404.
- The full tag list and the full release list, drafts included, **equal `R-baseline.json` exactly**.
- alpha.12's asset digests are unchanged, and its downloaded ZIP hashes to its recorded digest.
- `main` is unchanged, and immutable releases are still off.

V then writes the drill verdict and lands the records PR.

## Expected helper behaviour

| When | Expected |
| --- | --- |
| Before R | J `GATED` |
| After R `PASS` | J `PREVIEW` |
| After the approval record | J `READY` |
| After J's final record (`failed`, `FAIL`) | J `PREVIEW` again for the same fingerprint, and `--ready` lists J as "ELIGIBLE FOR APPROVAL PREVIEW" alongside V. Neither is permission to retry; the retry boundary applies. Recorded as a finding to decide on, since the helper cannot know the tag was public. |
| After J `failed` | V `READY`; K `BLOCKED` throughout |
| Final state | "stopped after verified rollback", not complete, because terminal task K never succeeds. Whether the spec should name this end state is a question the pilot records. |

Any other difference is a finding and stops the run before any live step.

## Accepted unknowns (CONTRACT.md)

- **Runner tools.** The runner builds the ZIP; a different hash is a real failure.
- **Release notes.** Generated by GitHub and not frozen. They compare against a previous tag and may list a lot of history.
- **Action versions.** Pinned by tag; covered by the ZIP hash.
- **Website wording.** The exact labels of GitHub's delete controls are not frozen. Every deletion is verified through the API right after it happens.

## Records

The coordinator keeps `agent-work/pilot-rollback-drill/` on `pilot/rollback-drill-records`. In V, a records PR adds only that directory and a `docs/PILOT-HISTORY.md` entry. The PR:

- is checked for secrets;
- carries its divergence proof;
- is independently reviewed;
- is merged on the owner's go-ahead, then `main` is rechecked.

## Owner decisions

1. Approve this plan.
2. Use the drill version `v0.0.0-drill.1`: briefly public, listed above alpha.12 while it exists, notifies watchers, never reused.
3. Rollback by the owner on the GitHub website through direct links, one verified step at a time (recommended). The alternative is to first add a guarded rollback workflow in a separate reviewed PR, so the coordinator can delete.
4. At J, approve only when available to delete within 30 minutes. The coordinator follows up at T+30 minutes and T+24 hours.
5. Main freeze from readiness until the rollback is verified.
6. Accept the declared deviation: one live-only check is rigged to fail by freezing an expected checksum with 64 zeros in place of the hash, alongside the correct file.
7. The run's records land through a reviewed PR and ship in later release ZIPs, after a secrets check, marked `drill: true`.
8. The reviewer is a different model from the builder.
9. Later: the y/n on the live preview in J, the deletions themselves, and the go-ahead to merge the records PR in V.

## Out of scope

- Cancelling a run mid-flight on purpose.
- A run that fails before creating the tag.
- Frozen-batch invalidation.

Each could be a later drill; the rollback matrix handles the first two if they happen by accident. Changes to the threat model or the spec during the run are also out of scope.
