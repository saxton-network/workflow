from __future__ import annotations

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "agent-task.py"
SPEC = importlib.util.spec_from_file_location("agent_task", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load scripts/agent-task.py")
agent_task = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent_task)


class WorkflowV3Tests(unittest.TestCase):
    SOURCE = "a" * 40
    REVIEW_RESULT = "b" * 40

    def task(self, kind: str, deps: list[str], **fields: object) -> dict:
        return {
            "name": kind,
            "kind": kind,
            "file": f"agent-work/example/{kind}.md",
            "branch": f"example/{kind}",
            "depends_on": deps,
            **fields,
        }

    def deploy_manifest(self, *, promotion: bool = True) -> dict:
        tasks = {
            "G": self.task("integration", []),
            "H": self.task("independent_review", ["G"], rerun_after="I"),
            "I": self.task(
                "repair",
                ["H"],
                conditional="review_findings_exist",
                required_status={"H": "findings"},
            ),
            "R": self.task("release_readiness", ["H"], required_status={"H": "passed"}),
            "J": self.task("live_deployment", ["R"], human_gate="live-change-approval"),
            "K": self.task("final_reconciliation", ["J"]),
        }
        status = {
            "G": "complete",
            "H": "passed",
            "I": "conditional",
            "R": "complete",
            "J": "blocked",
            "K": "blocked",
        }
        deployment = {
            "implementation_tasks": ["G"],
            "review_task": "H",
            "authority_remote": "origin",
            "authority_ref": "refs/heads/main",
            "readiness_task": "R",
            "live_task": "J",
            "final_reconciliation_task": "K",
        }
        if promotion:
            tasks["P"] = self.task(
                "authority_promotion",
                ["H"],
                required_status={"H": "passed"},
            )
            tasks["R"]["depends_on"] = ["H", "P"]
            status["P"] = "complete"
            deployment["authority_task"] = "P"

        return {
            "phase": "example",
            "workflow_version": 3,
            "workflow": {
                "evidence_manifest": "agent-work/example/evidence.json",
                "human_gate_tasks": ["J"],
                "terminal_task": "K",
            },
            "status": status,
            "tasks": tasks,
            "deployment": deployment,
        }

    def evidence(self, *, verdict: str = "PASS", approved: bool = True) -> dict:
        batch = {
            "deploymentSourceSha": self.SOURCE,
            "deployableArtifactSha256": "c" * 64,
            "deploymentConfiguration": [{"path": "deploy/config", "sha256": "d" * 64}],
            "validators": [{"path": "scripts/check.py", "sha256": "e" * 64}],
            "rollbackArtifact": {"identity": "artifact:rollback", "provenance": "verified"},
            "installedScripts": [{"path": "scripts/install.sh", "sha256": "f" * 64}],
            "deploymentTargets": [
                {
                    "destination": "/srv/example/app",
                    "mode": "0755",
                    "owner": "example",
                    "group": "example",
                }
            ],
        }
        fingerprint = agent_task.batch_fingerprint(batch)
        records = [
            {"taskId": "G", "taskStatus": "complete", "candidateSha": self.SOURCE},
            {
                "taskId": "H",
                "taskStatus": "passed",
                "candidateSha": self.REVIEW_RESULT,
                "deploymentSourceSha": self.SOURCE,
            },
            {
                "taskId": "R",
                "taskStatus": "complete",
                "readinessVerdict": verdict,
                "deploymentSourceSha": self.SOURCE,
                "frozenBatch": batch,
                "frozenBatchFingerprint": fingerprint,
                "gitDivergence": {
                    "identical": True,
                    "authoritySha": self.SOURCE,
                    "otherSha": self.SOURCE,
                },
            },
        ]
        if approved:
            records.append(
                {
                    "taskId": "J",
                    "taskStatus": "blocked",
                    "approvalReference": "approval-1",
                    "deploymentSourceSha": self.SOURCE,
                    "frozenBatchFingerprint": fingerprint,
                }
            )
        return {"workflowVersion": 3, "workflowId": "example", "records": records}

    def gate(self, manifest: dict, evidence: dict) -> str:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / manifest["workflow"]["evidence_manifest"]
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(evidence), encoding="utf-8")
            with patch.object(agent_task, "ROOT", root):
                return agent_task.live_gate_state(manifest)

    def test_v2_compatibility_is_left_untouched(self) -> None:
        agent_task.validate_manifest({"workflow_version": 2})

    def test_v3_non_deployment_graph_is_valid(self) -> None:
        manifest = self.deploy_manifest()
        del manifest["deployment"]
        manifest["tasks"] = {
            "G": manifest["tasks"]["G"],
            "H": manifest["tasks"]["H"],
            "I": manifest["tasks"]["I"],
        }
        manifest["status"] = {"G": "complete", "H": "passed", "I": "conditional"}
        manifest["workflow"]["terminal_task"] = "H"
        manifest["workflow"].pop("human_gate_tasks")
        agent_task.validate_manifest(manifest)

    def test_v3_requires_known_terminal_task(self) -> None:
        manifest = self.deploy_manifest()
        manifest["workflow"].pop("terminal_task")
        with self.assertRaisesRegex(SystemExit, "terminal_task"):
            agent_task.validate_manifest(manifest)

        manifest = self.deploy_manifest()
        manifest["workflow"]["terminal_task"] = "Z"
        with self.assertRaisesRegex(SystemExit, "terminal_task"):
            agent_task.validate_manifest(manifest)

    def test_deployment_terminal_must_be_final_reconciliation(self) -> None:
        for terminal in ("R", "J"):
            manifest = self.deploy_manifest()
            manifest["workflow"]["terminal_task"] = terminal
            with self.subTest(terminal=terminal), self.assertRaisesRegex(
                SystemExit, "final_reconciliation_task"
            ):
                agent_task.validate_manifest(manifest)

    def test_deployment_requires_authority_even_without_promotion(self) -> None:
        manifest = self.deploy_manifest(promotion=False)
        agent_task.validate_manifest(manifest)

        for missing in (
            ("authority_remote",),
            ("authority_ref",),
            ("authority_remote", "authority_ref"),
        ):
            broken = copy.deepcopy(manifest)
            for key in missing:
                broken["deployment"].pop(key)
            with self.subTest(missing=missing), self.assertRaisesRegex(SystemExit, "authority"):
                agent_task.validate_manifest(broken)

    def test_authority_values_must_be_nonempty_strings(self) -> None:
        for key, value in (
            ("authority_remote", ""),
            ("authority_ref", ""),
            ("authority_remote", 7),
            ("authority_ref", 7),
        ):
            manifest = self.deploy_manifest()
            manifest["deployment"][key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(SystemExit, "authority"):
                agent_task.validate_manifest(manifest)

    def test_review_and_authority_cannot_be_bypassed(self) -> None:
        edits = (
            lambda m: m["tasks"]["H"].update(depends_on=[]),
            lambda m: m["tasks"]["P"].update(depends_on=[]),
            lambda m: m["tasks"]["R"].update(depends_on=["P"]),
            lambda m: m["tasks"]["R"].update(required_status={"H": "findings"}),
            lambda m: m["tasks"]["J"].update(depends_on=["H"]),
        )
        for edit in edits:
            manifest = self.deploy_manifest()
            edit(manifest)
            with self.subTest(edit=edit), self.assertRaises(SystemExit):
                agent_task.validate_manifest(manifest)

    def test_human_gate_and_final_order_are_required(self) -> None:
        edits = (
            lambda m: m["tasks"]["J"].pop("human_gate"),
            lambda m: m["workflow"].update(human_gate_tasks=[]),
            lambda m: m["tasks"]["K"].update(depends_on=[]),
        )
        for edit in edits:
            manifest = self.deploy_manifest()
            edit(manifest)
            with self.subTest(edit=edit), self.assertRaises(SystemExit):
                agent_task.validate_manifest(manifest)

    def test_readiness_fail_and_unknown_gate_live(self) -> None:
        manifest = self.deploy_manifest()
        for verdict in ("FAIL", "UNKNOWN"):
            with self.subTest(verdict=verdict):
                self.assertEqual(self.gate(manifest, self.evidence(verdict=verdict)), "GATED")

    def test_pass_without_approval_is_preview_only(self) -> None:
        manifest = self.deploy_manifest()
        self.assertEqual(self.gate(manifest, self.evidence(approved=False)), "PREVIEW")

    def test_matching_approval_record_makes_helper_ready(self) -> None:
        manifest = self.deploy_manifest()
        self.assertEqual(self.gate(manifest, self.evidence(approved=True)), "READY")

    def test_gated_handoff_never_instructs_execution(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            agent_task.print_task("example", "J", self.deploy_manifest())
        self.assertIn("Do not dispatch", output.getvalue())
        self.assertNotIn("execute Phase", output.getvalue())

    def test_review_findings_activate_repair_then_rereview(self) -> None:
        manifest = self.deploy_manifest()
        manifest["status"].update(H="findings", I="conditional", P="blocked", R="blocked")
        self.assertTrue(agent_task.task_ready("I", manifest))
        self.assertFalse(agent_task.task_ready("H", manifest))
        manifest["status"]["I"] = "complete"
        self.assertTrue(agent_task.task_ready("H", manifest))

    def test_final_reconciliation_requires_runtime_acceptance(self) -> None:
        manifest = self.deploy_manifest()
        manifest["status"]["J"] = "complete"
        evidence = self.evidence()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / manifest["workflow"]["evidence_manifest"]
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(evidence), encoding="utf-8")
            with patch.object(agent_task, "ROOT", root):
                self.assertFalse(agent_task.task_ready("K", manifest))
                evidence["records"][3].update(taskStatus="complete", runtimeAcceptance="FAIL")
                path.write_text(json.dumps(evidence), encoding="utf-8")
                self.assertFalse(agent_task.task_ready("K", manifest))
                evidence["records"][3]["runtimeAcceptance"] = "PASS"
                path.write_text(json.dumps(evidence), encoding="utf-8")
                self.assertTrue(agent_task.task_ready("K", manifest))

    def test_invalid_versions_kinds_cycles_and_stage_aliases_fail(self) -> None:
        edits = (
            lambda m: m.update(workflow_version=4),
            lambda m: m.update(workflow_version="3"),
            lambda m: m["tasks"]["R"].update(kind="unknown"),
            lambda m: m["tasks"]["G"].update(depends_on=["K"]),
            lambda m: m["deployment"].update(live_task="R"),
        )
        for edit in edits:
            manifest = self.deploy_manifest()
            edit(manifest)
            with self.subTest(edit=edit), self.assertRaises(SystemExit):
                agent_task.validate_manifest(manifest)

    def test_result_commit_cannot_replace_source(self) -> None:
        manifest = self.deploy_manifest()
        evidence = self.evidence()
        evidence["records"][2]["deploymentSourceSha"] = self.REVIEW_RESULT
        evidence["records"][2]["frozenBatch"]["deploymentSourceSha"] = self.REVIEW_RESULT
        evidence["records"][2]["frozenBatchFingerprint"] = agent_task.batch_fingerprint(
            evidence["records"][2]["frozenBatch"]
        )
        self.assertEqual(self.gate(manifest, evidence), "GATED")

    def test_frozen_batch_or_approval_change_invalidates_gate(self) -> None:
        manifest = self.deploy_manifest()
        evidence = self.evidence()
        evidence["records"][2]["frozenBatch"]["validators"][0]["sha256"] = "0" * 64
        self.assertEqual(self.gate(manifest, evidence), "GATED")

        evidence = self.evidence()
        evidence["records"][3]["frozenBatchFingerprint"] = "0" * 64
        self.assertEqual(self.gate(manifest, evidence), "PREVIEW")

    def test_evidence_identity_must_match_workflow(self) -> None:
        manifest = self.deploy_manifest()
        evidence = self.evidence()
        evidence["workflowId"] = "foreign"
        self.assertEqual(self.gate(manifest, evidence), "GATED")

    def test_frozen_batch_requires_explicit_deployment_targets(self) -> None:
        manifest = self.deploy_manifest()

        evidence = self.evidence()
        del evidence["records"][2]["frozenBatch"]["deploymentTargets"]
        evidence["records"][2]["frozenBatchFingerprint"] = agent_task.batch_fingerprint(
            evidence["records"][2]["frozenBatch"]
        )
        self.assertEqual(self.gate(manifest, evidence), "GATED")

        for targets in (
            [],
            [{"destination": "/srv/example/app"}],
            [{"destination": "", "mode": "0755"}],
            [{"destination": "/srv/example/app", "mode": ""}],
            [{"destination": "/srv/example/app", "mode": 755}],
        ):
            evidence = self.evidence()
            evidence["records"][2]["frozenBatch"]["deploymentTargets"] = targets
            evidence["records"][2]["frozenBatchFingerprint"] = agent_task.batch_fingerprint(
                evidence["records"][2]["frozenBatch"]
            )
            with self.subTest(targets=targets):
                self.assertEqual(self.gate(manifest, evidence), "GATED")

    def test_batch_fingerprint_is_order_independent_for_declared_lists(self) -> None:
        batch = self.evidence()["records"][2]["frozenBatch"]
        batch["deploymentConfiguration"].append(
            {"path": "deploy/other", "sha256": "1" * 64}
        )
        batch["validators"].append(
            {"path": "scripts/other-check.py", "sha256": "2" * 64}
        )
        batch["installedScripts"].append(
            {"path": "scripts/other-install.sh", "sha256": "3" * 64}
        )
        batch["deploymentTargets"].append(
            {"destination": "/srv/example/worker", "mode": None}
        )

        reordered = copy.deepcopy(batch)
        for key in (
            "deploymentConfiguration",
            "validators",
            "installedScripts",
            "deploymentTargets",
        ):
            reordered[key].reverse()

        self.assertEqual(
            agent_task.batch_fingerprint(batch),
            agent_task.batch_fingerprint(reordered),
        )

    def test_repair_candidate_without_preceding_findings_is_gated(self) -> None:
        manifest = self.deploy_manifest()
        manifest["status"]["I"] = "complete"
        evidence = self.evidence()
        repaired = "1" * 40
        batch = evidence["records"][2]["frozenBatch"]
        batch["deploymentSourceSha"] = repaired
        fingerprint = agent_task.batch_fingerprint(batch)
        evidence["records"] = [
            evidence["records"][0],
            {"taskId": "I", "taskStatus": "complete", "candidateSha": repaired},
            {
                "taskId": "H",
                "taskStatus": "passed",
                "candidateSha": self.REVIEW_RESULT,
                "deploymentSourceSha": repaired,
            },
            {
                **evidence["records"][2],
                "deploymentSourceSha": repaired,
                "frozenBatchFingerprint": fingerprint,
                "gitDivergence": {
                    "identical": True,
                    "authoritySha": repaired,
                    "otherSha": repaired,
                },
            },
            {
                **evidence["records"][3],
                "deploymentSourceSha": repaired,
                "frozenBatchFingerprint": fingerprint,
            },
        ]
        self.assertEqual(self.gate(manifest, evidence), "GATED")

    def test_stale_readiness_cannot_survive_repair_and_fresh_review(self) -> None:
        manifest = self.deploy_manifest()
        manifest["status"]["I"] = "complete"
        evidence = self.evidence()
        repaired = "1" * 40
        evidence["records"].extend(
            [
                {
                    "taskId": "H",
                    "taskStatus": "findings",
                    "deploymentSourceSha": self.SOURCE,
                },
                {"taskId": "I", "taskStatus": "complete", "candidateSha": repaired},
                {
                    "taskId": "H",
                    "taskStatus": "passed",
                    "candidateSha": self.REVIEW_RESULT,
                    "deploymentSourceSha": repaired,
                },
            ]
        )
        self.assertEqual(self.gate(manifest, evidence), "GATED")

    def test_new_candidate_after_final_review_invalidates_gate(self) -> None:
        manifest = self.deploy_manifest()
        evidence = self.evidence()
        evidence["records"].append(
            {"taskId": "G", "taskStatus": "complete", "candidateSha": "9" * 40}
        )
        self.assertEqual(self.gate(manifest, evidence), "GATED")

    def test_newer_conflicting_review_record_invalidates_stale_pass(self) -> None:
        manifest = self.deploy_manifest()
        evidence = self.evidence()
        evidence["records"].append(
            {
                "taskId": "H",
                "taskStatus": "findings",
                "deploymentSourceSha": self.SOURCE,
            }
        )
        self.assertEqual(self.gate(manifest, evidence), "GATED")

    def test_evidence_with_right_identity_at_wrong_path_is_gated(self) -> None:
        manifest = self.deploy_manifest()
        evidence = self.evidence()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            foreign_path = root / "agent-work" / "foreign" / "evidence.json"
            foreign_path.parent.mkdir(parents=True)
            foreign_path.write_text(json.dumps(evidence), encoding="utf-8")
            with patch.object(agent_task, "ROOT", root):
                self.assertEqual(
                    agent_task.live_gate_state(manifest, foreign_path),
                    "GATED",
                )

    def test_malformed_or_mismatched_approval_stays_preview_only(self) -> None:
        manifest = self.deploy_manifest()
        for value in (None, "", "   ", 123):
            evidence = self.evidence()
            evidence["records"][3]["approvalReference"] = value
            with self.subTest(approvalReference=value):
                self.assertEqual(self.gate(manifest, evidence), "PREVIEW")

        evidence = self.evidence()
        evidence["records"][3]["deploymentSourceSha"] = "9" * 40
        self.assertEqual(self.gate(manifest, evidence), "PREVIEW")

    def test_final_reconciliation_binds_runtime_to_readiness_source_and_fingerprint(self) -> None:
        manifest = self.deploy_manifest()
        manifest["status"]["J"] = "complete"
        evidence = self.evidence()
        evidence["records"][3].update(taskStatus="complete", runtimeAcceptance="PASS")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / manifest["workflow"]["evidence_manifest"]
            path.parent.mkdir(parents=True)

            with patch.object(agent_task, "ROOT", root):
                path.write_text(json.dumps(evidence), encoding="utf-8")
                self.assertTrue(agent_task.final_reconciliation_ready(manifest))

                wrong_source = copy.deepcopy(evidence)
                wrong_source["records"][3]["deploymentSourceSha"] = "9" * 40
                path.write_text(json.dumps(wrong_source), encoding="utf-8")
                self.assertFalse(agent_task.final_reconciliation_ready(manifest))

                wrong_fingerprint = copy.deepcopy(evidence)
                wrong_fingerprint["records"][3]["frozenBatchFingerprint"] = "0" * 64
                path.write_text(json.dumps(wrong_fingerprint), encoding="utf-8")
                self.assertFalse(agent_task.final_reconciliation_ready(manifest))

    def test_live_gate_enforces_known_additive_divergence_proof(self) -> None:
        manifest = self.deploy_manifest()
        evidence = self.evidence()
        evidence["records"][2]["gitDivergence"] = {
            "identical": False,
            "objectPresent": True,
            "ancestryProven": True,
            "changedPathsInspected": True,
            "deploymentInputsUnchanged": True,
            "changedPaths": ["docs/readme.md"],
            "deploymentInputPaths": ["services/**", "deploy/**"],
            "authoritySha": self.SOURCE,
            "otherSha": self.REVIEW_RESULT,
            "objectSha": self.REVIEW_RESULT,
            "ancestryAncestorSha": self.SOURCE,
            "ancestryDescendantSha": self.REVIEW_RESULT,
            "proofEvidencePath": "agent-work/example/results/refs.log",
            "proofEvidenceSha256": "1" * 64,
        }
        self.assertEqual(self.gate(manifest, evidence), "READY")

        protected = copy.deepcopy(evidence)
        protected["records"][2]["gitDivergence"]["changedPaths"] = [
            "services/app/server.py"
        ]
        self.assertEqual(self.gate(manifest, protected), "GATED")

        missing_proof = copy.deepcopy(evidence)
        del missing_proof["records"][2]["gitDivergence"]["proofEvidenceSha256"]
        self.assertEqual(self.gate(manifest, missing_proof), "GATED")

    def test_divergence_requires_explicit_proof(self) -> None:
        base = dict(
            identical=False,
            object_present=True,
            ancestry_proven=True,
            changed_paths_inspected=True,
            deployment_inputs_unchanged=True,
            changed_paths=["docs/readme.md"],
            deployment_input_paths=["services/**", "deploy/**"],
        )
        self.assertEqual(agent_task.classify_divergence(**base), "known_additive")
        for edit in (
            {"object_present": False},
            {"ancestry_proven": False},
            {"changed_paths_inspected": False},
            {"deployment_inputs_unchanged": False},
            {"changed_paths": ["services/app/server.py"]},
            {"destructive": True},
        ):
            with self.subTest(edit=edit):
                self.assertNotEqual(
                    agent_task.classify_divergence(**{**base, **edit}),
                    "known_additive",
                )


if __name__ == "__main__":
    unittest.main()
