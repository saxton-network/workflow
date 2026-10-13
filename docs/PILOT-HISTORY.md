# Pilot history

This is a sanitized history of defects found while testing Workflow v3 itself. It intentionally omits private infrastructure details.

## Pilot 1: repository-only workflow

Goal: run a small non-deployment workflow through implementation, independent review, conditional repair semantics, evidence, and Git-only integration.

The first attempt stopped before implementation because the specification required workflow.terminal_task, but the validator accepted a v3 manifest that omitted it.

Repair:

- require workflow.terminal_task;
- require it to name a declared task;
- add missing and unknown terminal-task regression tests;
- preserve v2 compatibility.

The retry passed end-to-end with independent review, evidence checks, and no deployment stages.

## Pilot 2: read-only release readiness

Goal: exercise deployment source identity, authority, readiness, frozen-batch evidence, and approval-preview behavior without live mutation.

Independent review found two static-validation gaps before readiness ran:

1. A deployment graph could declare readiness as its terminal task, leaving live deployment and final reconciliation unfinished while appearing terminal.
2. A deployment graph could omit authority_remote and authority_ref when no authority-promotion task existed.

Repair:

- deployment terminal_task must equal final_reconciliation_task;
- every deployment graph requires nonempty authority remote/ref, even without a promotion task;
- add regression coverage for both cases.

## Pilot 3: live prerelease through the full deployment graph

Goal: run every Workflow v3 stage once for real (implementation, independent review, authority promotion, readiness with a frozen batch, an owner-approved live change, runtime acceptance, and final reconciliation) by publishing this repository's own `v0.1.0-alpha.11` prerelease. The full records are in `agent-work/pilot-alpha11/`.

What happened:

- The independent review passed the candidate on the first round, so the conditional repair task did not run.
- `main` was fast-forwarded to the reviewed commit, and readiness froze the batch, including the release ZIP's SHA-256, which `git archive` reproduces byte for byte.
- After the owner's explicit yes on a plain-language preview, one workflow dispatch published the release. The published ZIP and checksum file matched the frozen bytes exactly, and nothing else in the repository's tags or releases changed.
- The helper reported the gate states the plan predicted at every step: `GATED` before readiness, `PREVIEW` after it, `READY` after the approval record, and final reconciliation ready only after runtime acceptance `PASS`.

Findings, recorded for a later batch and not patched during the run:

1. `AGENTS.md` does not name this repository's own deployment authority; the pilot used its manifest plus `docs/RELEASING.md`.
2. After the live task completes, the helper shows it as `PREVIEW` again. This is the predicted quirk and was not mistaken for permission.
3. The helper has no divergence check for the records that follow a deployment. Applied by hand, `classify_divergence` reports the records as a protected change, because they add files the frozen batch names.
4. The rule to run git with no inherited `GIT_*` variables cannot apply to commands that reach the remote when the environment supplies git configuration that way. The docs could say which commands it covers.
5. The evidence `model` field has no guidance for repositories that keep model identifiers out of committed files.
6. Frozen batch paths mix two trees: the release source and the records branch. The spec does not say which tree a path refers to.
7. Repository settings (immutable releases) were checked as live facts; the frozen batch has no place for settings that are not files.
8. No test ties the documented default-port list or bracket rule to the code, and the builder's result overstated what its tests covered.
9. The terminal records cannot contain proof of their own merge, so task K is recorded `complete` before its step 4 (review, merge, `main` recheck); that step is reported outside them.
10. Only one model was available, so the reviewer was a separate agent on the same model, not a different vendor.

Follow-up, in the next change after Pilot 3:

- Finding 1: `AGENTS.md` names this repository's deployment authority.
- Finding 2: the helper labels a finished live task `DONE` when runtime acceptance passed, and `GATED` otherwise, instead of `PREVIEW`, even while the manifest status still lags behind a finished attempt record.
- Findings 3 and 9: `agent-work/WORKFLOW-SPEC.md` describes the records check after deployment, and how the records' own merge is reported.
- Findings 4 to 7: `agent-work/EVIDENCE-MANIFEST.md` says which git commands the `GIT_*` rule covers, what `model` holds when model identifiers stay out of the repository, which tree a batch path names, and how live settings are recorded.
- Finding 8: tests compare the documented default ports and bracket rule with the code.
- Finding 10: the pilot records say no other model was available, but the session's agent tool could in fact select a different model for a subagent. The coordinator missed this. The follow-up's independent review used a different model from its builder; its verdict and findings are recorded on the follow-up pull request (#14).

## Pilot 4: rollback drill

Goal: exercise the failure path live, on purpose. The drill covered:

- a failed runtime acceptance check;
- the stop at that check;
- an owner-performed rollback;
- verification against an exact baseline;
- how a failed workflow lands its records.

The full records are in `agent-work/pilot-rollback-drill/` (`drill: true`).

What happened:

- A drill prerelease `v0.0.0-drill.1` was published from `main` after the owner's explicit yes. One acceptance check was rigged to fail, as a declared exception: the frozen expected checksum had its hash replaced by zeros, and readiness proved locally that the rigged file and the correct file differed only in that hash.
- Checks 1–3 passed: the right commit was built, and the published ZIP is byte-identical to the frozen local build. Check 4 failed with exactly the declared signature, so the failure was the injected one.
- The coordinator stopped and recorded the attempt `failed`. The owner then deleted the release and then the tag, through direct links, one step at a time; each deletion was verified before the next.
- Final verification: every tag and every release, with every asset digest, equals the readiness snapshot exactly. alpha.12 and `main` are unchanged.
- **Drill verdict: PASS.**
- The helper reported what the plan predicted at every step. After the failure that included `PREVIEW` for J again and an "eligible for approval preview" line from `--ready`.
- Independent review of the drill contract before the live run caught five Low gaps, including that the Actions run must finish before the rollback reads the state. They were repaired before readiness.

Findings, recorded for a later batch:

1. After a failed live attempt, the helper offers the same fingerprint for a new approval preview, although the drill tag had been public. The retry boundary is enforced only by the contract, not by the helper. A fresh readiness record could be required before another preview.
2. The spec says a workflow completes only when its terminal task succeeds, and has no name for "stopped after verified rollback". This drill used an `other`-kind task (V) with `required_status = {J: "failed"}` to finish its work.
3. The spec treats a records `protected_change` as expected only after runtime acceptance passed. It does not cover records landed after a failed and rolled-back deployment.
4. The spec has no clause for a deliberately injected failure; the drill relied on a declared exception in its contract.
5. When review B found issues, the coordinator ran repair C without first setting B's manifest status to `findings`. The evidence held the `findings` record, but the manifest skipped that step, and the helper does not detect it afterwards.
6. Independent reviews of ordinary PRs, such as PR #15, are not recorded anywhere durable.
7. While a tag exists, GitHub serves a plain tag page at `/releases/tag/<tag>` even after the release is deleted. Rollback checks must use the API, not the page.
8. Draft visibility for the GitHub connection could only be inferred from write access, not observed.

## Current maturity

The repository-only path has passed a controlled pilot. The deployment path has passed one live pilot on its success path (Pilot 3) and one live rollback drill (Pilot 4). The drill exercised only the published-release-plus-tag row of the rollback matrix, performed by the owner by hand. The tag-only and draft rows, run cancellation, the retry boundary, and frozen-batch invalidation have not been exercised live.

The framework should still be treated as experimental: two live runs are not broad coverage, and Pilot 4's findings are open.

The important pattern is deliberate: a pilot finding stops advancement, becomes a narrow validator/test repair, receives independent review, and only then is the same scenario retried.
