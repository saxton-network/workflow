"""Bounded mock scheduler. Agents supply results; coordinator owns transitions."""
from __future__ import annotations

from copy import deepcopy
import time
from .contracts import Rejected, digest, validate, validate_plan
from .permissions import COORDINATOR, HUMAN, ROLE_KIND, agent_for, require
from .providers import ProviderBus

MODELS = {"builder": "mock-builder-v1", "reviewer": "mock-reviewer-v1", "validator": "mock-validator-v1"}
MOCK_TOKENS = 15


def zero_usage():
    return {"input_tokens": 0, "output_tokens": 0, "cost_microusd": 0}


class Runtime:
    def __init__(self, store, git, *, bus=None, clock=None):
        self.store, self.git = store, git
        self.bus = bus or ProviderBus()
        self.clock = clock or (lambda: int(time.time()))

    def _change(self, workflow_id, operation, actor, fn, *, create=False):
        now = self.clock()
        if type(now) is not int or now < 0:
            raise Rejected("invalid runtime clock")
        def change(state, states):
            updated = fn(deepcopy(state), states, now)
            self._account(updated)
            return updated
        return self.store.transition(workflow_id, operation, actor, now, change, create=create)

    def create(self, plan, *, actor):
        require(actor, HUMAN)
        validate_plan(plan)
        self.git.check(plan)
        def change(_, states, now):
            return {"schema_version": 1, "plan": deepcopy(plan), "plan_hash": digest(plan),
                    "status": "draft", "approval": None, "agents": {}, "usage": zero_usage(), "reserved_tokens": 0,
                    "tasks": {t["id"]: {"status": "pending", "agent": None, "attempt": 0,
                              "lease": None, "checkpoint": None, "result": None, "history": []}
                              for t in plan["tasks"]}}
        return self._change(plan["workflow_id"], "create", actor, change, create=True)

    def approve(self, workflow_id, plan_hash, reference, *, actor):
        require(actor, HUMAN)
        if not isinstance(reference, str) or not reference.strip():
            raise Rejected("approval reference required")
        def change(state, states, now):
            if state["status"] != "draft" or plan_hash != state["plan_hash"]:
                raise Rejected("approval must bind exact draft proposal")
            state["approval"] = {"scope": "simulation", "plan_hash": plan_hash,
                                 "reference": reference, "actor": actor, "at": now}
            state["status"] = "approved"
            return state
        return self._change(workflow_id, "approve", actor, change)

    @staticmethod
    def _spec(state, task_id):
        for spec in state["plan"]["tasks"]:
            if spec["id"] == task_id:
                return spec
        raise Rejected("unknown task")

    @staticmethod
    def _account(state):
        """Unknown telemetry stays unknown; frozen mock reservations bound retries."""
        total = zero_usage()
        for agent_id, agent in state["agents"].items():
            usage = zero_usage()
            for task in state["tasks"].values():
                if task["agent"] != agent_id:
                    continue
                for attempt in task["history"]:
                    measured = attempt["result"]["usage"] if attempt["result"] is not None else {k: None for k in usage}
                    for key in usage:
                        usage[key] = None if usage[key] is None or measured[key] is None else usage[key] + measured[key]
            agent["usage"] = usage
            for key in total:
                total[key] = None if total[key] is None or usage[key] is None else total[key] + usage[key]
        state["usage"] = total

    def enroll(self, workflow_id, agent_id, role, task_id, *, actor, parent=None):
        require(actor, HUMAN)
        import re
        if (not isinstance(agent_id, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", agent_id) is None or
                agent_id in {HUMAN, COORDINATOR}):
            raise Rejected("invalid agent identity")
        def change(state, states, now):
            spec = self._spec(state, task_id)
            task = state["tasks"][task_id]
            if (state["status"] not in {"draft", "approved"} or agent_id in state["agents"] or
                    task["agent"] is not None or ROLE_KIND.get(role) != spec["kind"]):
                raise Rejected("enrollment or role assignment not authorized")
            if parent is not None and (parent not in state["agents"] or state["agents"][parent]["state"] == "stopped"):
                raise Rejected("unknown or stopped lineage parent")
            state["agents"][agent_id] = {"role": role, "parent": parent, "created_by": HUMAN,
                                        "created_at": now, "last_activity": now, "state": "idle",
                                        "task": task_id, "provider": "mock", "model": MODELS[role],
                                        "usage": zero_usage()}
            task["agent"] = agent_id
            return state
        return self._change(workflow_id, "enroll", actor, change)

    @staticmethod
    def _approved(state):
        approval = state["approval"]
        if (state["status"] not in {"approved", "running"} or approval is None or
                approval["plan_hash"] != state["plan_hash"] or approval["scope"] != "simulation"):
            raise Rejected("approved simulation plan required")

    @staticmethod
    def _evidence(result):
        validate("result", result)
        if result["verdict"] != "PASS" or result["artifact_hash"] != digest(result["artifact"]):
            raise Rejected("failed, unknown, or invalid artifact evidence")
        if any(v is None for v in result["usage"].values()):
            raise Rejected("unknown mock resource telemetry")
        if result["usage"] != {"input_tokens": 10, "output_tokens": 5, "cost_microusd": 0}:
            raise Rejected("mock resource contract mismatch")

    def _eligible(self, state, task_id):
        spec = self._spec(state, task_id)
        task = state["tasks"][task_id]
        if task["status"] != "pending" or task["agent"] is None:
            return False
        if state["agents"][task["agent"]]["state"] != "idle":
            return False
        for dep in spec["depends_on"]:
            dep_task = state["tasks"][dep]
            wanted = "passed" if self._spec(state, dep)["kind"] == "review" else "complete"
            if dep_task["status"] != wanted or dep_task["result"] is None:
                return False
            self._evidence(dep_task["result"])
        if spec["kind"] == "review":
            builder = state["tasks"][spec["subject"]]["agent"]
            reviewer = task["agent"]
            if (builder == reviewer or state["agents"][builder]["model"] == state["agents"][reviewer]["model"]):
                raise Rejected("reviewer is not independent")
        return True

    def _request(self, state, task_id):
        task, spec = state["tasks"][task_id], self._spec(state, task_id)
        return {"schema_version": 1, "workflow_id": state["plan"]["workflow_id"],
                "task_id": task_id, "attempt": task["attempt"], "lease": task["lease"]["token"],
                "plan_hash": state["plan_hash"], "source_sha": state["plan"]["source_sha"],
                "subject_hash": state["tasks"][spec["subject"]]["result"]["artifact_hash"] if spec["subject"] else None,
                "objective": state["plan"]["objective"], "kind": spec["kind"],
                "model": state["agents"][task["agent"]]["model"]}

    def inspect(self, workflow_id):
        state = self.store.read(workflow_id)
        eligible = []
        if state["status"] in {"approved", "running"}:
            self._approved(state)
            eligible = [t["id"] for t in state["plan"]["tasks"] if self._eligible(state, t["id"])]
        return {"state": state, "eligible_tasks": eligible, "providers": self.bus.discover(),
                "simulation": True, "deployment_authority": False}

    def claim(self, workflow_id, task_id, *, actor):
        require(actor, COORDINATOR)
        def change(state, states, now):
            self._approved(state)
            self.git.check(state["plan"])
            if not self._eligible(state, task_id):
                raise Rejected("task dependencies, assignment, or status block dispatch")
            task, spec = state["tasks"][task_id], self._spec(state, task_id)
            agent = state["agents"][task["agent"]]
            if ROLE_KIND[agent["role"]] != spec["kind"]:
                raise Rejected("assigned actor lacks task role")
            self.bus.adapter(agent["provider"], agent["model"], spec["kind"])
            for other in states.values():
                for other_id, other_task in other["tasks"].items():
                    if other_task["status"] == "running":
                        other_spec = self._spec(other, other_id)
                        if (spec["branch"] == other_spec["branch"] or spec["worktree"] == other_spec["worktree"]):
                            raise Rejected("isolated resource already owned")
            limit = state["plan"]["estimates"]
            # Reserve fixed mock consumption at claim, including interrupted attempts.
            used = state["reserved_tokens"]
            if used + MOCK_TOKENS > limit["max_tokens"] or task["attempt"] >= limit["max_attempts"]:
                raise Rejected("frozen resource/attempt limit reached")
            task["attempt"] += 1
            token = digest({"workflow": workflow_id, "task": task_id, "attempt": task["attempt"],
                            "plan": state["plan_hash"]})
            task["lease"] = {"token": token, "expires_at": now + limit["lease_seconds"], "heartbeat_at": now}
            task["checkpoint"] = None
            task["status"] = agent["state"] = "running"
            task["history"].append({"attempt": task["attempt"], "lease": token, "started_at": now,
                                    "finished_at": None, "status": "running", "reason": None, "result": None})
            state["reserved_tokens"] += MOCK_TOKENS
            agent["last_activity"] = now
            state["status"] = "running"
            return state
        state = self._change(workflow_id, "claim", actor, change)
        return self._request(state, task_id)

    @staticmethod
    def _lease(state, task_id, token, now):
        task = state["tasks"].get(task_id)
        if (task is None or state["status"] != "running" or task["status"] != "running" or
                task["lease"] is None or task["lease"]["token"] != token or
                now >= task["lease"]["expires_at"]):
            raise Rejected("inactive, stale, or foreign execution lease")
        return task

    @staticmethod
    def _fail(state, task_id, now, reason, *, result=None, cancelled=False):
        task = state["tasks"][task_id]
        task["status"] = "cancelled" if cancelled else "failed"
        task["history"][-1].update(status=task["status"], finished_at=now, reason=reason, result=result)
        task["lease"] = None
        state["agents"][task["agent"]]["state"] = "stopped"
        state["agents"][task["agent"]]["last_activity"] = now
        state["status"] = "cancelled" if cancelled else "failed"

    def finish(self, workflow_id, task_id, lease, result, *, actor, error=None):
        require(actor, COORDINATOR)
        def change(state, states, now):
            task = state["tasks"].get(task_id)
            if (task is not None and task["status"] in {"complete", "passed"} and
                    task["history"][-1]["lease"] == lease and result == task["result"] and error is None):
                return state  # Already durably accepted: no second event or dispatch.
            task = self._lease(state, task_id, lease, now)
            self.git.check(state["plan"])
            if error is not None:
                self._fail(state, task_id, now, error)
                return state
            request = self._request(state, task_id)
            try:
                self._evidence(result)
                for key in ("workflow_id", "task_id", "attempt", "lease", "plan_hash", "source_sha", "subject_hash", "model"):
                    if result[key] != request[key]:
                        raise Rejected(f"result identity mismatch: {key}")
                expected_artifact = {"objective": request["objective"], "task": task_id,
                                     "source_sha": request["source_sha"], "subject_hash": request["subject_hash"],
                                     "simulation": True}
                if result["provider"] != "mock" or result["artifact"] != expected_artifact:
                    raise Rejected("mock artifact/identity mismatch")
                # Recheck dependency evidence at acceptance, not just claim.
                spec = self._spec(state, task_id)
                for dep in spec["depends_on"]:
                    self._evidence(state["tasks"][dep]["result"])
            except Rejected as exc:
                # Preserve well-formed rejected result; malformed input gets a reason only.
                try:
                    validate("result", result)
                    rejected_result = result
                except Rejected:
                    rejected_result = None
                self._fail(state, task_id, now, str(exc), result=rejected_result)
                return state
            task["result"] = deepcopy(result)
            task["status"] = "passed" if self._spec(state, task_id)["kind"] == "review" else "complete"
            task["history"][-1].update(status=task["status"], finished_at=now, result=deepcopy(result))
            task["lease"] = None
            agent = state["agents"][task["agent"]]
            agent["state"], agent["last_activity"] = "idle", now
            if task_id == state["plan"]["terminal_task"]:
                state["status"] = "completed"
            return state
        return self._change(workflow_id, "finish", actor, change)

    def advance(self, workflow_id, *, actor):
        require(actor, COORDINATOR)
        view = self.inspect(workflow_id)
        if not view["eligible_tasks"]:
            return view
        task_id = view["eligible_tasks"][0]
        request = self.claim(workflow_id, task_id, actor=actor)
        try:
            agent = self.store.read(workflow_id)["agents"][view["state"]["tasks"][task_id]["agent"]]
            adapter = self.bus.adapter(agent["provider"], agent["model"], request["kind"])
            result = adapter.dispatch(request, timeout_seconds=view["state"]["plan"]["estimates"]["lease_seconds"])
        except Exception as exc:
            # Adapter messages can contain secrets. Persist only a bounded failure class.
            self.finish(workflow_id, task_id, request["lease"], None, actor=actor,
                        error=f"provider failure: {type(exc).__name__}")
        else:
            self.finish(workflow_id, task_id, request["lease"], result, actor=actor)
        return self.inspect(workflow_id)

    def heartbeat(self, workflow_id, task_id, lease, *, actor):
        def change(state, states, now):
            agent = agent_for(state, task_id, actor)
            task = self._lease(state, task_id, lease, now)
            task["lease"].update(heartbeat_at=now, expires_at=now + state["plan"]["estimates"]["lease_seconds"])
            agent["last_activity"] = now
            return state
        return self._change(workflow_id, "heartbeat", actor, change)

    def checkpoint(self, workflow_id, task_id, lease, data, *, actor):
        if not isinstance(data, dict):
            raise Rejected("checkpoint must be an object")
        def change(state, states, now):
            agent_for(state, task_id, actor)
            task = self._lease(state, task_id, lease, now)
            task["checkpoint"] = {"task": task_id, "attempt": task["attempt"], "lease": lease,
                                  "data": deepcopy(data), "sha256": digest(data)}
            return state
        return self._change(workflow_id, "checkpoint", actor, change)

    def recover(self, workflow_id, *, actor):
        require(actor, COORDINATOR)
        def change(state, states, now):
            if state["status"] in {"completed", "cancelled"}:
                return state
            for task_id, task in state["tasks"].items():
                if task["status"] == "running" and now >= task["lease"]["expires_at"]:
                    self._fail(state, task_id, now, "expired lease: interrupted mock execution")
            return state
        return self._change(workflow_id, "recover", actor, change)

    def retry(self, workflow_id, task_id, *, actor):
        require(actor, COORDINATOR)
        def change(state, states, now):
            task = state["tasks"].get(task_id)
            if (state["status"] != "failed" or task is None or task["status"] != "failed" or
                    task["attempt"] >= state["plan"]["estimates"]["max_attempts"] or
                    any(t["status"] == "running" for t in state["tasks"].values())):
                raise Rejected("retry not authorized by bounded simulation policy")
            self.git.check(state["plan"])
            task["status"], task["result"] = "pending", None
            task["checkpoint"] = None
            state["agents"][task["agent"]]["state"] = "idle"
            state["status"] = "failed" if any(t["status"] == "failed" for t in state["tasks"].values()) else "approved"
            return state
        return self._change(workflow_id, "retry", actor, change)

    def cancel(self, workflow_id, *, actor):
        if actor not in {HUMAN, COORDINATOR}:
            raise Rejected("cancellation requires operator authority")
        def change(state, states, now):
            if state["status"] == "completed":
                raise Rejected("completed workflow cannot be cancelled")
            if state["status"] == "cancelled":
                return state
            for task_id, task in state["tasks"].items():
                if task["status"] == "running":
                    self._fail(state, task_id, now, "operator cancellation", cancelled=True)
                elif task["status"] in {"pending", "failed"}:
                    task["status"] = "cancelled"
                    if task["agent"]:
                        state["agents"][task["agent"]]["state"] = "stopped"
            state["status"] = "cancelled"
            return state
        return self._change(workflow_id, "cancel", actor, change)
