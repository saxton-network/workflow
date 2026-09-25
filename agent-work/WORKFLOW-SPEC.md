# Workflow specification

This file defines the repository convention behind `/workflow`. Compilation is instruction-driven: the approved plan becomes task files and a manifest, then one coordinator runs the graph. `scripts/agent-task.py` is a read-only handoff and validation helper, not a compiler or deployment tool.

## Authorization and durable files

The lifecycle begins with a plan, independent plan review, and user approval. Only then may `/workflow` capture the approved plan, freeze a contract where needed, compile tasks, validate and independently review the scaffold, and run it. Repository implementation is within the approved plan. Live changes still require the explicit bounded `y/n` approval in `AGENTS.md`.

Each workflow lives under `agent-work/<workflow-id>/` with `PLAN.md`, `manifest.toml`, one task file per task, and `results/README.md`. Include `CONTRACT.md` when behavior, security, or data contracts need freezing. Compile the scaffold on an isolated branch, validate and independently review it, then run it. Use lettered task IDs when practical. Task files state prerequisites, exact base and branch, owned paths, required reading and validation, result evidence using `agent-work/RESULT-TEMPLATE.md` unless stricter, forbidden work, and a stop boundary. Use one branch/worktree per mutating agent. Prefer independent parallel tasks and put shared files in a foundation or integration task.

The coordinator owns shared status and advancement. Child agents stop at their task boundary. Builder and reviewer roles remain independent; findings go to a repair role and back to an independent re-review. Preserve failed attempts and their evidence.

## Version and task graph

New workflows may declare `workflow_version = 3`. Existing version 2 manifests retain their existing schema, task readiness, and status semantics; do not rewrite them to migrate. Reject absent, malformed, or unsupported versions rather than guessing. A v3 workflow retains the existing `[workflow]`, `[status]`, and `[tasks.<id>]` structure, including `depends_on`, `required_status`, `conditional`, `rerun_after`, `human_gate`, and `parallel_group`. Every v3 task also declares one `kind`:

The base manifest still declares workflow ID/title, baseline commit, approved plan, optional contract, coordinator mode and file, auto-dispatch, intended maximum parallelism, task name/file/branch, dependency and status maps, conditional/rerun rules, and human-gate tasks. `[workflow].terminal_task` is a string naming one declared task. The coordinator validates these before dispatch and remains the only role that advances shared status.

`implementation`, `integration`, `independent_review`, `repair`, `authority_promotion`, `release_readiness`, `live_deployment`, `final_reconciliation`, or `other`.

Ordinary dependencies require task status `complete` or `passed`. `failed`, `blocked`, `findings`, `skipped`, and unknown statuses never satisfy an ordinary dependency. Exceptional transitions require an explicit `required_status`. Review `findings` may activate a conditional repair, but cannot satisfy a deployment gate. `rerun_after` makes re-review wait for repair. A final `passed` review must cover the current candidate after any repair.

The v3 schema does not assume a deployment. For a deployment workflow, add `[deployment]` with these task IDs:

```toml
workflow_version = 3

[workflow]
evidence_manifest = "agent-work/<workflow-id>/evidence.json"

[deployment]
implementation_tasks = ["G"] # integration tip or all tasks whose output must be reviewed
review_task = "H"
authority_task = "P" # omit when the reviewed source is already authoritative
authority_remote = "origin"
authority_ref = "refs/heads/main"
readiness_task = "R"
live_task = "J"
final_reconciliation_task = "K"
```

This is an illustrative fragment, not a complete manifest. The authority remote/ref are project-specific; no forge is hardcoded in the generic schema. Declare them when the project has a deployment authority, even when no promotion task is needed because the reviewed source is already authoritative. `implementation_tasks` is nonempty and names the implementation output that the independent reviewer must cover. If the reviewed integration task depends on the feature tasks, listing that integration task is sufficient. The coordinator records the exact reviewed implementation commit separately from any reviewer or result commit.

### Complete non-deployment example

A repository-only workflow can use an `integration` task as its terminal task for Git-only integration and reconciliation. This example uses implementation, independent review, conditional repair, and integration. Replace the workflow identity, baseline, plan path, and task-file paths when compiling a new workflow.

```toml
workflow_version = 3
phase = "nondeployment-example"
title = "Example repository-only change"
phase_baseline = "1111111111111111111111111111111111111111"
plan = "agent-work/nondeployment-example/PLAN.md"

[workflow]
mode = "coordinator"
plan_status = "approved"
coordinator = "agent-work/COORDINATOR.md"
auto_dispatch = true
max_parallel_subagents = 1
evidence_manifest = "agent-work/nondeployment-example/evidence.json"
terminal_task = "D"

[status]
A = "pending"
B = "blocked"
C = "conditional"
D = "blocked"

[tasks.A]
kind = "implementation"
name = "Implement the approved change"
file = "agent-work/nondeployment-example/A-implementation.md"
branch = "agent/nondeployment-example"
depends_on = []

[tasks.B]
kind = "independent_review"
name = "Review the implementation candidate"
file = "agent-work/nondeployment-example/B-review.md"
branch = "review/nondeployment-example"
depends_on = ["A"]
required_status = { A = "complete" }
rerun_after = "C"

[tasks.C]
kind = "repair"
name = "Address reported review findings"
file = "agent-work/nondeployment-example/C-repair.md"
branch = "fix/nondeployment-example"
depends_on = ["B"]
required_status = { B = "findings" }
conditional = "review_findings_exist"

[tasks.D]
kind = "integration"
name = "Integrate and reconcile the reviewed Git change"
file = "agent-work/nondeployment-example/D-integration.md"
branch = "integration/nondeployment-example"
depends_on = ["B"]
required_status = { B = "passed" }
```

Task B waits for the implementation to complete and must run again after C repairs findings. Task D waits for B to pass and owns the Git-only terminal work. This graph has no `[deployment]` table or deployment-specific task kinds.

The top-level `phase` is the workflow ID. A v3 manifest must name its evidence index exactly `agent-work/<phase>/evidence.json`, and the index's `workflowId` must equal that `phase`. A foreign index or alternate manifest path cannot satisfy a gate.

Static v3 validation must reject unknown task IDs, duplicate stage IDs, wrong stage kinds, cycles, and any path that could make `live_deployment` ready early. Require:

1. The review task is an `independent_review` and transitively depends on every `implementation_tasks` entry through success-only edges. Every upstream implementation/integration dependency feeding a listed output, and every edge from that output to review, must require ordinary `complete`/`passed`; an exceptional `required_status` such as `failed`, `findings`, or `skipped` cannot turn failed implementation into a review pass. Its final verdict must be `passed` for the current candidate; `findings` triggers repair and fresh re-review.
2. If configured, `authority_promotion` depends on review `passed`. It performs Git-only, non-force promotion of the exact reviewed source to the declared deployment authority; it does not deploy. Omit this task when no promotion is needed, while retaining an applicable authority remote/ref declaration for readiness checks.
3. `release_readiness` depends on review `passed` and on completed authority promotion when configured. It cannot change production or canonical refs.
4. `live_deployment` depends directly on completed readiness, declares `human_gate = "live-change-approval"`, and appears in `[workflow].human_gate_tasks`. A task status of `complete` for readiness is insufficient without its separate readiness verdict and frozen-batch evidence described below.
5. `final_reconciliation` depends on successful live deployment, including its required runtime acceptance. It verifies or advances remaining refs only by reviewed, non-force operations. It never supplies deployment authority retroactively.

`depends_on` and `required_status` must agree with these edges. For every required stage edge above, require only `complete`/`passed`, with `passed` specifically required for independent review. An exceptional status cannot bypass implementation completion, review, readiness, or live success. Deployment-specific kinds cannot appear outside a complete `[deployment]` declaration. Non-deployment workflows omit `[deployment]` and deployment kinds cleanly. A v3 workflow may use optional stages only when the approved plan needs them.

## Release readiness and frozen live batch

Readiness is read-only with respect to production and canonical Git refs. It may inspect live state and build disposable local artifacts or fixtures. The task lifecycle status remains `pending`/`complete`/`failed` as applicable; its independent `readinessVerdict` is `PASS`, `FAIL`, or `UNKNOWN` in coordinator-owned evidence. `FAIL` and unresolved `UNKNOWN` block the approval preview and live mutation. A contract may explicitly accept a named unknown check with bounded consequences; record that exception and its reason, then mark the *overall* verdict `PASS` only if every remaining required check passes. Never turn unknown into a general successful task status.

Select checks for the deployment method. Where applicable, readiness proves the exact reviewed source SHA and authority ref/direct remote values; artifact SHA-256 and extracted bytes; executable shebang/line-ending fidelity; Git, staged, live, and intended owner/mode values; exact live paths; rendered configuration; rollback artifact availability and provenance; validator hashes and client/protocol compatibility; semantic assertions and HTTP/TLS/security boundary probes; exposure, credential, and unrelated-service baselines; and the exact proposed live batch, stop points, runtime checks, and rollback actions. Before freezing, execute **every** required validator, including supplemental semantic and boundary probes, against a disposable exact candidate or representative endpoint. Assert expected response/status values and, for SDK-based clients, preservation of required authentication, Host, and Origin headers through wrappers. A probe that yields no interpretable result fails readiness; live-only assertions must be identified explicitly and still run after deployment. Do not impose Docker or Compose checks on projects that do not use them. Any intended `chmod`/`chown` belongs in the bounded live preview; never normalize permissions blindly.

Compute `frozenBatchFingerprint` as lowercase SHA-256 hex of a canonical UTF-8 JSON record: sorted object keys, no insignificant whitespace, path-entry arrays sorted by `path`, and deployment-target arrays sorted by `destination`. Include at least `deploymentSourceSha`, deployable artifact SHA-256, relevant deployment configuration path/hash pairs, validator/harness path/hash pairs, rollback artifact identity/provenance, every reviewed script installed by the batch with its path/hash, and a nonempty `deploymentTargets` array. Each deployment target records a nonempty `destination` and an explicit `mode`; use `null` only when mode is genuinely not applicable to that deployment method. Record `owner` and `group` when those properties are applicable. These target fields are part of the frozen batch and therefore changes to destination, mode, ownership, or grouping invalidate the fingerprint and any approval bound to it. Use exact bytes, not branch names or mutable tags alone. The readiness result records the record, its hash, the validator set, and evidence links. The approval preview names that fingerprint and the exact commands/effects it authorizes.

Static graph eligibility is **not** authorization to mutate. The read-only helper's v3 `--ready`, `--all`, and task handoff output must label a live task `GATED`, not dispatchable, unless it verifies coordinator-owned evidence for readiness `PASS`, the exact source and frozen fingerprint, and an approval reference bound to that same fingerprint. The source must equal the latest completed candidate-producing record before the final review PASS: a declared implementation/integration output, or the declared repair output after findings. A candidate-producing record after that PASS invalidates the gate. With PASS/fingerprint but no approval, it may report `eligible for approval preview`, never `ready for live mutation`; an invalid, missing, stale, or mismatched record remains `GATED`. Before the approval preview, the coordinator independently confirms readiness `PASS` and the recorded fingerprint. It verifies the actual human approval behind the reference; the helper cannot grant approval. Even a helper `READY` label is only a handoff, not authorization to mutate. Immediately before the first live mutation, the task rechecks direct refs, current live baselines, and that the approved artifact, source, config, scripts, validators, rollback identity, and fingerprint still match. Mutable state checks are rerun, never borrowed from old evidence. A relevant source, artifact, validator, config, destination, or mode change invalidates readiness and approval: run fresh readiness, present a revised bounded preview, and obtain a new explicit `y/n`. Live deployment executes the proven batch and stops at the first failed required check; restore and verify known-good state within the approved rollback boundary. Do not invent a new required validator while production is changed.

## Git divergence and source identity

Use direct ref/object inspection immediately before promotion, deployment, and final reconciliation. A result or evidence commit is not an implementation or deployment-source commit. Never infer ancestry from branch names, commit messages, or a child report.

| Classification | Required action |
| --- | --- |
| Identical refs | Confirm the exact reviewed source and configured authority state, then proceed within the declared stage. |
| Known additive descendant | Obtain the object, prove ancestry, inspect changed paths, preserve the descendant, and keep deployment pinned to the independently reviewed authoritative source. Defer the descendant to final reconciliation only when it does not alter reviewed deployment inputs. |
| Destructive divergence | Stop mutation, preserve both histories, and require separately reviewed reconciliation. |
| Unknown divergence or missing object | Stop mutation; gather read-only remote/object evidence and classify before proceeding. |
| Expected result/evidence commit | Track separately. Never silently substitute it for the reviewed source. |

Deployment inputs include deployable service source, deployment/Compose configuration, consumed inventory, authentication/security settings, dependencies, deployment scripts, and required validator code. An additive descendant touching one of those categories blocks deployment until separately reviewed or explicitly resolved. Every non-force push requires fresh fetch/ancestry checks and direct post-push ref verification. For this repository, `AGENTS.md` defines deployment authority; the generic schema only names a configured remote/ref.

## Validation and evidence

Use distinct layers: (1) focused edit-loop checks, (2) fresh final task handoff, (3) fresh integration on the merged tree, (4) independent review and re-review, (5) release readiness, (6) live deployment/runtime acceptance, (7) rollback verification after a failure, and (8) final reconciliation ref verification. Repository checks do not prove live behavior. A task involving bounded/paginated upstream data should test adversarial ordering and server-side filtering before pagination when those semantics matter.

Reuse deterministic validation only when its candidate SHA, relevant source/config hashes, dependency state, validator hash, material toolchain identity, and fixtures are demonstrably unchanged. Integration, repair, or relevant configuration changes require fresh validation. When uncertain, rerun. Host, network, remote-ref, permission, and other mutable-state checks are never reused as current evidence. Do not repeat a direct full suite immediately before an unchanged strict gate that already includes it, but retain each required final gate.

The coordinator owns a compact machine-readable evidence index defined in `agent-work/EVIDENCE-MANIFEST.md`. It complements detailed results and logs, including failures; parallel task agents never edit it. Link immutable evidence by path and SHA-256, record unavailable metrics as unknown, and keep credentials and unnecessary response bodies out. Child prompts carry goal, exact base, owned paths, checks, stop boundary, and shared-document references rather than pasted plan/contract prose. Independent reviewers still read the full relevant contract and source.

## Stop and completion rules

Stop for a human gate, changed approved plan/frozen contract, failed required validation beyond bounded repair, unavailable credentials requiring interactive authentication, unsafe Git divergence, unverifiable result, or an `AGENTS.md` safety rule. Never silently skip work, turn findings into a pass, weaken a security boundary, or treat a green repository gate as deployment proof.

A workflow completes only when its terminal task succeeds and fresh evidence proves accepted implementation, independent review, deployed/runtime state if any, and required canonical refs. Report the exact accepted/deployed source, canonical Git state, checks, preserved failures, and deferred work. An optional later efficiency audit may classify recommendations `NOW`, `NEXT`, or `WATCH`; it cannot change canonical workflow rules without a separately reviewed workflow-system revision.
