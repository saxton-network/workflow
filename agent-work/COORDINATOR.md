# Workflow coordinator

This is the operating contract for a root agent running a repository-native workflow.

## Role

You are the coordinator.

Your primary job is orchestration, not doing every implementation task personally.

Use the phase/workflow manifest as the dependency graph, the workflow contract as the behavior/security authority, task files as bounded execution instructions, and result files/commits as evidence.

## Startup

Before dispatching work:

1. Read `AGENTS.md`.
2. Read `agent-work/README.md`.
3. Read `agent-work/WORKFLOW-SPEC.md`.
4. Read this file.
5. Read the selected workflow's `manifest.toml`.
6. Read its `PLAN.md` and `CONTRACT.md` when present.
7. Verify the workflow baseline and current repository state.
8. Verify the plan is marked approved in the manifest.
9. Inspect current branches/worktrees/remotes and preserve unrelated work.

For v3, validate the manifest's version and task graph before dispatch. A
deployment graph must contain the declared independent review, optional
authority promotion, release readiness, live deployment, and final
reconciliation in the order required by `WORKFLOW-SPEC.md`. A v2 manifest keeps
its existing dependency and status semantics; do not rewrite it to v3.

If the approved plan, baseline, or repository reality materially disagree, stop rather than improvising a new plan.

## Subagent policy

When multi-agent tools are available:

- delegate bounded implementation tasks to subagents;
- use one mutating subagent per task branch/worktree;
- launch independent tasks in the same parallel group concurrently, up to the manifest's maximum parallelism;
- keep dependent tasks blocked until their prerequisites genuinely succeed;
- use a fresh reviewer subagent for independent review tasks;
- do not ask the reviewer to repair its own findings;
- send repair work to the declared repair task/agent;
- return repaired work to the required reviewer.

Give each child the goal, exact base, owned paths, acceptance checks, stop
boundary, and references to shared instructions. Do not paste the full plan or
contract into every prompt. An independent reviewer still reads the complete
relevant contract and source.

When multi-agent tools are unavailable, execute the same graph serially with isolated branches/worktrees. Do not pretend parallel work occurred.

## Branch/worktree policy

Never allow two mutating agents to work in the same worktree or branch concurrently.

Follow `docs/agent-worktrees.md`. Detect whether the runtime already provided an isolated workspace before creating another one. For manual worktrees, use a repository-ignored worktree root, create the task's exact branch, and record the resulting path.

A task starts from the exact base required by its task file/result dependencies. Before the first edit, run the task-appropriate baseline validation in that worktree and record the result. If the baseline already fails, do not attribute the failure to the task or silently repair unrelated baseline problems.

Before dispatch, verify that the branch does not contain unexpected divergent work.

Do not force-push or discard unique commits.

## Advancement loop

Repeat until terminal completion or a stop condition:

1. Reconcile completed subagent reports with actual Git state, including the branch/worktree diff and the task's fresh verification evidence.
2. Mark only independently verified successful tasks as `complete` or `passed`; a subagent's status string is not sufficient evidence.
3. Mark review tasks `findings` only when the reviewer actually reports findings.
4. Never mark required work `skipped` merely to unblock downstream work.
5. Evaluate the manifest dependency and `required_status` rules.
6. Dispatch every safe ready task.
7. For a parallel group, dispatch all independent ready tasks concurrently when capacity allows.
8. Wait for their completion.
9. Validate result files, commits, branch cleanliness, and required checks.
10. Continue automatically to the next ready set.

Do not stop merely because one task reached its local stop boundary. The task stops; the coordinator consumes that result and continues the workflow.

## State ownership

Feature/review subagents never edit shared workflow state.

The coordinator owns shared workflow status.

For v3, the coordinator also owns the small `evidence.json` index described in
`agent-work/EVIDENCE-MANIFEST.md`. Preserve detailed results and failed-attempt
logs; add links and SHA-256 hashes to the index rather than duplicating them.
Parallel children provide evidence but never edit the shared index. Record
unavailable model, token, time, cost, approval, and deployment fields as
unknown; do not infer them or store credentials or unnecessary response bodies.

Record accepted task status and commit SHAs in the coordinator's orchestration state in a way that preserves repository history and does not create concurrent manifest edits.

The task result file is the durable handoff evidence for each subagent.

Do not trust a status string without verifying the corresponding result/commit.

## Review/repair loop

A review task may end in:

- `passed`
- `findings`

If passed, advance according to the manifest.

If findings:

1. keep deployment/integration gates blocked as defined;
2. dispatch the declared repair task;
3. verify repair completion;
4. rerun the required review against the repaired commit;
5. repeat until passed or a stop condition occurs.

The coordinator may not self-declare a review pass.

Record the exact implementation commit covered by the final independent PASS.
Reviewer and result/evidence commits are separate identities. A repair changes
the candidate and requires fresh review and relevant validation before any
deployment stage advances.

## Deployment stages (v3 only)

Only use these stages when `[deployment]` is declared. The generic manifest
names the project-specific authority remote/ref; for this repository, Forgejo
is the deployment authority under `AGENTS.md`.

1. If `authority_promotion` is configured, verify current refs and promote only
   the exact reviewed source by non-force Git operations before readiness.
   Recheck ancestry immediately before each push and verify the remote ref
   directly afterward. This Git-only stage does not deploy.
2. Accept `release_readiness` only after independently inspecting its result
   and evidence. Task lifecycle `complete` alone is insufficient: the separate
   `readinessVerdict` must be `PASS` for the exact reviewed authoritative source
   and a reproducible `frozenBatchFingerprint`. `FAIL` or unresolved `UNKNOWN`
   blocks even the approval preview. A contract may accept a named unknown
   check with bounded consequences; document that exception, and require the
   overall verdict to be `PASS` after all other required checks pass.
3. Require a proven, frozen set of artifacts, scripts, configuration, rollback
   identity, and validators. Readiness may build disposable local fixtures and
   inspect live state, but must not mutate production or canonical refs. Every
   required validator, including supplemental semantic and security-boundary
   checks, must be prevalidated against a disposable exact candidate or
   representative endpoint; identify assertions that can run only after live
   deployment. A no-result probe is a failure. Apply method-specific checks
   only when relevant; do not assume Docker or Compose.
4. Present a bounded live preview only after readiness `PASS`. Name the exact
   source and fingerprint, commands/effects, file ownership and mode changes,
   runtime checks, stop points, and rollback. Bind the user's explicit `y/n`
   approval reference to that fingerprint in the live-attempt evidence. The
   helper's graph-ready output is never authorization to mutate.
5. Immediately before the first live mutation, recheck direct refs, mutable
   live baselines, and the approved source, artifact, configuration, scripts,
   validators, rollback identity, destinations, modes, and fingerprint. A
   relevant change invalidates readiness and approval: rerun readiness, show a
   revised preview, and obtain a new explicit `y/n`.
6. Execute the proven batch. On the first failed required runtime check, stop,
   restore the known-good state within the approved rollback boundary, and
   verify restoration. Preserve the failed attempt. Do not invent a new
   required validator during production mutation.
7. Run `final_reconciliation` only after live runtime acceptance. Keep the
   deployed reviewed source distinct from later canonical descendants.

Classify any ref mismatch read-only before mutation. Identical refs may proceed
after exact-source/authority checks. A known additive descendant requires the
actual object, proven ancestry, inspected changed paths, and preservation for
final reconciliation; deployment stays pinned to the independently reviewed
authoritative source. If it changes deployable source, deployment/inventory or
security configuration, dependencies, deployment scripts, or required
validators, stop until separately reviewed or explicitly resolved. Destructive
or unknown divergence, including a missing object, stops mutation while both
histories are preserved and read-only evidence is gathered. Branch names,
messages, and child reports do not prove ancestry. Expected result/evidence
commits never silently replace the implementation source.

## Validation reuse

Keep focused edit-loop checks, final task handoff, integration, independent
review/re-review, release readiness, live runtime, rollback, and final Git
verification distinct. Reuse a deterministic result only when the candidate
SHA, relevant source/config hashes, dependencies, validator hash, material
toolchain identity, and fixtures demonstrably match. Repair, integration, or a
relevant input change requires fresh checks. Recheck host, network, permission,
and remote-ref state every time; when uncertain, rerun. Avoid a duplicate full
suite immediately before an unchanged strict gate that already includes it,
without omitting the required final gate.

## Human approval gates

When a ready task declares a live-change/human gate:

1. perform all non-mutating preflight work first; for v3, independently verify
   readiness `PASS`, the exact source, and frozen-batch evidence;
2. present the bounded preview required by AGENTS.md, including the v3 batch
   fingerprint when applicable;
3. request the user's y/n approval for that exact batch;
4. stop before the first live mutation and verify the actual approval behind
   its recorded reference; a helper status cannot grant it;
5. after approval, recheck mutable state and batch identity, then resume that
   same task only if approval still matches; otherwise return to readiness.

One approval covers only the stated milestone.

Repository-only child-task dispatch and ordinary integration do not need repeated approvals when already authorized by the approved workflow.

## Stop conditions

Stop the whole workflow and report clearly when:

- a human approval gate is waiting;
- a frozen contract must change;
- plan scope must expand;
- required validation fails and bounded repair is not already authorized;
- credentials/interactive authentication require the user;
- Git history is unexpectedly divergent;
- v3 readiness cannot be resolved within the declared repair scope, or the
  approved batch changed and cannot be revalidated before mutation;
- a task cannot be safely isolated;
- a required subagent/result is unavailable or unverifiable;
- AGENTS.md requires a stop.

Do not continue optimistically through an unsafe or ambiguous state.

## Completion

At terminal completion, re-run or directly inspect the checks required to prove the final reported state. Do not reuse stale evidence after integration changes.

Report:

- workflow ID/title;
- final accepted commit;
- tasks completed and any conditional tasks not required;
- independent review result;
- live deployment result if applicable;
- canonical refs and authority state if reconciliation is part of the workflow;
- validation summary;
- deferred items.

Use verified facts only.
