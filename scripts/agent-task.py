#!/usr/bin/env python3
"""Print repository-native agent task handoffs without mutating Git state."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover - Python < 3.11
    raise SystemExit("agent-task.py requires Python 3.11 or newer") from exc


ROOT = Path(__file__).resolve().parents[1]
AGENT_WORK = ROOT / "agent-work"


def load_manifest(phase: str) -> tuple[Path, dict]:
    manifest_path = AGENT_WORK / phase / "manifest.toml"
    try:
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError:
        raise SystemExit(f"unknown phase: {phase}")
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"invalid manifest: {exc}") from exc
    return manifest_path, data


DEFAULT_DEPENDENCY_SUCCESS_STATUSES = {"complete", "passed"}
V3_KINDS = {
    "implementation", "integration", "independent_review", "repair", "authority_promotion",
    "release_readiness", "live_deployment", "final_reconciliation", "other",
}
DEPLOYMENT_KINDS = {"authority_promotion", "release_readiness", "live_deployment", "final_reconciliation"}
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _fail(message: str) -> None:
    raise SystemExit(f"invalid manifest: {message}")


def _edge_status(task: dict, dependency: str) -> str | None:
    return task.get("required_status", {}).get(dependency)


def _success_edge(task: dict, dependency: str, *, review: bool = False) -> bool:
    required = _edge_status(task, dependency)
    return required == "passed" if review else required is None or required in DEFAULT_DEPENDENCY_SUCCESS_STATUSES


def validate_manifest(data: dict) -> None:
    """Fail closed on unsupported versions and malformed v3 task graphs; leave v2 semantics intact."""
    if not isinstance(data, dict) or type(data.get("workflow_version")) is not int:
        _fail("workflow_version must be 2 or 3")
    version = data["workflow_version"]
    if version == 2:
        return
    if version != 3:
        _fail(f"unsupported workflow_version {version}")

    tasks = data.get("tasks")
    status = data.get("status")
    workflow = data.get("workflow")
    if not isinstance(tasks, dict) or not tasks or not isinstance(status, dict) or not isinstance(workflow, dict):
        _fail("v3 requires [tasks], [status], and [workflow]")
    if any(not isinstance(task_id, str) or not task_id for task_id in tasks):
        _fail("v3 task IDs must be nonempty strings")
    if set(tasks) != set(status):
        _fail("v3 task and status IDs must match")
    terminal_task = workflow.get("terminal_task")
    if not isinstance(terminal_task, str) or terminal_task not in tasks:
        _fail("v3 workflow terminal_task must name a known task")
    for task_id, task in tasks.items():
        if not isinstance(task, dict) or task.get("kind") not in V3_KINDS:
            _fail(f"task {task_id} has an unsupported or missing kind")
        if any(not isinstance(task.get(key), str) or not task[key] for key in ("name", "branch", "file")):
            _fail(f"task {task_id} needs name, branch, and file")
        deps = task.get("depends_on")
        required = task.get("required_status", {})
        if (not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps) or
            len(deps) != len(set(deps)) or any(dep not in tasks or dep == task_id for dep in deps)):
            _fail(f"task {task_id} has invalid dependencies")
        if not isinstance(required, dict) or not set(required).issubset(deps) or any(
            value not in {"complete", "passed", "findings", "failed", "skipped", "blocked"}
            for value in required.values()
        ):
            _fail(f"task {task_id} has invalid required_status")
        rerun = task.get("rerun_after")
        if rerun is not None and (not isinstance(rerun, str) or rerun not in tasks or
                                  not isinstance(tasks[rerun], dict) or tasks[rerun].get("kind") != "repair"):
            _fail(f"task {task_id} has invalid rerun_after")
        if rerun is not None and (task_id not in tasks[rerun].get("depends_on", []) or
                                  _edge_status(tasks[rerun], task_id) != "findings" or
                                  not tasks[rerun].get("conditional")):
            _fail(f"task {task_id} rerun_after must name conditional findings repair")

    visiting: set[str] = set()
    ancestor_cache: dict[str, set[str]] = {}

    def ancestors(task_id: str) -> set[str]:
        if task_id in visiting:
            _fail("dependency cycle")
        if task_id in ancestor_cache:
            return ancestor_cache[task_id]
        visiting.add(task_id)
        found = set(tasks[task_id]["depends_on"])
        for dependency in tasks[task_id]["depends_on"]:
            found.update(ancestors(dependency))
        visiting.remove(task_id)
        ancestor_cache[task_id] = found
        return found

    for task_id in tasks:
        ancestors(task_id)

    evidence = workflow.get("evidence_manifest")
    phase = data.get("phase")
    if (not isinstance(phase, str) or not phase or phase in {".", ".."} or
        "/" in phase or "\\" in phase):
        _fail("v3 needs a single-segment phase identity")
    if evidence != f"agent-work/{phase}/evidence.json":
        _fail("v3 evidence_manifest must match the phase identity")
    deployment = data.get("deployment")
    if deployment is None:
        if any(task["kind"] in DEPLOYMENT_KINDS for task in tasks.values()):
            _fail("deployment task kind requires [deployment]")
        return
    if not isinstance(deployment, dict):
        _fail("[deployment] must be a table")
    stage_keys = ("review_task", "readiness_task", "live_task", "final_reconciliation_task")
    stage_kinds = ("independent_review", "release_readiness", "live_deployment", "final_reconciliation")
    stage_ids = [deployment.get(key) for key in stage_keys]
    authority = deployment.get("authority_task")
    if authority is not None:
        stage_ids.append(authority)
    implementations = deployment.get("implementation_tasks")
    if (not isinstance(implementations, list) or not implementations or
        any(not isinstance(impl, str) for impl in implementations) or
        len(implementations) != len(set(implementations)) or
        any(impl not in tasks or tasks[impl]["kind"] not in {"implementation", "integration"} for impl in implementations)):
        _fail("deployment needs nonempty implementation_tasks")
    if any(not isinstance(stage, str) or stage not in tasks for stage in stage_ids) or len(set(stage_ids)) != len(stage_ids):
        _fail("deployment stage IDs must be distinct known tasks")
    for stage, kind in zip(stage_ids[:4], stage_kinds):
        if tasks[stage]["kind"] != kind:
            _fail(f"deployment stage {stage} must be {kind}")
    if authority is not None and tasks[authority]["kind"] != "authority_promotion":
        _fail("authority_task must be authority_promotion")
    if any(task["kind"] in DEPLOYMENT_KINDS and task_id not in stage_ids for task_id, task in tasks.items()):
        _fail("undeclared deployment task kind")
    remote, ref = deployment.get("authority_remote"), deployment.get("authority_ref")
    if (not isinstance(remote, str) or not remote or
        not isinstance(ref, str) or not ref):
        _fail("deployment requires nonempty authority_remote and authority_ref")

    review, readiness, live, final = stage_ids[:4]
    if terminal_task != final:
        _fail("deployment workflow terminal_task must equal final_reconciliation_task")
    if any(impl not in ancestors(review) for impl in implementations):
        _fail("independent review must depend on all implementation outputs")
    # A failed or skipped upstream implementation cannot be laundered through review.
    for node in ancestors(review) | {review}:
        for dependency in tasks[node]["depends_on"]:
            if not _success_edge(tasks[node], dependency):
                _fail("review implementation ancestry requires success-only edges")
    if authority is not None:
        if review not in tasks[authority]["depends_on"] or not _success_edge(tasks[authority], review, review=True):
            _fail("authority promotion must directly require review passed")
    if review not in tasks[readiness]["depends_on"] or not _success_edge(tasks[readiness], review, review=True):
        _fail("release readiness must directly require review passed")
    if authority is not None and (authority not in tasks[readiness]["depends_on"] or
                                  not _success_edge(tasks[readiness], authority)):
        _fail("release readiness must require completed authority promotion")
    if readiness not in tasks[live]["depends_on"] or not _success_edge(tasks[live], readiness):
        _fail("live deployment must directly require completed readiness")
    human_gates = workflow.get("human_gate_tasks")
    if (tasks[live].get("human_gate") != "live-change-approval" or
        not isinstance(human_gates, list) or live not in human_gates):
        _fail("live deployment needs an explicit live-change-approval human gate")
    if live not in tasks[final]["depends_on"] or not _success_edge(tasks[final], live):
        _fail("final reconciliation must require successful live deployment")


def _canonical_batch(value: object) -> bytes:
    """Canonical JSON, including path-sorted entry arrays, for the approved batch."""
    def ordered(item: object) -> object:
        if isinstance(item, dict):
            return {key: ordered(part) for key, part in item.items()}
        if isinstance(item, list):
            parts = [ordered(part) for part in item]
            if parts and all(isinstance(part, dict) and isinstance(part.get("path"), str) for part in parts):
                parts.sort(key=lambda part: part["path"])
            return parts
        return item
    return json.dumps(ordered(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def batch_fingerprint(batch: dict) -> str:
    return hashlib.sha256(_canonical_batch(batch)).hexdigest()


def classify_divergence(*, identical: bool, object_present: bool = False,
                        ancestry_proven: bool = False, changed_paths_inspected: bool = False,
                        deployment_inputs_unchanged: bool = False, destructive: bool = False,
                        changed_paths: list[str] | None = None,
                        deployment_input_paths: list[str] | None = None) -> str:
    """Conservative classification of independently gathered Git proof, never a ref-name guess."""
    if identical and destructive:
        return "unknown"
    if identical:
        return "identical"
    if not object_present:
        return "unknown"
    if destructive:
        return "destructive"
    if (ancestry_proven and changed_paths_inspected and deployment_inputs_unchanged and
        isinstance(changed_paths, list) and all(isinstance(path, str) for path in changed_paths) and
        isinstance(deployment_input_paths, list) and deployment_input_paths and
        all(isinstance(path, str) and path for path in deployment_input_paths)):
        if any(fnmatch.fnmatchcase(path, pattern) or path.startswith(pattern.rstrip("/") + "/")
               for path in changed_paths for pattern in deployment_input_paths):
            return "protected_change"
        return "known_additive"
    return "unknown"


def _read_evidence(data: dict, evidence_path: Path | None) -> dict | None:
    phase = data.get("phase")
    if (not isinstance(phase, str) or not phase or
        data.get("workflow", {}).get("evidence_manifest") != f"agent-work/{phase}/evidence.json"):
        return None
    try:
        expected_path = ROOT / data["workflow"]["evidence_manifest"]
        path = evidence_path or expected_path
        if path.resolve() != expected_path.resolve():
            return None
        with path.open(encoding="utf-8") as handle:
            evidence = json.load(handle)
    except (KeyError, OSError, ValueError, TypeError):
        return None
    return evidence if (isinstance(evidence, dict) and evidence.get("workflowVersion") == 3 and
                        evidence.get("workflowId") == phase and isinstance(evidence.get("records"), list)) else None


def live_gate_state(data: dict, evidence_path: Path | None = None, *, allow_completed: bool = False) -> str:
    """Return GATED, PREVIEW, or READY; the coordinator still verifies real approval and drift."""
    deployment = data["deployment"]
    records_data = _read_evidence(data, evidence_path)
    if records_data is None:
        return "GATED"
    records = records_data["records"]
    review_id, readiness_id, live_id = (deployment[key] for key in ("review_task", "readiness_task", "live_task"))
    reviews = [(index, record) for index, record in enumerate(records)
               if isinstance(record, dict) and record.get("taskId") == review_id]
    readiness = [(index, record) for index, record in enumerate(records)
                 if isinstance(record, dict) and record.get("taskId") == readiness_id]
    if data["status"].get(review_id) != "passed" or data["status"].get(readiness_id) != "complete" or not reviews or not readiness:
        return "GATED"
    authority_id = deployment.get("authority_task")
    if authority_id is not None and data["status"].get(authority_id) not in DEFAULT_DEPENDENCY_SUCCESS_STATUSES:
        return "GATED"
    if any(data["status"].get(task_id) not in DEFAULT_DEPENDENCY_SUCCESS_STATUSES
           for task_id in deployment["implementation_tasks"]):
        return "GATED"
    review_index, review_record = reviews[-1]
    readiness_index, record = readiness[-1]
    if review_index >= readiness_index or review_record.get("taskStatus") != "passed":
        return "GATED"
    repair_id = data["tasks"][review_id].get("rerun_after")
    candidate_tasks = set(deployment["implementation_tasks"])
    if repair_id:
        candidate_tasks.add(repair_id)
    if any(isinstance(item, dict) and item.get("taskId") in candidate_tasks
           for item in records[review_index + 1:]):
        return "GATED"
    source = record.get("deploymentSourceSha")
    batch = record.get("frozenBatch")
    fingerprint = record.get("frozenBatchFingerprint")
    if (record.get("taskStatus") != "complete" or record.get("readinessVerdict") != "PASS" or
        not isinstance(source, str) or not SHA1.fullmatch(source) or
        not isinstance(batch, dict) or not isinstance(fingerprint, str) or not SHA256.fullmatch(fingerprint)):
        return "GATED"
    if review_record.get("deploymentSourceSha") != source:
        return "GATED"
    # Bind the final PASS to the latest completed implementation or post-findings repair.
    candidate_records = [(index, item) for index, item in enumerate(records[:review_index])
                         if isinstance(item, dict) and item.get("taskId") in candidate_tasks and
                         item.get("taskStatus") == "complete"]
    if not candidate_records:
        return "GATED"
    candidate_index, candidate_record = candidate_records[-1]
    if candidate_record.get("candidateSha") != source:
        return "GATED"
    findings_indices = [index for index, item in enumerate(records[:review_index])
                        if isinstance(item, dict) and item.get("taskId") == review_id and
                        item.get("taskStatus") == "findings"]
    if findings_indices:
        last_findings = findings_indices[-1]
        if (not repair_id or data["status"].get(repair_id) not in DEFAULT_DEPENDENCY_SUCCESS_STATUSES or
            not any(isinstance(item, dict) and item.get("taskId") == repair_id and
                    item.get("taskStatus") == "complete"
                    for item in records[last_findings + 1:review_index]) or
            candidate_index <= last_findings):
            return "GATED"
    elif candidate_record.get("taskId") == repair_id:
        # A repair without a recorded review finding is not a reviewed candidate.
        return "GATED"
    required_batch = {"deploymentSourceSha", "deployableArtifactSha256", "deploymentConfiguration", "validators", "rollbackArtifact", "installedScripts"}
    if not required_batch.issubset(batch) or batch.get("deploymentSourceSha") != source:
        return "GATED"
    if not isinstance(batch.get("deployableArtifactSha256"), str) or not SHA256.fullmatch(batch["deployableArtifactSha256"]):
        return "GATED"
    for key in ("deploymentConfiguration", "validators", "installedScripts"):
        entries = batch[key]
        if not isinstance(entries, list) or any(
            not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not entry["path"] or
            not isinstance(entry.get("sha256"), str) or not SHA256.fullmatch(entry["sha256"])
            for entry in entries
        ):
            return "GATED"
    rollback = batch["rollbackArtifact"]
    if not isinstance(rollback, dict) or any(not isinstance(rollback.get(key), str) or not rollback[key]
                                              for key in ("identity", "provenance")):
        return "GATED"
    try:
        if batch_fingerprint(batch) != fingerprint:
            return "GATED"
    except (TypeError, ValueError):
        return "GATED"
    divergence = record.get("gitDivergence")
    if not isinstance(divergence, dict) or divergence.get("authoritySha") != source:
        return "GATED"
    other_sha = divergence.get("otherSha")
    if not isinstance(other_sha, str) or not SHA1.fullmatch(other_sha):
        return "GATED"
    if divergence.get("identical") is True:
        if other_sha != source:
            return "GATED"
    else:
        if (divergence.get("ancestryAncestorSha") != source or divergence.get("ancestryDescendantSha") != other_sha or
            divergence.get("objectSha") != other_sha or
            not isinstance(divergence.get("proofEvidencePath"), str) or not divergence["proofEvidencePath"] or
            not isinstance(divergence.get("proofEvidenceSha256"), str) or
            not SHA256.fullmatch(divergence["proofEvidenceSha256"])):
            return "GATED"
    if classify_divergence(
        identical=divergence.get("identical") is True,
        object_present=divergence.get("objectPresent") is True,
        ancestry_proven=divergence.get("ancestryProven") is True,
        changed_paths_inspected=divergence.get("changedPathsInspected") is True,
        deployment_inputs_unchanged=divergence.get("deploymentInputsUnchanged") is True,
        destructive=divergence.get("destructive") is True,
        changed_paths=divergence.get("changedPaths"),
        deployment_input_paths=divergence.get("deploymentInputPaths"),
    ) not in {"identical", "known_additive"}:
        return "GATED"
    live_attempts = [item for item in records[readiness_index + 1:] if isinstance(item, dict)
                     and item.get("taskId") == live_id]
    if not live_attempts:
        return "PREVIEW"
    attempt = live_attempts[-1]
    return "READY" if (isinstance(attempt.get("approvalReference"), str) and
                       attempt["approvalReference"].strip() and
                       attempt.get("deploymentSourceSha") == source and
                       attempt.get("frozenBatchFingerprint") == fingerprint and
                       attempt.get("taskStatus") not in ({"failed", "skipped"} if allow_completed else
                                                         {"failed", "complete", "passed", "skipped"})) else "PREVIEW"


def final_reconciliation_ready(data: dict, evidence_path: Path | None = None) -> bool:
    """A completed live status alone cannot attest runtime acceptance."""
    if live_gate_state(data, evidence_path, allow_completed=True) != "READY":
        return False
    records_data = _read_evidence(data, evidence_path)
    if records_data is None:
        return False
    deployment = data["deployment"]
    live_records = [record for record in records_data["records"] if isinstance(record, dict)
                    and record.get("taskId") == deployment["live_task"]]
    readiness_records = [record for record in records_data["records"] if isinstance(record, dict)
                         and record.get("taskId") == deployment["readiness_task"]]
    if not live_records or not readiness_records:
        return False
    live_record, readiness_record = live_records[-1], readiness_records[-1]
    return (isinstance(live_record.get("approvalReference"), str) and
            bool(live_record["approvalReference"].strip()) and
            readiness_record.get("readinessVerdict") == "PASS" and
            live_record.get("taskStatus") in DEFAULT_DEPENDENCY_SUCCESS_STATUSES and
            live_record.get("runtimeAcceptance") == "PASS" and
            live_record.get("deploymentSourceSha") == readiness_record.get("deploymentSourceSha") and
            live_record.get("frozenBatchFingerprint") == readiness_record.get("frozenBatchFingerprint"))


def _dependencies_ready(task_id: str, data: dict) -> bool:
    tasks = data.get("tasks", {})
    status = data.get("status", {})
    task = tasks[task_id]
    current_status = status.get(task_id, "unknown")

    if current_status == "findings":
        rerun_after = task.get("rerun_after")
        if not isinstance(rerun_after, str) or status.get(rerun_after) not in DEFAULT_DEPENDENCY_SUCCESS_STATUSES:
            return False

    required_status = task.get("required_status", {})
    if not isinstance(required_status, dict):
        return False

    for dependency in task.get("depends_on", []):
        expected_status = required_status.get(dependency)
        if expected_status is not None:
            if not isinstance(expected_status, str) or status.get(dependency) != expected_status:
                return False
            continue
        if status.get(dependency) not in DEFAULT_DEPENDENCY_SUCCESS_STATUSES:
            return False

    return True


def task_ready(task_id: str, data: dict, evidence_path: Path | None = None) -> bool:
    if not _dependencies_ready(task_id, data):
        return False
    task = data["tasks"][task_id]
    if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment":
        return live_gate_state(data, evidence_path) == "READY"
    if data.get("workflow_version") == 3 and task.get("kind") == "final_reconciliation":
        return final_reconciliation_ready(data, evidence_path)
    return True



def print_coordinator(phase: str, data: dict) -> None:
    workflow = data.get("workflow", {})
    if not isinstance(workflow, dict):
        raise SystemExit("manifest is missing [workflow] coordinator configuration")
    if workflow.get("mode") != "coordinator":
        raise SystemExit("workflow mode is not coordinator")
    if workflow.get("auto_dispatch") is not True:
        raise SystemExit("workflow auto-dispatch is disabled")
    if workflow.get("plan_status") != "approved":
        raise SystemExit("workflow plan is not marked approved")
    coordinator = workflow.get("coordinator")
    if not isinstance(coordinator, str) or not coordinator:
        raise SystemExit("workflow coordinator file is not configured")
    max_parallel = workflow.get("max_parallel_subagents", 1)
    if not isinstance(max_parallel, int) or max_parallel < 1:
        raise SystemExit("workflow max_parallel_subagents must be a positive integer")

    print(f"{phase.upper()} WORKFLOW COORDINATOR")
    print(f"Title: {data.get('title', phase)}")
    print(f"Baseline: {data.get('phase_baseline', 'unknown')}")
    print(f"Plan: {data.get('plan', 'not configured')}")
    print(f"Contract: {data.get('contract', 'not configured')}")
    print(f"Coordinator: {coordinator}")
    print(f"Max parallel subagents: {max_parallel}")
    print()
    print("Coordinator instruction:")
    print(
        f"In the adopting repository, run {phase.replace('phase', 'Phase ')} as the workflow coordinator. "
        f"Read AGENTS.md, agent-work/WORKFLOW-SPEC.md, {coordinator}, and the phase manifest/plan/contract. "
        f"Execute the approved workflow end-to-end, using isolated subagents for ready tasks and stopping "
        f"only at declared human approval or safety gates."
    )

def print_task(phase: str, task_id: str, data: dict) -> None:
    tasks = data.get("tasks", {})
    if task_id not in tasks:
        raise SystemExit(f"unknown task {task_id!r} for {phase}")
    task = tasks[task_id]
    status = data.get("status", {}).get(task_id, "unknown")
    deps = task.get("depends_on", [])
    ready = task_ready(task_id, data)
    gate = live_gate_state(data) if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment" else None
    if gate == "READY" and not ready:
        gate = "GATED"

    print(f"{phase.upper()} / TASK {task_id}")
    print(f"Name: {task['name']}")
    print(f"Status: {status}")
    print(f"Ready by manifest: {'yes' if ready else 'no'}" if gate is None else f"Live gate: {gate}")
    print(f"Branch: {task['branch']}")
    print(f"Task file: {task['file']}")
    print(f"Contract: {data.get('contract', 'not configured')}")
    print(f"Dependencies: {', '.join(deps) if deps else 'none'}")
    if task.get("parallel_group"):
        print(f"Parallel group: {task['parallel_group']}")
    if task.get("conditional"):
        print(f"Conditional: {task['conditional']}")
    if task.get("rerun_after"):
        print(f"Rerun after: {task['rerun_after']}")
    print()
    print("Agent instruction:")
    if gate is not None:
        if gate == "GATED":
            print("Do not dispatch this live task; its required evidence or dependency gate is closed.")
        elif gate == "PREVIEW":
            print("Approval preview only; do not dispatch or mutate live state.")
        else:
            print("Coordinator handoff only: verify actual human approval, direct Git refs, and fresh live drift before dispatch.")
        return
    print(
        f"In the adopting repository, follow agent-work/README.md and execute "
        f"{phase.replace('phase', 'Phase ')} Task {task_id}. Stop at its completion boundary."
    )


def print_all(data: dict) -> None:
    for task_id, task in data.get("tasks", {}).items():
        status = data.get("status", {}).get(task_id, "unknown")
        if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment":
            ready = live_gate_state(data)
            if not task_ready(task_id, data) and ready == "READY":
                ready = "GATED"
        else:
            ready = "READY" if task_ready(task_id, data) else "BLOCKED"
        print(f"{task_id:>2}  {ready:<7} {status:<12} {task['name']}")


def print_ready(data: dict) -> None:
    found = False
    for task_id, task in data.get("tasks", {}).items():
        status = data.get("status", {}).get(task_id, "unknown")
        if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment":
            gate = live_gate_state(data)
            if gate == "PREVIEW" and _dependencies_ready(task_id, data) and status not in {"complete", "passed", "skipped"}:
                found = True
                print(f"{task_id}  {task['name']}  ->  ELIGIBLE FOR APPROVAL PREVIEW; not ready for live mutation")
            elif gate == "READY" and task_ready(task_id, data) and status not in {"complete", "passed", "skipped"}:
                found = True
                print(f"{task_id}  {task['name']}  ->  {task['file']} (coordinator must verify approval and fresh drift)")
            continue
        if task_ready(task_id, data) and status not in {"complete", "passed", "skipped"}:
            found = True
            print(f"{task_id}  {task['name']}  ->  {task['file']}")
    if not found:
        print("No incomplete tasks are currently ready by manifest state.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", help="workflow directory under agent-work, e.g. example")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("task", nargs="?", help="task ID, e.g. A")
    group.add_argument("--coordinator", action="store_true", help="print the one-shot workflow coordinator handoff")
    group.add_argument("--ready", action="store_true", help="list incomplete tasks whose dependencies are satisfied")
    group.add_argument("--all", action="store_true", help="list all tasks and manifest readiness")
    args = parser.parse_args()

    _path, data = load_manifest(args.phase)
    validate_manifest(data)
    if args.coordinator:
        print_coordinator(args.phase, data)
    elif args.ready:
        print_ready(data)
    elif args.all:
        print_all(data)
    else:
        print_task(args.phase, args.task.upper(), data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
