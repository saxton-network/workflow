"""Local JSON Mission Control. Actor arguments are trusted operator assertions."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from .contracts import Rejected, decode
from .git_state import GitObserver
from .permissions import HUMAN, COORDINATOR
from .planner import propose
from .runtime import Runtime
from .store import Store


def parser():
    p = argparse.ArgumentParser(description="AItism experimental mock-only runtime")
    p.add_argument("--store", type=Path, default=Path(".aitism/runtime.sqlite"))
    p.add_argument("--repository", type=Path, default=Path.cwd())
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("propose", "demo"):
        cmd = commands.add_parser(name)
        cmd.add_argument("workflow_id")
        cmd.add_argument("--objective", required=True)
        if name == "demo":
            cmd.add_argument("--simulate-approval", action="store_true", required=True,
                             help="Record explicitly synthetic approval; never human/live evidence")
    create = commands.add_parser("create")
    create.add_argument("plan", type=Path)
    create.add_argument("--actor", required=True)
    for name in ("inspect", "journal", "approve", "enroll", "advance", "claim", "heartbeat", "checkpoint", "recover", "retry", "cancel"):
        cmd = commands.add_parser(name)
        cmd.add_argument("workflow_id")
        if name not in {"inspect", "journal"}:
            cmd.add_argument("--actor", required=True)
        if name == "approve":
            cmd.add_argument("--plan-hash", required=True)
            cmd.add_argument("--reference", required=True)
        if name == "enroll":
            cmd.add_argument("--agent", required=True)
            cmd.add_argument("--role", required=True, choices=("builder", "reviewer", "validator"))
            cmd.add_argument("--task", required=True)
            cmd.add_argument("--parent")
        if name in {"claim", "heartbeat", "checkpoint", "retry"}:
            cmd.add_argument("--task", required=True)
        if name in {"heartbeat", "checkpoint"}:
            cmd.add_argument("--lease", required=True)
        if name == "checkpoint":
            cmd.add_argument("--data", type=Path, required=True)
    return p


def run(args):
    git = GitObserver(args.repository)
    if args.command in {"propose", "demo"}:
        sha, branch = git.observe()
        if branch != "experimental/features":
            raise Rejected("experimental/features checkout required")
        plan = propose(args.objective, sha, args.workflow_id)
        if args.command == "propose":
            return plan
    runtime = Runtime(Store(args.store), git,
                      clock=(lambda: 1000) if args.command == "demo" else None)
    if args.command == "create":
        return runtime.create(decode(args.plan.read_text()), actor=args.actor)
    if args.command == "demo":
        state = runtime.create(plan, actor=HUMAN)
        for role, task in (("builder", "build"), ("reviewer", "review"), ("validator", "validate")):
            runtime.enroll(args.workflow_id, f"mock-{role}", role, task, actor=HUMAN)
        runtime.approve(args.workflow_id, state["plan_hash"], "SIMULATED-DEMO-APPROVAL", actor=HUMAN)
        for _ in range(3):
            view = runtime.advance(args.workflow_id, actor=COORDINATOR)
        if view["state"]["status"] != "completed":
            raise Rejected("demo did not complete")
        return {"simulation": True, "synthetic_approval": True,
                "implementation_independently_reviewed": False,
                "plan": plan, "mission_control": view,
                "event_history": [{k: v for k, v in event.items() if k != "state"}
                                  for event in runtime.store.events(args.workflow_id)]}
    wid = args.workflow_id
    if args.command == "inspect":
        return runtime.inspect(wid)
    if args.command == "journal":
        return runtime.store.events(wid)
    if args.command == "approve":
        return runtime.approve(wid, args.plan_hash, args.reference, actor=args.actor)
    if args.command == "enroll":
        return runtime.enroll(wid, args.agent, args.role, args.task, actor=args.actor, parent=args.parent)
    if args.command == "advance":
        return runtime.advance(wid, actor=args.actor)
    if args.command == "claim":
        return runtime.claim(wid, args.task, actor=args.actor)
    if args.command == "heartbeat":
        return runtime.heartbeat(wid, args.task, args.lease, actor=args.actor)
    if args.command == "checkpoint":
        return runtime.checkpoint(wid, args.task, args.lease, decode(args.data.read_text()), actor=args.actor)
    if args.command == "recover":
        return runtime.recover(wid, actor=args.actor)
    if args.command == "retry":
        return runtime.retry(wid, args.task, actor=args.actor)
    if args.command == "cancel":
        return runtime.cancel(wid, actor=args.actor)
    raise Rejected("unknown operation")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = run(args)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False), flush=True)
        return 0
    except BrokenPipeError:
        with open(os.devnull, "w") as sink:
            os.dup2(sink.fileno(), sys.stdout.fileno())
        return 1
    except (Rejected, OSError, sqlite3.Error, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({"verdict": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2
