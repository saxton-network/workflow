# Workflow

A repository-native workflow system for coordinating AI coding agents with isolated worktrees, independent review, evidence-backed gates, and fail-closed deployment safety.

> **Status: experimental / pre-1.0.** The repository-only path has passed a controlled end-to-end pilot. Deployment-readiness behavior is still being adversarially piloted. Treat the deployment model as a safety framework to review and adapt, not as a turnkey deployer.

## What it is

Workflow turns an approved implementation plan into a durable task graph stored in the repository. The graph can coordinate builders, independent reviewers, conditional repairs, integration, release readiness, explicit human approval, live deployment, runtime acceptance, and final reconciliation.

The included scripts/agent-task.py helper is intentionally **read-only**. It validates manifests and reports task/gate readiness. It does not compile plans, mutate Git, deploy software, or grant human approval.

## Core invariants

- One mutating agent per branch/worktree.
- Builders do not approve their own work.
- Review findings activate a separate repair role and then return to the same reviewer.
- Ordinary dependencies require complete or passed. Findings, failed, blocked, and skipped do not silently satisfy them.
- Deployment source identity is separate from review/result/evidence commits.
- Release readiness is read-only and produces a deterministic frozen-batch fingerprint.
- PASS, FAIL, and UNKNOWN readiness are distinct.
- Readiness PASS without human approval is approval-preview eligible, not live-mutation authority.
- Deployment workflows terminate only at final reconciliation.
- Deployment authority is explicit even when no promotion task is necessary.
- Unknown or destructive Git divergence fails closed.
- Runtime acceptance is required before final reconciliation.

## Layout

~~~text
AGENTS.md
agent-work/
  README.md
  WORKFLOW-SPEC.md
  COORDINATOR.md
  RESULT-TEMPLATE.md
  EVIDENCE-MANIFEST.md
docs/
  DESIGN.md
  PILOT-HISTORY.md
  RELEASING.md
examples/
  README.md
  nondeployment/manifest.toml
  deployment/manifest.toml
scripts/
  agent-task.py
  validate-repository.sh
  tests/test_agent_workflow.py
.github/workflows/
  validate.yml
  release.yml
~~~

## Quick start

1. Copy or vendor the workflow control files into a repository.
2. Define repository-specific safety rules and deployment authority in AGENTS.md.
3. Create agent-work/<workflow-id>/PLAN.md, manifest.toml, task files, and results/.
4. Validate the manifest:

~~~bash
python3 scripts/agent-task.py <workflow-id> --all
python3 scripts/agent-task.py <workflow-id> --ready
~~~

5. Run the repository gate:

~~~bash
bash scripts/validate-repository.sh
~~~

6. Let the coordinator advance only through evidence-backed ready tasks.

See examples/ for non-deployment and deployment graph shapes.

## Deployment model

~~~text
implementation/integration
        |
independent review
        |
optional authority promotion
        |
release readiness
        |
explicit human approval
        |
live deployment + runtime acceptance
        |
final reconciliation
~~~

The manifest must still declare an authority remote/ref when promotion is omitted. That means the source is already authoritative, not that authority is irrelevant.

The live gate has three helper states:

- **GATED**: required evidence is missing, invalid, stale, or failed.
- **PREVIEW**: readiness PASS is proven, but there is no matching approval reference.
- **READY**: evidence contains a matching approval reference. This is still only a coordinator handoff. The coordinator must verify the actual human approval and recheck mutable state before mutation.

## Evidence

Workflow v3 uses a compact coordinator-owned evidence.json. Detailed logs and reports remain separate and are linked by path plus SHA-256. Failed attempts are preserved. Frozen deployment batches explicitly bind deployment destinations and mode metadata, so a changed target invalidates readiness and approval. Credentials, bearer values, private keys, secret-bearing bodies, and chat transcripts do not belong in the index.

## Validation

The public repository intentionally has a small dependency surface. CI validates Python syntax, the Workflow v3 regression suite, example TOML manifests, and shell syntax. It requires no production credentials and performs no deployment.

## Releases

Public releases are intentionally dispatched by a human from `main`. The release workflow validates the exact commit, creates a Git archive ZIP plus SHA-256 checksum, and refuses to move or overwrite an existing version tag. See `docs/RELEASING.md`.

## Origin

The design grew out of real multi-agent repository and deployment work where implementation defects were not the dominant source of failure. Stale assumptions, validator mistakes, source-identity ambiguity, Git divergence, and deployment-procedure drift were. Workflow v3 moves those failure modes into explicit gates and evidence.

See docs/PILOT-HISTORY.md for sanitized examples of defects found by the workflow's own pilots.

## License

No public license has been selected yet. Until one is added, normal copyright rules apply. This is intentional so the project can be published and reviewed before a licensing choice is made.
