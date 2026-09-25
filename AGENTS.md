# Agent operating rules

This repository contains a reusable multi-agent workflow framework. Adopting repositories should extend this file with their own project-specific rules.

## Preserve work

- Inspect branch, remotes, worktrees, and git status before editing.
- Preserve concurrent work. Never reset, clean, force-checkout, or discard unrelated changes.
- Use one branch and isolated worktree per mutating agent unless an equivalent isolated workspace already exists.
- Never force-push to erase divergence or discard unique commits.

## Separate repository states

Keep these concepts distinct:

- **Working:** a change exists on a working or collaboration ref.
- **Authoritative:** the configured deployment-authority ref contains the accepted source.
- **Deployed:** that exact reviewed source was applied live and passed runtime acceptance.

Do not infer one state from another.

## Approval

Repository-only implementation may follow an approved plan without repeated approval prompts.

Before any live state mutation, require a bounded preview and explicit human approval for that exact batch. The preview should identify the source, effects, commands or script, exposure, verification, stop conditions, rollback, and retry boundary.

A helper status, evidence record, plan approval, or previous approval does not authorize a different live batch.

## Secrets

Never commit or place in evidence credentials, bearer tokens, private keys, runtime secret files, or raw secret-bearing response bodies. Use sanitized evidence references instead.

## Repository-native workflows

- Read agent-work/WORKFLOW-SPEC.md and agent-work/COORDINATOR.md.
- The coordinator owns shared workflow status and evidence.json.
- Child agents stop at their task boundary.
- Builders and independent reviewers remain separate roles.
- Findings go to a separate repair role and back to the same reviewer.
- Do not silently weaken a frozen contract or safety boundary.

## Deployment authority

An adopting repository must define its deployment authority. Workflow v3 records it in the deployment table as authority_remote and authority_ref.

Deployment must remain pinned to the exact independently reviewed authoritative source. A known additive descendant may wait for final reconciliation only after object, ancestry, and changed-path proof and only when protected deployment inputs are unchanged. Unknown or destructive divergence stops mutation.

## Verification

No agent may claim complete, fixed, passing, ready, deployed, or reconciled without fresh evidence for the exact candidate or state being described.

Repository CI is not proof of live deployment behavior. Mutable host, network, remote-ref, permission, and runtime facts require fresh checks when they matter.
