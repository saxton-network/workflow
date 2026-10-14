"""Versioned contracts, strict JSON decoding, and semantic safety checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class Rejected(ValueError):
    """A fail-closed domain verdict; no successful transition was authorized."""


def canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise Rejected("value is outside the JSON contract") from exc


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("duplicate JSON key")
        result[key] = value
    return result


def decode(raw: str) -> object:
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Rejected("nonfinite JSON")))
    except (ValueError, TypeError, RecursionError) as exc:
        raise Rejected(f"invalid JSON: {exc}") from exc


def _validate(value: object, spec: dict, root: dict, path: str) -> None:
    """Dependency-free validator for the explicitly used JSON Schema subset."""
    if "$ref" in spec:
        spec = root["$defs"][spec["$ref"].split("/")[-1]]
    if "anyOf" in spec:
        for option in spec["anyOf"]:
            try:
                _validate(value, option, root, path)
                return
            except Rejected:
                pass
        raise Rejected(f"{path}: no allowed type")
    types = {"object": type(value) is dict, "array": type(value) is list,
             "string": type(value) is str, "integer": type(value) is int,
             "boolean": type(value) is bool, "null": value is None}
    if "type" in spec and not types[spec["type"]]:
        raise Rejected(f"{path}: expected {spec['type']}")
    if "enum" in spec and value not in spec["enum"]:
        raise Rejected(f"{path}: invalid enum")
    if "const" in spec and (type(value) is not type(spec["const"]) or value != spec["const"]):
        raise Rejected(f"{path}: unsupported contract value")
    if isinstance(value, str):
        import re
        if len(value) < spec.get("minLength", 0) or len(value) > spec.get("maxLength", 100000):
            raise Rejected(f"{path}: invalid length")
        if "pattern" in spec and re.fullmatch(spec["pattern"], value) is None:
            raise Rejected(f"{path}: invalid spelling")
    if type(value) is int and value < spec.get("minimum", value):
        raise Rejected(f"{path}: below minimum")
    if type(value) is dict:
        properties = spec.get("properties", {})
        if not set(spec.get("required", [])).issubset(value):
            raise Rejected(f"{path}: missing fields")
        for key, item in value.items():
            child = properties.get(key, spec.get("additionalProperties", True))
            if child is False:
                raise Rejected(f"{path}: unknown field {key}")
            if isinstance(child, dict):
                _validate(item, child, root, f"{path}.{key}")
    if type(value) is list:
        if len(value) < spec.get("minItems", 0):
            raise Rejected(f"{path}: empty collection")
        if spec.get("uniqueItems") and len({canonical(v) for v in value}) != len(value):
            raise Rejected(f"{path}: duplicate entries")
        for item in value:
            _validate(item, spec.get("items", {}), root, path + "[]")


def validate(name: str, value: object) -> None:
    schema = json.loads((Path(__file__).parent / "schemas" / f"{name}-v1.json").read_text())
    schema["$defs"] = json.loads((Path(__file__).parent / "schemas" / "contracts-v1.json").read_text())["$defs"]
    _validate(value, schema, schema, name)


def validate_plan(plan: dict) -> None:
    validate("plan", plan)
    tasks = plan["tasks"]
    if len({t["id"] for t in tasks}) != len(tasks):
        raise Rejected("duplicate task identity")
    by_id = {t["id"]: t for t in tasks}
    seen, active = set(), set()

    def visit(task_id: str) -> None:
        if task_id not in by_id or task_id in active:
            raise Rejected("unknown dependency or cycle")
        if task_id in seen:
            return
        active.add(task_id)
        for dep in by_id[task_id]["depends_on"]:
            visit(dep)
        active.remove(task_id)
        seen.add(task_id)

    for task in tasks:
        visit(task["id"])
        if task["kind"] == "review":
            if (task["subject"] not in task["depends_on"] or
                    by_id[task["subject"]]["kind"] != "build"):
                raise Rejected("review must directly cover a build")
        elif task["subject"] is not None:
            raise Rejected("only review has a subject")
    builds = {t["id"] for t in tasks if t["kind"] == "build"}
    reviews = {t["id"] for t in tasks if t["kind"] == "review"}
    if not builds or {by_id[t]["subject"] for t in reviews} != builds:
        raise Rejected("every build needs mandatory independent review")
    terminals = [t for t in tasks if t["kind"] == "validate"]
    if (len(terminals) != 1 or terminals[0]["id"] != plan["terminal_task"] or
            set(terminals[0]["depends_on"]) != set(by_id) - {terminals[0]["id"]}):
        raise Rejected("terminal validation must depend on every other task")
    # Prevent aliases even before active ownership reservations exist.
    for field in ("branch", "worktree"):
        values = [t[field] for t in tasks]
        if len(set(values)) != len(values):
            raise Rejected(f"duplicate {field} ownership")


def validate_state(state: dict) -> None:
    validate("state", state)
    validate_plan(state["plan"])
    if state["plan_hash"] != digest(state["plan"]):
        raise Rejected("checkpoint plan hash mismatch")
    expected = {t["id"] for t in state["plan"]["tasks"]}
    if set(state["tasks"]) != expected:
        raise Rejected("checkpoint task identities mismatch")
    if state["approval"] is not None and state["approval"]["plan_hash"] != state["plan_hash"]:
        raise Rejected("checkpoint approval hash mismatch")
    if state["status"] not in {"draft", "cancelled"} and state["approval"] is None:
        raise Rejected("checkpoint lacks approval")
    specs = {t["id"]: t for t in state["plan"]["tasks"]}
    assigned = []
    for task_id, task in state["tasks"].items():
        if task["agent"] is not None and task["agent"] not in state["agents"]:
            raise Rejected("checkpoint missing actor")
        if (task["status"] == "running") != (task["lease"] is not None):
            raise Rejected("checkpoint lease/state mismatch")
        if task["agent"] is not None:
            assigned.append(task["agent"])
            agent = state["agents"][task["agent"]]
            if agent["task"] != task_id or {"builder": "build", "reviewer": "review", "validator": "validate"}[agent["role"]] != specs[task_id]["kind"]:
                raise Rejected("checkpoint assignment/role mismatch")
        if task["attempt"] != len(task["history"]) or task["attempt"] > state["plan"]["estimates"]["max_attempts"]:
            raise Rejected("checkpoint attempt history mismatch")
        if (task["status"] in {"running", "complete", "passed", "failed"} or task["checkpoint"] is not None) and not task["history"]:
            raise Rejected("checkpoint lacks required attempt history")
        for index, attempt in enumerate(task["history"], 1):
            if attempt["attempt"] != index:
                raise Rejected("checkpoint attempt ordering mismatch")
        if task["status"] == "running":
            if (task["history"][-1]["status"] != "running" or
                    task["history"][-1]["lease"] != task["lease"]["token"]):
                raise Rejected("checkpoint fencing mismatch")
        if task["status"] in {"complete", "passed"}:
            result = task["result"]
            if (result is None or result["verdict"] != "PASS" or
                    result["artifact_hash"] != digest(result["artifact"]) or
                    result != task["history"][-1]["result"] or
                    result["source_sha"] != state["plan"]["source_sha"] or
                    result["plan_hash"] != state["plan_hash"] or
                    result["workflow_id"] != state["plan"]["workflow_id"] or result["task_id"] != task_id):
                raise Rejected("checkpoint successful evidence mismatch")
        if task["checkpoint"] is not None:
            cp = task["checkpoint"]
            if (cp["sha256"] != digest(cp["data"]) or cp["task"] != task_id or
                    cp["attempt"] != task["attempt"] or
                    cp["lease"] != task["history"][-1]["lease"]):
                raise Rejected("corrupted task checkpoint")
    if len(set(assigned)) != len(assigned) or set(assigned) != set(state["agents"]):
        raise Rejected("checkpoint duplicate or unassigned actors")
    if state["status"] == "completed" and any(
            t["status"] != ("passed" if specs[tid]["kind"] == "review" else "complete")
            for tid, t in state["tasks"].items()):
        raise Rejected("checkpoint premature completion")
    for agent_id, agent in state["agents"].items():
        if agent["parent"] is not None and agent["parent"] not in state["agents"]:
            raise Rejected("orphaned lineage")
        if agent["state"] == "running":
            task = state["tasks"].get(agent["task"])
            if task is None or task["status"] != "running" or task["agent"] != agent_id:
                raise Rejected("orphaned actor")
