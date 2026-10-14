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

Follow-up, in the next change after Pilot 4:

- Finding 1: the helper keeps the live task `GATED` after a failed attempt until a fresh readiness record exists, so it no longer offers the same fingerprint for a new approval preview.
- Findings 2, 3 and 4: `agent-work/WORKFLOW-SPEC.md` names the end state "stopped after verified rollback", allows records after a verified rollback, and defines drills with declared injected failures.
- Finding 5: `agent-work/COORDINATOR.md` requires setting a review's `findings` status before dispatching repair, and dispatching only what `--ready` lists.
- Finding 6: `agent-work/COORDINATOR.md` requires one durable PR comment for independent reviews outside a workflow directory.
- Findings 7 and 8: `docs/RELEASING.md` describes rollback order, API-based verification, and draft visibility.

## Pilot 5: first adopter project, `saxton-network/site`

Goal: run Workflow end to end in a new repository with a real live target. The repository was adopted by a fresh builder that had not seen Workflow before; the two workflows were then run by a coordinator and reviewers that knew it. The project is a one-page GitHub Pages landing page listing the organisation's public repositories. It ran two workflows:

- `site-launch`, the success path;
- `site-update-drill`, a deliberate failure and rollback.

The full records are in `saxton-network/site` under `agent-work/site-launch/` and `agent-work/site-update-drill/`, with the adoption log in its `ADOPTION.md`.

What happened:

- **Adoption.** A fresh builder adopted Workflow at `3d38b27` from an export without the pilot history. It was graded against a hidden 17-item checklist, and all 17 passed. It logged 21 places where the docs were unclear for a newcomer. The bootstrap review found one Medium: `validate.sh` silently skipped hash rows it could not parse. That was repaired before merge.
- **Turning on Pages** was treated as its own live change, with a preview and the owner's approval.
- **`site-launch`.**
  - The site check went through four independent review rounds and three repair rounds (F1–F7: CSS escapes, parser-dependent comments, a deploy ancestry guard, a timeout, repository names outside links, `<applet>`, and entity-encoded or look-alike names).
  - One Low (F8) was batched as out of scope, since it needs deliberate tampering by a trusted author.
  - After the owner's yes, one deploy ran. The live bytes equalled the frozen hash on the first fetch.
  - The records landed as the expected `protected_change`.
- **`site-update-drill`.**
  - v2 changed only the page.
  - Under one approval covering both dispatches, v2 was deployed. Check 2a proved the v2 bytes were live, and the injected check 2b failed exactly as declared.
  - The coordinator then redeployed v1 with one dispatch of the same deploy code. The live bytes equalled v1 on the first fetch.
  - **Drill verdict: PASS.** End state "stopped after verified rollback": `main` holds v2 while the site serves v1.
- Both workflows' records were reviewed independently and landed on the site's `main` with the owner's go-ahead (site PRs #2 and #3). Each landing was a local `--no-ff` merge pushed as a fast-forward, and each touched only its workflow directory.
- The scaffold review of the drill caught that a failed J with no v2 deploy would still make V ready, which would trigger a needless live dispatch. The contract was fixed before anything was frozen.

Findings, recorded for a later batch. Unless marked otherwise, each can be checked against the site records.

1. **Adoption docs.** The 21 entries in the site's `ADOPTION.md` "Ambiguities". The main ones:
   - which files are "the workflow control files";
   - Quick start step 5 runs `validate-repository.sh`, which is Workflow-specific;
   - Quick start step 3 conflicts with plan approval;
   - extending versus replacing `AGENTS.md`;
   - a threat model that covers only Workflow;
   - no guidance for GitHub Pages (artifact, rollback, target, and the no-trailing-separator destination rule);
   - settings changes as live changes;
   - undocumented Python 3.11+;
   - references to files an adopter does not get;
   - a content rule against naming people or emails conflicting with the mandated commit identity and trailers (entry 17).

   *Suggested action:* an adopter's guide that lists the files to copy, provides a template `validate.sh`, says how to write a local threat model, and covers Pages-style targets.
2. **Approval reference.** The docs say to "bind the user's explicit y/n approval reference" to the fingerprint, but do not say what that reference is when approval is given in chat. These pilots used a coordinator-written `J-approval.md`, which the coordinator attests itself. *Suggested action:* define the approval record's required content (source, fingerprint, each approved dispatch with its input hash, and conditions) and say plainly that it is self-attested when approval is given in chat.
3. **Repository creation.** The session's GitHub connection was refused permission to create a repository in the organisation. The owner created it, and GitHub added a starter commit that does not use the mandated identity. *Suggested action:* list repository creation as a possible owner step, and say how a pre-existing starter commit is handled.
4. **Reviewer model.** After a session restart, resumed reviewer agents came back on the builder's model. Two early reviews were therefore same-model; they are recorded as deviations. From then on, each review used a fresh agent pinned to a different model, and its transcript's model field was checked. *Suggested action:* require reviewers to record the model observed in their transcript, and say that a resumed reviewer must be re-checked.
5. **Repair rounds.** A second repair round needs the repair task reset to `pending` by hand before the helper lists it again. This is not documented. *Suggested action:* document the reset in `COORDINATOR.md`, or have the helper offer the repair task again whenever the review is `findings`.
6. **Review convergence.** An allow-list check of free-form HTML kept finding new encodings to cover. The threat model's exclusion of deliberate tampering by a trusted author is what ended the loop. *Suggested action:* state that stopping rule for guard-style validators in the threat-model guidance.
7. **Plan drift.** The plan's readiness section said an unauthenticated GET proves a repository public. The session proxy returns 403 there, so the task files switched to an authenticated read of the `private`/`visibility` field. Plan text and task files drifted apart; the drift was disclosed, not fixed. *Suggested action:* say which document governs when the plan and a task file disagree, and require the drift to be recorded in the plan.
8. **Pages deployment labels.** `actions/deploy-pages` labels each deployment with `GITHUB_SHA`, which is `main`'s tip on a dispatch, not the deployed input. The v2 deploy and the v1 rollback are both labelled with the v2 commit. Only the job log's `DEPLOY HEAD` line and the live bytes show what is served. *Suggested action:* note in `docs/RELEASING.md`-style guidance that deployment labels must not be used as evidence of the live commit.
9. **Shallow clones.** A first-parent ancestry proof run in the session's shallow clone could not see history and failed. A fresh full fetch was needed. *Suggested action:* say that ancestry proofs need a non-shallow clone (`git rev-parse --is-shallow-repository` is `false`).
10. **Coordinator shell errors**, both with no live effect:
    - *Reported by the coordinator, not in the site records* (it happened while landing the `site-launch` records, which are reported outside the records). A chained command continued after a failed `git merge` and ran `git push origin $M:refs/heads/main` with `$M` unset, which is the delete refspec `:refs/heads/main`. The captured last line of the push output was "Everything up-to-date", which does not match what a delete refspec normally prints, so it is not evidence of what happened. The checked fact is that `git ls-remote` showed `main` unchanged straight after. Why no delete happened was not established; the guard was luck, not design.
    - *In the site records* (`agent-work/site-update-drill/results/P.md`). A first-parent check used `grep -q` after a pipe under `set -o pipefail`. It returned 141 (SIGPIPE), printed nothing, and the push on the next line was not gated on it. The check would have passed and was re-run straight after.

    *Suggested action:* gates should be explicit `if ! …; then exit 1; fi` steps before the push, and a push should name a literal, asserted SHA. Avoid `grep -q` after a pipe under `pipefail`.
11. **Gating V, and other contract gaps.** The helper makes V ready on J's status alone, whether or not a dispatch happened. The drill's scaffold review also found that the contract did not say:
    - what to do when a dispatch call gets no `204` or no run appears (S3);
    - what V's status is when no rollback is needed (D1);
    - what `J-approval.md` must contain (S4).

    All of these are now in the drill's contract and task files (`CONTRACT.md`, `J-live.md`, `V-rollback.md`); neither the helper nor the spec carries them. *Suggested action:* add them to the spec's live-task and rollback guidance, and consider recording on the live attempt whether a dispatch happened.
12. **Helper output.** *Not in the site records.* `python3 scripts/agent-task.py <id> --all | head -1` prints a `BrokenPipeError` traceback; this reproduces on Workflow's own example workflows. *Suggested action:* handle `BrokenPipeError` in the helper's output path.


Follow-up, in the next change after Pilot 5:

- **Finding 1:** `docs/ADOPTING.md`.
  - It lists the files to copy and the files not to copy.
  - It covers provenance in `ADOPTION.md`, writing `AGENTS.md`, local threat models, the order adopt → plan → compile, repository creation by the owner, and Pages-style targets.
  - It gives a repository gate template. The test suite runs the template against a correct adoption and against drift, missing, duplicate, malformed and extra rows, and workflow directories without a valid manifest.
  - README's Quick start points to the guide; it no longer tells adopters to run Workflow's own gate, and compiles a workflow only after plan approval.
- **Finding 2:** `agent-work/COORDINATOR.md` "Approval records" defines what an approval record states, and says a chat approval's record is the coordinator's own account. `agent-work/EVIDENCE-MANIFEST.md` points `approvalReference` at it.
- **Findings 4 and 5:** `agent-work/COORDINATOR.md` "Review/repair loop" requires resetting the repair task to `pending` for each further round, and recording the reviewer's observed model in every round.
- **Findings 9 and 10:** `agent-work/COORDINATOR.md` "Commands that move refs".
  - Gates must exit before the action.
  - A push names an asserted literal SHA.
  - No `grep -q` at the end of a pipeline under `pipefail`. A test runs the documented `grep -c` form 50 times against a 400-commit history.
  - Ancestry proofs need a non-shallow clone.
- **Finding 12:** the helper exits quietly with status 1 when its reader closes the pipe early, and a test covers it.
- **Findings 3 and 8** are covered in `docs/ADOPTING.md`.
- **Left for the next change:** finding 6 for the threat-model document (`docs/ADOPTING.md` section 4 states the stopping rule for adopters), finding 7, and finding 11, the helper and spec carrying the drill's dispatch and no-rollback rules.

The change after that closes Pilot 5's remaining findings:

- **Finding 6:** `docs/THREAT-MODEL.md` "How reviews use this" gains a guard-validator rule. A finding that needs deliberately crafted content to slip past a project's content guard is out of scope and recorded in the PR description. A guard that misses an ordinary way of writing the forbidden content, including copy-paste artifacts, is fixed. The rule does not cover the helper's evidence parsing. This is an owner scope decision; the owner's go-ahead to merge that change is the approval.
- **Finding 7:** `agent-work/WORKFLOW-SPEC.md` says the approved plan governs. A task file may make a check stricter, or swap in an equal or stronger proof, recorded as a dated plan clarification, checked by the next independent review and listed in the next owner preview. Weakening a check, widening scope or changing a live batch needs a revised plan and fresh approval.
- **Finding 11:** `agent-work/WORKFLOW-SPEC.md` "Failed live attempts and drills" covers the drill's contract rules:
  - a failed pre-dispatch recheck dispatches nothing and leaves the live task `in_progress`;
  - a dispatch that errors, or whose run never appears, is never repeated;
  - a failed attempt records `liveStateChanged`.

  The helper keeps a task that requires the live task `failed` from being ready while the latest live-attempt record says `liveStateChanged: false`, and its task view says no rollback is needed. A test covers explicit false against true, null, absent and wrong-typed values, and a later attempt.

## Pilot 6: release v0.1.0-alpha.13 with the post-Pilot 5 rules

Goal: publish `v0.1.0-alpha.13`, packaging PRs #15–#21, through the full deployment graph, and use the rules merged after Pilot 5 live for the first time. The full records are in `agent-work/release-alpha13/`.

What happened:

- **Plan.** An independent plan review took three rounds.
  - Round 1 found three High gaps. A cancel cannot beat a 15-second run's tag step. The rollback matrix had no draft rows. The proof that nothing went live was too thin.
  - Round 2 found two Medium gaps: no "nothing exists" row, and no end to the main freeze when nothing was published.
  - Round 3 approved. The owner approved revision 3.
- **Scaffold.** The scaffold review added eight task-file details (S1–S8), mainly a fuller pre-dispatch recheck.
- **Review.** The release review (B), on a different model from the builder, passed with five Low findings: one applied before readiness, four deferred.
- **Plan clarification.** One review suggestion made an acceptance check stricter: name both assets, require "not a draft", and check the title. It was recorded as a dated plan clarification before readiness, which is the PR #21 mechanism used live for the first time.
- **Readiness.** It passed. The ZIP was reproducible, alpha.12's published ZIP was reproduced from its commit, and there were no rulesets.
- **Approval.** The approval record follows `COORDINATOR.md` "Approval records": the question as asked, the owner's answer, the approved actions with input hashes, the conditions, and what it does not cover.
- **Live run.** The pre-dispatch recheck was read clean, then one dispatch was made on its own. Run 38508243210 took 16 seconds.
- **Acceptance PASS.** The downloaded ZIP and `.sha256` equal the frozen bytes. The unpacked ZIP equals `git archive` of the source. The tag is lightweight at the source. Every other tag and release is unchanged.
- **Helper labels.** The helper showed every label the plan expected: `GATED`, `PREVIEW`, `READY`, then `DONE` with K `READY`.

Findings, recorded for a later batch:

1. **README.** It says the live gate has three helper states; there are four (`DONE`). *Suggested action:* add `DONE`.
2. **`docs/RELEASING.md`.** Its "fails after creating the tag" paragraph does not mention that a draft release may exist. *Suggested action:* say to check the authenticated release list for a draft.
3. **Helper gating.** The helper's live gate reads evidence only. A manifest `status.J = "failed"` with no failed live record still shows J `READY` or `PREVIEW`. It needs a coordinator to skip a required step, and no wrong source or approval is accepted. *Suggested action:* return `GATED` when the live task's manifest status is `failed`, with a test.
4. **`RESULT-TEMPLATE.md`.** Its live-attempt paragraph does not mention `liveStateChanged` or approval records. *Suggested action:* point to the spec and coordinator sections.
5. **Plan review.** The first plan revision relied on cancelling a run that would already have published. *Suggested action:* `docs/RELEASING.md` could state the run's timing and that a cancel will not beat the tag step.
6. **Release metadata.** The release's API `created_at` is the source commit's time, not the run's; `published_at` is the run's. Evidence should use `published_at`.

Rules exercised live for the first time, without trouble:

- approval records;
- a dated plan clarification;
- the full pre-dispatch recheck, read before a separate dispatch;
- the reviewer's observed model recorded every round.

The ref-move rules apply to landing these records, which happens after this entry is written.

Not exercised, because the run succeeded:

- the repair-round reset;
- the recheck-failure and dispatch-error paths;
- `liveStateChanged`;
- the rollback matrix.

## Pilot 7: first adopter upgrade, stopped after verified rollback

Goal: upgrade `saxton-network/site`'s vendored Workflow files to `v0.1.0-alpha.13` and put its existing v2 page live. The full [records](https://github.com/saxton-network/site/tree/a3aa6b47db3bca76ce314d07a0ddac35e4cc86df/agent-work/site-upgrade) are in `agent-work/site-upgrade/` in the site repository.

What happened:

- **Upgrade.** The release ZIP was verified against its digest and source commit. Five copied files changed and three stayed byte-identical; `ADOPTION.md` was updated. The page kept the owner's date choice, "Last updated 13 October 2026". v2 had already been briefly public during Pilot 5's drill, so this added no new exposure.
- **Review and clarification.** Independent plan, scaffold and implementation reviews passed (the plan after a second round). A dated plan clarification corrected ambiguity 7: the copied threat model still references `docs/PILOT-HISTORY.md`; the adoption guide now explains that this points back to Workflow. It is answered, not removed. Other ambiguities remain partly answered or unanswered.
- **Readiness and approval.** The reviewed source was promoted to `main`, readiness passed and the batch was frozen. After the plain-language preview, the owner approved one v2 dispatch and one conditional rollback, and confirmed availability if rollback failed. The approval record bound both input-file hashes to the source and fingerprint.
- **Handover.** The coordinator changed between readiness and the live attempt: the owner moved the remaining steps to an agent from another vendor, working from a written handoff. The new coordinator showed the preview again before asking the question. The site records do not describe the handover; this account comes from the outgoing coordinator and the owner.
- **Live attempt.** The pre-dispatch recheck was read clean, then one dispatch ran. Run 38513237296 reported success with the expected head and name, but the coordinator's command-line client got `Forbidden` after a redirect when it requested the deployment log that acceptance check 1 requires. Acceptance stopped at check 1; the v2 live-byte check was not attempted. The publishing step had succeeded and a new Pages deployment existed, so `liveStateChanged` was `true`.
- **Rollback.** The owner was told promptly. After the first run finished and the rollback recheck passed, one dispatch restored v1 under the same approval. The coordinator's authenticated GitHub connection, a second client, could read the rollback log; its source and file hash matched v1, and `curl` returned HTTP 200 with exact v1 bytes. `main` was unchanged. End state: **stopped after verified rollback**. J remains failed and K blocked; no retry is approved or planned.
- **The v2 run was correct.** A later read of run 38513237296's job log shows `DEPLOY HEAD=95914a54336983fc48e286b8e16cb6780076d2f2` and `DEPLOY INDEX_SHA256=1f60283e1c442f0fd8e0015787c84febd2b37eabfe83bc9dbea54e7b345f7a35`, the frozen source and v2 hash. The failure was in reading the evidence, not in the deploy, and the rollback undid a correct deploy. J stays `failed`: evidence read after the failed check does not turn a failed attempt into a pass.
- **Records.** Independent review of the records PR (site PR #4) reported a site-rule violation: inherited commit messages carry the mandated `Co-Authored-By` trailers, which contain an email address. That conflicted with the site's adoption log (`ADOPTION.md`, ambiguity 17), which records the mandated identity and trailers as treated as owner-approved; `AGENTS.md` itself has no such exception, so the review's reading of the rule was literal. Neither the review nor the repair mentions the adoption log's record. The review was right that a task instruction also asked for reviewer-identity trailers, and the repair removed it. A separate repair role prepared a file snapshot of the records directly above the source on a new branch, preserving the original branch and history. The same reviewer passed it. With the owner's go-ahead (confirmed by the owner afterwards), [site PR #5](https://github.com/saxton-network/site/pull/5) landed by local `--no-ff` merge and an asserted-literal fast-forward push; the API showed it merged. PR #4 was closed as replaced. The replacement's commits were made with the new coordinator machine's configured git identity, which is personal. So the detour added a personal name and email address to the site's public history, the exposure the finding meant to prevent. Removing them would mean rewriting `main`, which the rules forbid without the owner's decision.

Findings and observations:

1. **Evidence access.** Acceptance named the evidence (the job log's `DEPLOY` lines) but not how to read it. One client could not, and another could. *Suggested action:* readiness proves that the coordinator can read a recent deploy job's log with the client it will use at acceptance, and the contract says whether a second read-only client may be used within the acceptance window. A read of the same evidence is not a retry of the live batch. This is settled before approval; it never turns a failed acceptance into a pass.
2. **Owner decisions must reach the reviewer.** An owner decision that interprets a repository rule must be written next to the rule (in `AGENTS.md`), not only in the adoption log. Otherwise a careful reviewer reports the rule as broken and the repair works against the owner's decision. *Suggested action:* `docs/ADOPTING.md` section 3 already asks adopters to say whether the trailers are exempt; make it say the answer is written in `AGENTS.md`, not only in the adoption log, and have the review briefing list the adoption log's decisions.
3. **Commit identity on a handover.** "Use the identity already configured" depends on the machine. A handover between coordinators changed the author identity on a public repository. *Suggested action:* an adopter's `AGENTS.md` says which identity to use without naming a person or address (for example, "the configured no-reply identity, never a personal one"), and a handoff requires checking `git config user.name` and `user.email` against it before the first commit.
4. **Adoption rows.** `docs/ADOPTING.md` shows three-column provenance rows; the site's existing hash gate requires four columns, including the source path. The upgrade kept that format and recorded the difference rather than changing the gate.

## Current maturity

The repository-only path has passed a controlled pilot. The deployment path has run six live workflows:

- Pilot 3: the success path, a GitHub prerelease;
- Pilot 4: a rollback drill, with an owner-performed release and tag deletion;
- Pilot 5: two in a first adopter project, the GitHub Pages success path and a Pages rollback drill (a coordinator redeploy of the previous commit);
- Pilot 6: the success path again, `v0.1.0-alpha.13`, with the post-Pilot 5 rules;
- Pilot 7: the first adopter upgrade, with failed acceptance and a verified coordinator rollback.

Pilot 5 is the first adoption by a newcomer in another repository. It exercised the fixes for Pilot 4's findings: J stayed `GATED` after the failed attempt, and records landed after a verified rollback. The tag-only and draft rollback rows, run cancellation, frozen-batch invalidation and a refused retry have still not been exercised live; for the retry boundary, only the helper's `GATED` label was observed.

The framework should still be treated as experimental: six live workflows are not broad coverage, and Pilot 5's adoption findings show that the docs assume knowledge a newcomer does not have.

The important pattern is deliberate: a pilot finding stops advancement, becomes a narrow validator/test repair, receives independent review, and only then is the same scenario retried.
