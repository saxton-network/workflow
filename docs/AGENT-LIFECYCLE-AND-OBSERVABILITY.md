# Agent Lifecycle and Observability

## Status

This document defines design requirements for Workflow-managed execution actors and the resources they create. It is intended to guide implementation and future compatibility work. Where current behavior differs from these requirements, the difference should be treated as implementation debt rather than an implicit change to these principles.

## Core principle

Workflow should permit substantial agent autonomy without requiring the operator to surrender observability or control.

A Workflow-managed agent must not perform independently tasked work as an invisible execution actor. Agent identity, delegation, resource ownership, execution state, and resource consumption must remain attributable and inspectable throughout the agent lifecycle.

The system should preserve four operator-facing invariants:

1. **No invisible agents.**
2. **No invisible work.**
3. **No invisible resource consumption.**
4. **No orphaned execution.**

These requirements apply regardless of model provider, agent implementation, user interface, or execution backend.

## Agent identity and lineage

Every independently tasked Workflow-managed agent must have a durable identity.

At minimum, Workflow should be able to determine:

- the agent's unique identity;
- the task or scope assigned to it;
- the actor that created or delegated to it;
- its parent agent, when applicable;
- its root Workflow run or operator-owned execution;
- its current lifecycle state;
- its assigned branch, worktree, lease, or equivalent isolation boundary;
- its effective permissions and tool access;
- its model/provider or execution implementation where relevant;
- its creation time and last known activity;
- its accumulated measurable resource usage.

Delegation must create an explicit parent-child relationship. An agent tree must be reconstructable from durable Workflow state rather than inferred from transient process behavior.

Provider-internal implementation details that do not constitute independently tasked execution actors are outside this requirement. If an execution unit can independently receive work, consume resources, invoke tools, mutate state, delegate further work, or outlive the initiating call, Workflow should treat it as an identifiable actor.

## Operator observability

The operator must be able to inspect active Workflow-managed agents and understand what each is doing.

An observable agent state should expose enough information to answer:

- Why does this agent exist?
- What task is it performing?
- Who or what created it?
- What permissions does it currently have?
- What repository or other resources can it modify?
- What work has it produced?
- What resources has it consumed?
- Has it created child agents?
- Is it progressing, blocked, retrying, waiting, or failing?
- How can its execution be paused or terminated?

Observability should not depend on access to a provider-specific hidden interface. Provider adapters should surface lifecycle and usage information through common Workflow concepts wherever the provider makes that information available.

## Resource and spend visibility

Workflow should attribute measurable resource consumption to the execution actor and task that caused it.

Depending on provider capabilities, this may include:

- input and output tokens;
- model/API charges or estimated charges;
- wall-clock execution time;
- compute time;
- tool invocations;
- network or external-service usage;
- retry counts;
- child-agent creation;
- other quota consumption.

Missing provider telemetry must be represented as unknown or unavailable rather than silently treated as zero.

Usage should be aggregatable from an agent to its parent task and root Workflow run so an operator can determine where resources were consumed.

## Bounded delegation

Delegation must be explicit and bounded.

Workflow should support policy limits such as:

- maximum child-agent count;
- maximum delegation depth;
- maximum retries;
- maximum runtime;
- token, cost, or provider-quota budgets where measurable;
- allowed agent/provider classes;
- allowed capabilities and tools;
- allowed repository paths or other mutation scopes.

An agent must not be able to evade a limit by delegating the same work to another actor.

Budget and delegation enforcement belongs to the orchestration layer, not solely to the agent being constrained.

## Ownership invariant

Every Workflow-managed execution actor and managed resource must have an identifiable owner and lifecycle.

Managed resources may include:

- agents and child agents;
- operating-system processes;
- containers;
- branches and worktrees;
- locks and leases;
- temporary credentials;
- reservations;
- temporary files and directories;
- provider sessions;
- other resources whose continued existence can mutate state, consume resources, or block progress.

Ownership must be durable enough for Workflow to reconcile resources after interruption, restart, partial failure, or loss of a parent actor.

Unowned execution must not continue merely because the underlying process remains alive.

## Orphan detection

An orphan exists when a Workflow-managed actor or resource no longer has a valid, traceable owner according to Workflow's durable state and lifecycle rules.

Examples include:

- a child agent continuing after its parent has terminated unexpectedly;
- a process or container surviving after the agent responsible for it has ended;
- a worktree or lock whose owning task no longer exists;
- an execution session continuing after the controlling Workflow run has been terminated;
- a delegated agent whose parent relationship cannot be reconciled after recovery.

Workflow should actively reconcile durable state with live execution so that orphaned resources can be detected rather than relying exclusively on graceful shutdown paths.

## Fail-closed orphan handling

Orphaned execution should fail closed.

When an executing actor is determined to be orphaned, Workflow should, as applicable:

1. prevent new mutations and delegation;
2. revoke or suspend effective permissions;
3. preserve recoverable state, work product, and evidence;
4. record the orphan event and relevant lineage in the audit record;
5. determine whether an explicitly authorized re-parenting or recovery path exists;
6. if no authorized recovery path exists, terminate the orphaned actor;
7. reconcile and clean up owned resources;
8. report the disposition to the operator.

Termination should be the default disposition for unowned execution. Re-parenting should be an explicit, policy-governed recovery action rather than an assumption that an orphan may continue.

Cleanup must not destroy evidence required to understand the failure or recover legitimate work.

## Recovery and reconciliation

Workflow must assume that graceful shutdown will sometimes fail.

On startup and after relevant control-plane failures, Workflow should be able to reconcile:

- durable agent records against live execution;
- parent-child lineage;
- task ownership;
- branches and worktrees;
- locks and leases;
- temporary credentials and sessions;
- containers and processes;
- other tracked resources.

Reconciliation outcomes should be deterministic and auditable. Ambiguous ownership should not silently authorize continued execution.

## Audit requirements

Lifecycle events should be durably recorded when practical. Relevant events include:

- agent creation;
- delegation and parent assignment;
- capability or permission changes;
- budget changes and threshold events;
- retries and repeated failure;
- pause, resume, cancellation, and termination;
- orphan detection;
- re-parenting or recovery;
- cleanup and reconciliation results;
- resource-usage updates where available.

The audit record should make it possible to reconstruct the significant lifecycle decisions of a Workflow run after the fact.

## Provider neutrality

These requirements are provider-neutral.

Workflow should express identity, ownership, delegation, lifecycle, permissions, usage, and termination through common orchestration concepts rather than embedding assumptions about a specific model vendor.

Provider adapters may expose different capabilities and telemetry. Those differences should be represented explicitly as capabilities or unavailable information, not hidden behind provider-specific behavior.

A future provider or third-party agent implementation should be able to satisfy the same lifecycle contract without receiving privileged treatment from Workflow core.

## Compatibility direction

As Workflow's public agent contract matures, lifecycle and observability behavior should become part of compatibility testing.

A conforming implementation should not create independently tasked, Workflow-managed execution actors that are absent from Workflow's observable lifecycle model.

Compatibility tests should eventually cover at least:

- durable agent identity;
- explicit lineage;
- bounded delegation;
- usage attribution where telemetry exists;
- cancellation and termination;
- orphan detection;
- fail-closed orphan handling;
- restart reconciliation;
- evidence-preserving cleanup.

## Design summary

Workflow's desired execution model is **agentic autonomy without operator opacity**.

Agents may work independently, delegate, parallelize, and use different providers, but the operator remains the ultimate authority over execution performed on their behalf.

Every independently tasked actor should be identifiable. Every managed resource should have an owner. Every delegation should have lineage. Every measurable cost should be attributable. Every orphan should reach a deterministic disposition.

Autonomy is a capability. Observability and control are invariants.
