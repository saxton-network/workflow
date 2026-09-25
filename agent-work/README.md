# Agent work

This directory defines the repository-native workflow protocol.

- WORKFLOW-SPEC.md is the normative graph and gate specification.
- COORDINATOR.md defines coordinator behavior.
- RESULT-TEMPLATE.md defines durable task handoffs.
- EVIDENCE-MANIFEST.md defines the compact v3 evidence index.

## Workflow compilation

After a plan has been independently reviewed and approved, compile it into:

~~~text
agent-work/<workflow-id>/
  PLAN.md
  CONTRACT.md
  manifest.toml
  A-*.md
  B-*.md
  ...
  evidence.json
  results/
~~~

CONTRACT.md is optional when there is no behavior or safety contract to freeze.

The compiler is instruction-driven. The included helper does not create this scaffold.

## Task agent contract

A task agent should:

1. Read AGENTS.md.
2. Read this file and the selected workflow manifest.
3. Verify its dependencies are satisfied.
4. Read the plan, contract when present, and its task file.
5. Work only on its declared branch/worktree and owned paths.
6. Establish a baseline before editing.
7. Run fresh required validation.
8. Write a result using RESULT-TEMPLATE.md.
9. Stop at the task boundary.

Only the coordinator advances shared status or edits evidence.json.

## Helper

From the repository root:

~~~bash
python3 scripts/agent-task.py <workflow-id> --coordinator
python3 scripts/agent-task.py <workflow-id> A
python3 scripts/agent-task.py <workflow-id> --ready
python3 scripts/agent-task.py <workflow-id> --all
~~~

The helper is read-only.
