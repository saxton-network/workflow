"""Trusted local identities; no delegated authority or permission expansion."""
from .contracts import Rejected

HUMAN = "human"
COORDINATOR = "coordinator"
ROLE_KIND = {"builder": "build", "reviewer": "review", "validator": "validate"}


def require(actor: str, expected: str) -> None:
    if actor != expected:
        raise Rejected(f"operation requires {expected} authority")


def agent_for(state: dict, task_id: str, actor: str) -> dict:
    task = state["tasks"].get(task_id)
    if task is None or task["agent"] != actor or actor not in state["agents"]:
        raise Rejected("actor does not own task")
    agent = state["agents"][actor]
    if agent["state"] != "running" or agent["task"] != task_id:
        raise Rejected("actor has no active authority")
    return agent
