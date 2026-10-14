# AItism Task 001: provisional runtime foundation

Status: experimental, repository-only. The owner's Task 001 authorizes this
isolated implementation, not live execution or a change to Workflow v3 gates.
This design has not yet received independent architectural approval. No new
`agent-work/` workflow is compiled from an unreviewed plan.

## Repository assessment

Inspected baseline: `6b7016f3f2cd150469b71ce62ccd23e147d1f659`, clean
`experimental/features`, origin `https://github.com/saxton-network/workflow.git`.
The existing gate passed 67 tests before changes. Python 3.11+, unittest, shell
validation, and the standard library are the existing toolchain.

Reuse the specification's success-only dependencies, distinct source identities,
coordinator-owned state, explicit approvals, immutable evidence bindings, and
separate builder/reviewer identities. Keep `scripts/agent-task.py`, v2/v3
manifests, deployment fingerprints, release workflows, and all pilot records
unchanged. The helper is a validator, not an execution or permissions boundary.

Lifecycle identity, ownership, leases, resource budgets, provider sessions,
orphan reconciliation, and plan compilation are documented requirements, not
implemented capabilities at this baseline. This subsystem starts addressing
that debt without presenting itself as a conforming full lifecycle implementation.

Pilots 5–8 establish practical constraints: validate schemas rather than skipping
bad records; preserve failed acceptance despite later evidence; bind approvals
to exact inputs; recheck evidence access before live work; record actual review
identity rather than a requested model; do not assume cancellation prevents a
mutation; keep handover decisions and commit identity inspectable. Existing debt
includes unexercised live cancellation/rollback paths and the stale threat-model
cross-reference. Task 001 does not repair historical evidence or widen threat scope.

## Module boundaries

`aitism_runtime` is an opt-in Python package, runnable from the repository root.

| Module | Responsibility |
| --- | --- |
| `contracts` | Strict versioned JSON, canonical hashes, plan/state contracts |
| `planner` | Deterministic mock-only objective-to-proposal template |
| `store` | SQLite transactions, append-only hash-chained events, verified projection |
| `permissions` | Explicit local actor roles; agents cannot create authority |
| `providers` | Provider-neutral request/result interface, discovery, deterministic mock |
| `git_state` | Read-only exact branch/source observation, fail closed on mismatch |
| `runtime` | Approval, enrollment, scheduling, leases, result acceptance, recovery |
| `cli` | Local JSON Mission Control and bounded simulation commands |

The Workshop proposal includes requirements, assumptions, architecture, dependency
graph, roles, testing, estimates, risks, and checkpoints. It is an inspectable
template, not an AI planner. Creation persists a draft. A separate human operation
approves the exact plan hash with a nonempty reference and explicit simulation
scope. The demo labels its synthetic approval and review as simulation artifacts.
They cannot satisfy any Workflow v3 human or deployment gate.

## State machines and permissions

Workflow: `draft -> approved -> running -> completed`; approved/running may become
`failed`, and nonterminal workflows may become `cancelled`. A failed workflow
can resume only through explicit bounded retry. No live mutation kind is accepted.
Task: `pending -> running -> complete` (build/validation) or `passed` (review).
`running -> failed` on provider failure, invalid evidence, or stale lease.
Cancellation fences every running task. Failed attempts remain in history.
Agent: `idle -> running -> idle`, or `running -> stopped` after failure/cancel.
Explicit retry restores only the assigned actor and task, within the frozen limit.

Human registers actors and approves plans. Coordinator claims tasks, accepts
provider results, retries simulated failures, recovers expired leases, and cancels.
Assigned agents can heartbeat/checkpoint only their current fenced lease. Roles
are fixed at enrollment; no operation expands permissions. Parent lineage is
recorded, but delegation is denied in this slice: lineage grants no authority.
Reviews cover exact build-result hashes and source; reviewers must be different
actors from every builder they review. Completion requires validation of all
successful results and all mandatory reviews, not just a provider status string.

An enrolled actor's durable identity is the composite `(workflow_id, agent_id)`.
The same agent label in different workflows denotes separate actors, with
separate roles, assignments, and lifecycle state. Actor claim exclusion is
workflow-local: an enrolled actor must be idle before its assigned task is claimed.

Each claim reserves both an isolated simulation branch label and worktree label
across all workflows in one store, regardless of actor identity. These are
resources in a mock workspace; the runtime creates no Git worktrees and edits no
source files. Multiple store
files must not manage the same real resources. Actual filesystem isolation and
worktree provisioning are prerequisites for future execution, not claims here.

## Persistence and interruption

SQLite (foreign keys, full synchronous durability) serializes writers with
`BEGIN IMMEDIATE`. A transition atomically writes an event with the complete
versioned state checkpoint and updates its projection. SQL triggers prohibit
event update/delete. Sequence, predecessor hash, event hash, checkpoint contract,
and projection equality are verified before reads and writes. Corruption blocks
processing; it is never silently repaired or treated as an empty workflow.
Hash chains detect accidental damage; they do not resist a malicious database owner.

Claims commit before provider calls. Calls run outside the database transaction.
Results carry a lease fencing token, attempt identity, plan hash, source SHA,
provider/model, artifact checksum, review subject, and usage. Acceptance rechecks
the live lease and Git identity. Concurrent claims cannot acquire the same actor
within a workflow or the same branch/worktree label anywhere in the store. Separate
actors with the same label in different workflows may hold leases concurrently
when their resource labels differ. A duplicate completion with the same result is
a no-op; conflicting or old completions are rejected. Lost responses leave running leases; expired
leases become inspectable failed attempts through explicit recovery. Recovery
does not dispatch. Explicit retry allocates a new attempt and fencing token.
Only the deterministic mock can be dispatched in Task 001, so retries cannot
repeat external mutations. Checkpoints are hash-bound to task/attempt/lease and
are inspected before recovery. There are no external processes to reap.

## Provider bus and Mission Control

Adapters declare provider/model identity, capabilities, availability, and timeout
support, and accept a normalized request. Results expose nullable token/cost
telemetry; unavailable telemetry stays null. The mock reports measured synthetic
usage and zero simulated cost. A frozen token ceiling and attempt limit bound
mock execution. Providers cannot return permissions, tasks, or shell instructions
for the runtime to execute. An adapter's timeout contract must be enforced by its
backend; this synchronous mock cannot hang. External providers, asynchronous
cancellation, quota reservations, and safe cross-provider handoff are future work.

The CLI exposes proposal, creation, approval, enrollment, inspect, journal,
advance, recover, retry, cancel, and demo. JSON inspection includes task graph,
actors, approvals, attempts, evidence, usage, leases, failure reasons, and history.
A future self-hosted UI must consume the same read model, use authenticated actor
sessions, show approval previews, and never infer authority from display state.

## Trust boundaries and adversarial strategy

See [runtime threat notes](TASK-001-THREATS.md). Test faults include process loss
after claim, expired leases and heartbeats, invalid/unknown evidence, duplicate
ownership, unauthorized delegation, provider errors/unavailability/timeouts,
checkpoint corruption, foreign approval hashes, Git mismatch/unknown Git state,
duplicate completion, competing processes, and cancellation before late results.
Assertions check blocked successors, unchanged journals on rejected operations,
preserved failures, and absence of dispatch. An error message alone is insufficient.

## Migration and roadmap

Runtime schema version 1 is separate from Workflow manifest versions 2 and 3.
Published JSON Schema patterns require whole-string matches, just as the runtime
validator does. `^` anchors the start; `(?![\s\S])` requires the strict end,
including rejection of trailing newlines, using ECMAScript-compatible syntax.
There is no automatic importer, export of trusted v3 evidence, migration of pilot
files, or deployer. Never use simulation results as repository validation evidence.
Do not copy the runtime as part of the existing adoption file list. SQLite format
upgrades will require explicit version checks and evidence-preserving migration.

Next tasks, each separately scoped and reviewed:

1. Review this foundation and freeze compatibility fixtures and plan-review rules.
2. Add authenticated actors, policy-backed delegation, quota reservations, and
   cross-store resource ownership before introducing actual workers.
3. Add isolated worktree provisioning, confined tools, process reconciliation,
   checkpoint resume, and independently reviewed manifest conversion.
4. Add one read-only real-provider adapter with credentials outside the repository;
   prove timeouts, telemetry, cancellation, and safe handoff before mutation tools.
5. Add local Mission Control UI, evidence-backed institutional memory, and repeated
   fault-injection campaigns. Live deployment remains a separate approved project.
