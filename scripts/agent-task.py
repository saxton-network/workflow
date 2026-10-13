#!/usr/bin/env python3
"""Print repository-native agent task handoffs without mutating Git state."""

from __future__ import annotations

import argparse
import fnmatch
import functools
import hashlib
import ipaddress
import itertools
import json
import os
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
# Locations have one accepted spelling (agent-work/EVIDENCE-MANIFEST.md); anything else is GATED.
SEGMENT = re.compile(r"[A-Za-z0-9._~-]+")
GLOB_SEGMENT = re.compile(r"[A-Za-z0-9._~*?\[\]!-]+")
WINDOWS_DRIVE_PATH = re.compile(r"[A-Z]:\\")
# A one-letter scheme would read as a drive (c://x is C:\\x), so schemes have at least two characters.
URL_FORM = re.compile(r"([a-z][a-z0-9+.-]+)://([^/]*)(/.*)?")
HOST_NAME = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*")
IPV4 = re.compile(r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}")
DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443, "ftp": 21, "ftps": 990,
                 "ssh": 22, "sftp": 22, "scp": 22, "rsync": 873, "git": 9418, "smb": 445}
HOST_REQUIRED_SCHEMES = {"http", "https", "ws", "wss", "ftp"}
NUMERIC_LABEL = re.compile(r"\d+|0x[0-9a-f]*")
WINDOWS_DEVICE_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"{port}{n}" for port in ("COM", "LPT") for n in range(1, 10))}
MAX_PATTERN_EXPANSIONS = 6


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
    if any(not isinstance(value, str) for value in status.values()):
        _fail("v3 status values must be strings")
    terminal_task = workflow.get("terminal_task")
    if not isinstance(terminal_task, str) or terminal_task not in tasks:
        _fail("v3 workflow terminal_task must name a known task")
    for task_id, task in tasks.items():
        if not isinstance(task, dict) or not isinstance(task.get("kind"), str) or task["kind"] not in V3_KINDS:
            _fail(f"task {task_id} has an unsupported or missing kind")
        if any(not isinstance(task.get(key), str) or not task[key] for key in ("name", "branch", "file")):
            _fail(f"task {task_id} needs name, branch, and file")
        deps = task.get("depends_on")
        required = task.get("required_status", {})
        if (not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps) or
            len(deps) != len(set(deps)) or any(dep not in tasks or dep == task_id for dep in deps)):
            _fail(f"task {task_id} has invalid dependencies")
        if not isinstance(required, dict) or not set(required).issubset(deps) or any(
            not isinstance(value, str) or value not in {"complete", "passed", "findings", "failed", "skipped", "blocked"}
            for value in required.values()
        ):
            _fail(f"task {task_id} has invalid required_status")
    # Cross-task checks below may read another task's fields, so every task is type-checked first.
    for task_id, task in tasks.items():
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


SOURCE_ONLY_BATCH_LISTS = ("validators", "installedScripts")
BATCH_PATH_LISTS = ("deploymentConfiguration", "validators", "installedScripts")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _canonical_batch(batch: dict) -> bytes:
    """Canonical JSON for the approved batch; only the declared arrays are reordered."""
    record = dict(batch)
    sorted_arrays = [(key, "path") for key in BATCH_PATH_LISTS] + [("deploymentTargets", "destination")]
    for key, field in sorted_arrays:
        entries = record.get(key)
        if isinstance(entries, list) and all(isinstance(entry, dict) and isinstance(entry.get(field), str)
                                             for entry in entries):
            # Break ties on the whole entry so the encoding never depends on input order.
            record[key] = sorted(entries, key=lambda entry: (entry[field], _canonical_json(entry)))
    return _canonical_json(record).encode("utf-8")


def batch_fingerprint(batch: dict) -> str:
    return hashlib.sha256(_canonical_batch(batch)).hexdigest()


def _brackets_close(segment: str) -> bool:
    """True when every [ opens a class that fnmatch closes and no ] stands alone.

    As in fnmatch, a class may start with ! and then ] as a member, and ends at the next ]; so [] and [!]
    never close, while []a] and [!]a] are classes.
    """
    index = 0
    while index < len(segment):
        if segment[index] == "]":
            return False
        if segment[index] == "[":
            index += 1
            if segment[index:index + 1] == "!":
                index += 1
            if segment[index:index + 1] == "]":
                index += 1
            close = segment.find("]", index)
            if close < 0:
                return False
            index = close
        index += 1
    return True


def _segments_problem(segments: list[str], *, windows: bool = False, glob: bool = False) -> str | None:
    """Why these path segments are not in the accepted format, or None."""
    allowed = GLOB_SEGMENT if glob else SEGMENT
    for segment in segments:
        if not segment:
            return "has an empty segment (a repeated or trailing separator)"
        if segment in {".", ".."}:
            return f"has a {segment!r} segment"
        if not allowed.fullmatch(segment):
            extra = ", *, ?, [, ], !" if glob else ""
            return f"segment {segment!r} uses characters other than letters, digits, ., _, -, ~{extra}"
        if glob and not _brackets_close(segment):
            return f"segment {segment!r} has an unmatched [ or ]"
        # Windows drops a trailing dot, maps NUL, COM1 and the like to devices in every folder, and
        # reads NAME~1 as an 8.3 short name for a longer one.
        if windows and (segment.endswith(".") or "~" in segment or
                        segment.split(".")[0].upper() in WINDOWS_DEVICE_NAMES):
            return f"Windows segment {segment!r} ends in ., contains ~, or names a device"
    return None


def repo_path_problem(path: object, *, pattern: bool = False) -> str | None:
    """Why a changed path (or, with pattern=True, a protected-input pattern) is not accepted, or None."""
    if not isinstance(path, str) or not path:
        return "is not a nonempty string"
    if path.startswith("/"):
        return "must be repository-relative"
    if pattern and path.endswith("/"):
        path = path[:-1]
    return _segments_problem(path.split("/"), glob=pattern)


def batch_path_problem(path: object) -> str | None:
    """Why a frozen-batch file path is not accepted, or None."""
    if isinstance(path, str) and WINDOWS_DRIVE_PATH.match(path):
        return _segments_problem(path[3:].split("\\"), windows=True)
    if isinstance(path, str) and path.startswith("/"):
        return _segments_problem(path[1:].split("/"))
    if isinstance(path, str) and path.startswith("~"):
        # A shell would expand ~ or ~user to a home directory, so ~/.config is not repository-relative.
        return "starts with ~, which reads as a home directory"
    return repo_path_problem(path)


def destination_problem(destination: object) -> str | None:
    """Why a deployment destination is not in the accepted format, or None."""
    if not isinstance(destination, str) or not destination:
        return "is not a nonempty string"
    if destination == "/":
        return None
    if destination.startswith("/"):
        return _segments_problem(destination[1:].split("/"))
    if WINDOWS_DRIVE_PATH.match(destination):
        return None if destination == destination[:3] else _segments_problem(destination[3:].split("\\"), windows=True)
    if destination.startswith("\\\\"):
        parts = destination[2:].split("\\")
        return "UNC path needs \\\\server\\share" if len(parts) < 2 else _segments_problem(parts, windows=True)
    match = URL_FORM.fullmatch(destination)
    if not match:
        return "is not an absolute path, C:\\ path, \\\\server\\share path, or lowercase scheme://host/path URL"
    scheme, authority, path = match.groups()
    if scheme == "file":
        return "file: URLs are written as the plain path"
    if path is not None:
        problem = _segments_problem(path[1:].split("/"))
        if problem:
            return f"URL path {problem}"
    if not authority:
        if scheme in HOST_REQUIRED_SCHEMES:
            return f"{scheme}: URL needs a host"
        return "URL without a host needs a path" if path is None else None
    if "@" in authority:
        return "URL has user info"
    if authority.startswith("["):
        host, bracket, after = authority[1:].partition("]")
        if not bracket:
            return "URL host is missing the closing ] of its IPv6 address"
        port = after[1:] if after.startswith(":") else None
        if after and port is None:
            return "URL has text after the IPv6 address"
        try:
            address = ipaddress.IPv6Address(host)
        except ValueError:
            return "URL host is not an IPv6 address"
        if "%" in host or address.ipv4_mapped is not None or address.compressed != host:
            return f"IPv6 host must be written in compressed form, without a zone or IPv4 mapping ({address.compressed})"
    else:
        host, colon, port = authority.partition(":")
        port = port if colon else None
        if not HOST_NAME.fullmatch(host):
            return "URL host must be lowercase letters, digits, - and ."
        if NUMERIC_LABEL.fullmatch(host.rsplit(".", 1)[-1]) and not IPV4.fullmatch(host):
            # Parsers read 127.1, 2130706433 and 0x7f000001 as 127.0.0.1.
            return "numeric URL host must be a dotted-quad IPv4 address"
    if port is not None:
        if not port.isascii() or not port.isdigit() or port.startswith("0") or len(port) > 5 or int(port) > 65535:
            return "URL port must be a number from 1 to 65535 without leading zeros"
        if int(port) == DEFAULT_PORTS.get(scheme):
            return f"URL port {port} is the {scheme} default and is left out"
    return None


def _batch_path_key(path: str) -> str:
    # Windows paths are case-insensitive, so C:\App and C:\app are one file.
    return path.casefold() if WINDOWS_DRIVE_PATH.match(path) else path


def _destination_key(destination: str) -> str:
    # Drive and UNC paths are case-insensitive; every other accepted destination has one spelling.
    windows = WINDOWS_DRIVE_PATH.match(destination) or destination.startswith("\\\\")
    return destination.casefold() if windows else destination


@functools.lru_cache(maxsize=1024)
def _pattern_spellings(pattern: str) -> frozenset[str] | None:
    """Globs a protected pattern stands for, or None if it has too many ** segments to expand."""
    segments = pattern.split("/")
    recursive = [index for index, segment in enumerate(segments) if segment == "**"]
    if len(recursive) > MAX_PATTERN_EXPANSIONS:
        return None
    spellings: set[str] = set()
    # A ** segment also stands for no directories at all.
    for dropped in itertools.product((False, True), repeat=len(recursive)):
        skip = {index for index, drop in zip(recursive, dropped) if drop}
        spellings.add("/".join(segment for index, segment in enumerate(segments) if index not in skip))
    return frozenset(spellings)


@functools.lru_cache(maxsize=1024)
def _protected_matcher(pattern: str) -> tuple[frozenset[str], tuple[str, ...], re.Pattern[str]] | None:
    """Literal paths, subtree prefixes, and one compiled glob for a pattern; None protects every path."""
    spellings = _pattern_spellings(pattern)
    if spellings is None:
        return None
    literals: set[str] = set()
    prefixes: list[str] = []
    globs: list[str] = []
    for spelling in spellings:
        base = spelling.rstrip("/")
        if not base:
            return None
        literals.update({spelling, base})
        prefixes.append(base + "/")
        globs += [fnmatch.translate(base), fnmatch.translate(base + "/*")]
    return frozenset(literals), tuple(prefixes), re.compile("|".join(f"(?:{glob})" for glob in globs))


def _matches_protected(path: str, matcher: tuple[frozenset[str], tuple[str, ...], re.Pattern[str]] | None) -> bool:
    """Literal path, fnmatch glob (where * also crosses / and ** may be empty), or a / subtree."""
    if matcher is None:
        return True
    literals, prefixes, glob = matcher
    return path in literals or path.startswith(prefixes) or glob.match(path) is not None


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
        # A path outside the accepted format (./services/x, a quoted name) could slip past a pattern.
        isinstance(changed_paths, list) and all(repo_path_problem(path) is None for path in changed_paths) and
        isinstance(deployment_input_paths, list) and deployment_input_paths and
        all(repo_path_problem(path, pattern=True) is None for path in deployment_input_paths)):
        # Build every matcher once per call; a per-pair cache lookup thrashes once patterns outnumber it.
        matchers = [_protected_matcher(pattern) for pattern in deployment_input_paths]
        if any(_matches_protected(path, matcher) for path in changed_paths for matcher in matchers):
            return "protected_change"
        return "known_additive"
    return "unknown"


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    """Reject duplicate JSON keys, which different readers resolve differently."""
    keys = [key for key, _value in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key in evidence JSON")
    return dict(pairs)


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
            evidence = json.load(handle, object_pairs_hook=_unique_keys)
    except (KeyError, OSError, ValueError, TypeError, RecursionError, RuntimeError):
        # RuntimeError covers Path.resolve() symlink loops on Python 3.11 and 3.12.
        return None
    if not (isinstance(evidence, dict) and evidence.get("workflowVersion") == 3 and
            evidence.get("workflowId") == phase and isinstance(evidence.get("records"), list)):
        return None
    if any(not isinstance(record, dict) or not isinstance(record.get("taskId"), str) or
           "taskStatus" not in record or not isinstance(record["taskStatus"], (str, type(None)))
           for record in evidence["records"]):
        return None
    return evidence


def _source_only_problem(data: dict, path: object) -> str | None:
    """Validators and installed scripts must be files the reviewer saw at the source, not coordinator records."""
    records = f"agent-work/{data.get('phase')}/"
    if isinstance(path, str) and path.startswith(records):
        return f"is under {records}; validators and installed scripts must be read from the reviewed source"
    return None


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
    required_batch = {
        "deploymentSourceSha",
        "deployableArtifactSha256",
        "deploymentConfiguration",
        "validators",
        "rollbackArtifact",
        "installedScripts",
        "deploymentTargets",
    }
    if not required_batch.issubset(batch) or batch.get("deploymentSourceSha") != source:
        return "GATED"
    if not isinstance(batch.get("deployableArtifactSha256"), str) or not SHA256.fullmatch(batch["deployableArtifactSha256"]):
        return "GATED"
    frozen_hashes: dict[str, str] = {}
    for key in BATCH_PATH_LISTS:
        entries = batch[key]
        if not isinstance(entries, list) or any(
            not isinstance(entry, dict) or batch_path_problem(entry.get("path")) is not None or
            not isinstance(entry.get("sha256"), str) or not SHA256.fullmatch(entry["sha256"])
            for entry in entries
        ) or len({_batch_path_key(entry["path"]) for entry in entries}) != len(entries):
            # A repeated path is ambiguous about which bytes were frozen.
            return "GATED"
        for entry in entries:
            # One file may serve two roles, but never with two different contents.
            if frozen_hashes.setdefault(_batch_path_key(entry["path"]), entry["sha256"]) != entry["sha256"]:
                return "GATED"
    if not batch["validators"]:
        # A batch frozen without any validator has proven nothing about the candidate.
        return "GATED"
    if any(_source_only_problem(data, entry["path"]) for key in SOURCE_ONLY_BATCH_LISTS for entry in batch[key]):
        return "GATED"
    targets = batch["deploymentTargets"]
    if not isinstance(targets, list) or not targets:
        return "GATED"
    for target in targets:
        if (not isinstance(target, dict) or
            destination_problem(target.get("destination")) is not None or
            "mode" not in target):
            return "GATED"
        mode = target["mode"]
        if mode is not None and (not isinstance(mode, str) or not mode):
            return "GATED"
        for key in ("owner", "group"):
            value = target.get(key)
            if key in target and value is not None and (not isinstance(value, str) or not value):
                return "GATED"
    if len({_destination_key(target["destination"]) for target in targets}) != len(targets):
        return "GATED"
    rollback = batch["rollbackArtifact"]
    if not isinstance(rollback, dict) or any(not isinstance(rollback.get(key), str) or not rollback[key]
                                              for key in ("identity", "provenance")):
        return "GATED"
    try:
        if batch_fingerprint(batch) != fingerprint:
            return "GATED"
    except (TypeError, ValueError, RecursionError):
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
    protected = divergence.get("deploymentInputPaths")
    # An empty declaration stays invalid; batch files only add to a real one.
    if isinstance(protected, list) and protected:
        protected = protected + [entry["path"] for key in BATCH_PATH_LISTS for entry in batch[key]
                                 if repo_path_problem(entry["path"]) is None]
    if classify_divergence(
        identical=divergence.get("identical") is True,
        object_present=divergence.get("objectPresent") is True,
        ancestry_proven=divergence.get("ancestryProven") is True,
        changed_paths_inspected=divergence.get("changedPathsInspected") is True,
        deployment_inputs_unchanged=divergence.get("deploymentInputsUnchanged") is True,
        destructive=divergence.get("destructive") is True,
        changed_paths=divergence.get("changedPaths"),
        deployment_input_paths=protected,
    ) not in {"identical", "known_additive"}:
        return "GATED"
    live_attempts = [item for item in records[readiness_index + 1:] if isinstance(item, dict)
                     and item.get("taskId") == live_id]
    if _attempts_unsuccessful(live_attempts):
        # A failed attempt may have left public state behind; another attempt needs fresh readiness.
        return "GATED"
    if not live_attempts:
        return "PREVIEW"
    attempt = live_attempts[-1]
    return "READY" if (isinstance(attempt.get("approvalReference"), str) and
                       attempt["approvalReference"].strip() and
                       attempt.get("deploymentSourceSha") == source and
                       attempt.get("frozenBatchFingerprint") == fingerprint and
                       attempt.get("taskStatus") not in ({"failed", "skipped"} if allow_completed else
                                                         {"failed", "complete", "passed", "skipped"})) else "PREVIEW"


def evidence_format_problems(data: dict, evidence_path: Path | None = None) -> list[str]:
    """Locations in the latest readiness record that are not in the accepted format, as readable messages."""
    deployment = data.get("deployment")
    records_data = _read_evidence(data, evidence_path) if isinstance(deployment, dict) else None
    if records_data is None:
        return []
    readiness = [record for record in records_data["records"] if record.get("taskId") == deployment.get("readiness_task")]
    if not readiness:
        return []
    record, problems = readiness[-1], []
    batch = record.get("frozenBatch") if isinstance(record.get("frozenBatch"), dict) else {}
    for key in BATCH_PATH_LISTS:
        for entry in batch.get(key) if isinstance(batch.get(key), list) else []:
            path = entry.get("path") if isinstance(entry, dict) else None
            if (problem := batch_path_problem(path)) is not None:
                problems.append(f"frozenBatch.{key} path {path!r} {problem}")
            elif key in SOURCE_ONLY_BATCH_LISTS and (problem := _source_only_problem(data, path)) is not None:
                problems.append(f"frozenBatch.{key} path {path!r} {problem}")
    for target in batch.get("deploymentTargets") if isinstance(batch.get("deploymentTargets"), list) else []:
        destination = target.get("destination") if isinstance(target, dict) else None
        if (problem := destination_problem(destination)) is not None:
            problems.append(f"deploymentTargets destination {destination!r} {problem}")
    divergence = record.get("gitDivergence") if isinstance(record.get("gitDivergence"), dict) else {}
    for key, pattern in (("changedPaths", False), ("deploymentInputPaths", True)):
        for path in divergence.get(key) if isinstance(divergence.get(key), list) else []:
            if (problem := repo_path_problem(path, pattern=pattern)) is not None:
                problems.append(f"gitDivergence.{key} entry {path!r} {problem}")
    return problems


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


def rollback_not_needed(task_id: str, data: dict, evidence_path: Path | None = None) -> bool:
    """A task that runs after a failed live attempt waits while that attempt recorded no live change."""
    deployment = data.get("deployment")
    task = data.get("tasks", {}).get(task_id, {})
    required = task.get("required_status") if isinstance(task, dict) else None
    if data.get("workflow_version") != 3 or not isinstance(deployment, dict) or not isinstance(required, dict):
        return False
    live_id = deployment.get("live_task")
    if not isinstance(live_id, str) or required.get(live_id) != "failed":
        return False
    records_data = _read_evidence(data, evidence_path)
    if records_data is None:
        return False
    live_records = [record for record in records_data["records"] if record.get("taskId") == live_id]
    # Only an explicit false counts; true, null, a missing field or any other value leaves the rollback to the contract.
    return bool(live_records) and live_records[-1].get("liveStateChanged") is False


def task_ready(task_id: str, data: dict, evidence_path: Path | None = None) -> bool:
    if not _dependencies_ready(task_id, data):
        return False
    if rollback_not_needed(task_id, data, evidence_path):
        return False
    task = data["tasks"][task_id]
    if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment":
        return live_gate_state(data, evidence_path) == "READY"
    if data.get("workflow_version") == 3 and task.get("kind") == "final_reconciliation":
        return final_reconciliation_ready(data, evidence_path)
    return True



# Live-attempt statuses that do not mean the attempt ended badly; anything else closes the gate.
LIVE_ATTEMPT_OK_STATUSES = {None, "pending", "blocked", "in_progress", "complete", "passed"}


LIVE_ATTEMPT_NOT_STARTED = {None, "pending", "blocked"}


def _attempts_unsuccessful(attempts: list[dict]) -> bool:
    """True when any live record reports a non-PASS acceptance or an unknown status, or an attempt
    that reached in_progress later falls back to a not-started status (it stopped mid-run)."""
    started = False
    for record in attempts:
        status = record.get("taskStatus")
        if record.get("runtimeAcceptance") not in (None, "PASS"):
            return True
        if not (status is None or isinstance(status, str)) or status not in LIVE_ATTEMPT_OK_STATUSES:
            return True
        if started and status in LIVE_ATTEMPT_NOT_STARTED:
            return True
        started = started or status == "in_progress"
    return False


def _live_attempts_since_readiness(data: dict, evidence_path: Path | None = None) -> list[dict]:
    """Live records after the latest readiness record, oldest first."""
    records_data = _read_evidence(data, evidence_path)
    if records_data is None:
        return []
    deployment = data["deployment"]
    attempts: list[dict] = []
    for record in records_data["records"]:
        if not isinstance(record, dict):
            continue
        if record.get("taskId") == deployment["readiness_task"]:
            attempts = []
        elif record.get("taskId") == deployment["live_task"]:
            attempts.append(record)
    return attempts


def _live_attempt_finished(data: dict, evidence_path: Path | None = None) -> bool:
    """True when the latest live record since the latest readiness record reports a finished attempt."""
    attempts = _live_attempts_since_readiness(data, evidence_path)
    return bool(attempts) and attempts[-1].get("taskStatus") in DEFAULT_DEPENDENCY_SUCCESS_STATUSES


def live_task_label(task_id: str, data: dict, evidence_path: Path | None = None) -> str:
    """GATED, PREVIEW, READY, or DONE for a v3 live task, as the task view, --all and --ready show it."""
    if (data.get("status", {}).get(task_id) in DEFAULT_DEPENDENCY_SUCCESS_STATUSES or
            _live_attempt_finished(data, evidence_path)):
        # A finished live task is never offered for another preview or dispatch.
        return "DONE" if final_reconciliation_ready(data, evidence_path) else "GATED"
    gate = live_gate_state(data, evidence_path)
    if gate == "READY" and not task_ready(task_id, data, evidence_path):
        return "GATED"
    return gate


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
    gate = live_task_label(task_id, data) if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment" else None

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
        if gate == "DONE":
            print("This live task is complete with runtime acceptance PASS for the readied source and fingerprint; "
                  "do not dispatch it again. Another live change needs fresh readiness and a new approval.")
        elif gate == "GATED":
            print("Do not dispatch this live task; its required evidence or dependency gate is closed.")
            if status in DEFAULT_DEPENDENCY_SUCCESS_STATUSES:
                print(f"Its status is {status}, but no runtime acceptance PASS is recorded for the readied source and fingerprint.")
            elif _attempts_unsuccessful(_live_attempts_since_readiness(data)):
                print("The latest live attempt failed; another attempt needs fresh readiness and a new approval.")
            for problem in evidence_format_problems(data):
                print(f"Format problem: {problem}")
        elif gate == "PREVIEW":
            print("Approval preview only; do not dispatch or mutate live state.")
        else:
            print("Coordinator handoff only: verify actual human approval, direct Git refs, and fresh live drift before dispatch.")
        return
    if rollback_not_needed(task_id, data):
        print("The latest live attempt recorded liveStateChanged: false, so no rollback is needed. Do not dispatch "
              "this task; record that no rollback was needed and ask the owner how to continue.")
        return
    print(
        f"In the adopting repository, follow agent-work/README.md and execute "
        f"{phase.replace('phase', 'Phase ')} Task {task_id}. Stop at its completion boundary."
    )


def print_all(data: dict) -> None:
    for task_id, task in data.get("tasks", {}).items():
        status = data.get("status", {}).get(task_id, "unknown")
        if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment":
            ready = live_task_label(task_id, data)
        else:
            ready = "READY" if task_ready(task_id, data) else "BLOCKED"
        print(f"{task_id:>2}  {ready:<7} {status:<12} {task['name']}")


def print_ready(data: dict) -> None:
    found = False
    for task_id, task in data.get("tasks", {}).items():
        status = data.get("status", {}).get(task_id, "unknown")
        if data.get("workflow_version") == 3 and task.get("kind") == "live_deployment":
            gate = live_task_label(task_id, data)
            if gate == "PREVIEW" and _dependencies_ready(task_id, data) and status not in {"complete", "passed", "skipped"}:
                found = True
                print(f"{task_id}  {task['name']}  ->  ELIGIBLE FOR APPROVAL PREVIEW; not ready for live mutation")
            elif gate == "READY" and status not in {"complete", "passed", "skipped"}:
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
    try:
        status = main()
        if sys.stdout is not None:
            sys.stdout.flush()
    except BrokenPipeError:
        # The reader closed the pipe early (for example `| head`): exit quietly, without a traceback.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
    sys.exit(status)
