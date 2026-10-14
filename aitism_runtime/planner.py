"""Inspectible deterministic Workshop template; no model/API or execution."""
from .contracts import validate_plan


def propose(objective: str, source_sha: str, workflow_id: str) -> dict:
    tasks = []
    for task_id, kind, deps, subject in (
            ("build", "build", [], None), ("review", "review", ["build"], "build"),
            ("validate", "validate", ["build", "review"], None)):
        tasks.append({"id": task_id, "kind": kind, "depends_on": deps, "subject": subject,
                      "branch": f"sim/{workflow_id}/{task_id}",
                      "worktree": f"sim/{workflow_id}/{task_id}"})
    plan = {"schema_version": 1, "workflow_id": workflow_id, "objective": objective,
            "scope": "simulation", "source_sha": source_sha,
            "source_branch": "experimental/features", "terminal_task": "validate",
            "requirements": [objective, "No external calls or source mutations"],
            "assumptions": ["Trusted local operator", "Deterministic mock provider only"],
            "architecture": "Bounded mock build, independent mock review, evidence validation",
            "roles": ["human", "coordinator", "builder", "reviewer", "validator"],
            "review_strategy": "Separate actor and mock model; exact artifact/source binding",
            "test_strategy": "Checksum validation and fail-closed adversarial tests",
            "estimates": {"max_tokens": 1000, "max_attempts": 2, "lease_seconds": 30},
            "risks": [{"classification": "low", "description": "Simulation only; no deployment authority"}],
            "approval_checkpoints": ["Exact proposal hash before mock dispatch"], "tasks": tasks}
    validate_plan(plan)
    return plan
