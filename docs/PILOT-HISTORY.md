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
9. The terminal records cannot contain proof of their own merge; that last check is reported outside them.
10. Only one model was available, so the reviewer was a separate agent on the same model, not a different vendor.

## Current maturity

The repository-only path has passed a controlled pilot. The deployment path has passed one live pilot (Pilot 3), a low-risk prerelease of this repository.

The framework should still be treated as experimental: one live run is not broad coverage, and Pilot 3's findings are open.

The important pattern is deliberate: a pilot finding stops advancement, becomes a narrow validator/test repair, receives independent review, and only then is the same scenario retried.
