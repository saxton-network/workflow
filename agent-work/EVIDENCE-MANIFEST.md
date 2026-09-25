# Workflow evidence index (v3)

The coordinator maintains `agent-work/<workflow-id>/evidence.json`, named by `[workflow].evidence_manifest`. The top-level manifest `phase` is the workflow ID, so the declared path must be exactly `agent-work/<phase>/evidence.json` and the JSON `workflowId` must equal `phase`. This small UTF-8 JSON index points to task results, validation logs, review reports, failed attempts, and preserved checksums. It does not replace those records or the Git history. Task agents provide evidence to the coordinator; parallel agents do not edit this shared file.

## Shape

```json
{
  "workflowVersion": 3,
  "workflowId": "example",
  "records": [
    {
      "taskId": "R",
      "attempt": 1,
      "role": "release_readiness",
      "model": null,
      "branch": "example/readiness",
      "worktree": null,
      "baseSha": "<full commit SHA>",
      "candidateSha": "<full commit SHA>",
      "deploymentSourceSha": "<full reviewed source SHA>",
      "taskStatus": "complete",
      "readinessVerdict": "PASS",
      "startedAt": null,
      "completedAt": null,
      "changedPaths": [],
      "reviewFindingIds": [],
      "approvalReference": null,
      "rollbackArtifact": {"identity": "<immutable ID>", "provenance": "<evidence path>"},
      "frozenBatch": {
        "deploymentSourceSha": "<full reviewed source SHA>",
        "deployableArtifactSha256": "<sha256 hex>",
        "deploymentConfiguration": [{"path": "<path>", "sha256": "<sha256 hex>"}],
        "validators": [{"path": "<path>", "sha256": "<sha256 hex>"}],
        "rollbackArtifact": {"identity": "<immutable ID>", "provenance": "<evidence path>"},
        "installedScripts": [{"path": "<path>", "sha256": "<sha256 hex>"}]
      },
      "frozenBatchFingerprint": "<sha256 hex>",
      "gitDivergence": {
        "identical": true,
        "authoritySha": "<full reviewed source SHA>",
        "otherSha": "<full reviewed source SHA>"
      },
      "validation": [
        {
          "checkId": "artifact-extract",
          "inputFingerprint": "<sha256 hex>",
          "validatorSha256": "<sha256 hex>",
          "exitCode": 0,
          "verdict": "PASS",
          "recordedAt": null,
          "evidencePath": "agent-work/example/results/R-artifact.log"
        }
      ],
      "evidence": [{"path": "agent-work/example/results/R.md", "sha256": "<sha256 hex>"}]
    }
  ]
}
```

The example is illustrative; placeholder hashes are not valid evidence. Store one record per accepted task result or attempt, including failed attempts. Preserve record order. Use full commit SHAs and SHA-256 hex for actual fingerprints. `taskStatus` uses the manifest lifecycle vocabulary; `readinessVerdict` is only `PASS`, `FAIL`, or `UNKNOWN` for a readiness record and `null` elsewhere. The final review PASS, readiness record, and approval must name the candidate SHA in the latest completed declared implementation/integration record before that PASS, or the declared repair record following review findings. Any later candidate-producing record requires fresh review and readiness. A `PASS` readiness record identifies the exact source and includes `frozenBatch` so another agent can recompute `frozenBatchFingerprint` from canonical sorted-key JSON. The required batch fields are source SHA, deployable artifact hash, configuration and validator path/hash lists, rollback identity/provenance, and installed script path/hash list. Include relevant destination and mode metadata for the actual deployment. The human approval reference and exact source/fingerprint belong to the live-attempt record. After deployment, that record also carries `runtimeAcceptance` (`PASS` or `FAIL`); final reconciliation requires `PASS` for the same source and batch.

The readiness record includes `gitDivergence`. For identical refs, record `identical: true` with `authoritySha` and `otherSha` equal to the reviewed source. For a proposed known additive descendant, set `identical: false` and record `authoritySha`, `otherSha`, `objectSha`, `ancestryAncestorSha`, `ancestryDescendantSha`, `proofEvidencePath`, `proofEvidenceSha256`, `changedPaths`, `deploymentInputPaths`, and explicit boolean `objectPresent`, `ancestryProven`, `changedPathsInspected`, and `deploymentInputsUnchanged`. The coordinator obtains the object and verifies ancestry and paths directly; these fields are an index to durable proof, not a substitute. A missing proof, unknown or destructive divergence, or a changed path matching protected deployment inputs blocks live handoff. Direct remote refs and mutable paths must be checked again immediately before mutation.

Use `null` for unavailable scalar data and an empty array only when an observed collection is truly empty. Unknown model, tokens, cost, times, approval, or deployment state must not be inferred. Optional measured token/cost fields may be added only when a trustworthy source exists; the index is not a telemetry mandate. Validation entries may use a command instead of `checkId`, and a non-process check may set `exitCode` to `null`; always record its verdict and detailed evidence link. Hash each referenced durable evidence file with SHA-256. Keep path references relative to the repository or to an explicitly named external evidence root; do not duplicate complete logs in JSON.

Never store credentials, bearer values, private keys, raw secrets, unnecessary full response bodies, or chat transcripts. Sanitize detailed evidence before indexing it. Preserve earlier records when a task retries or a validator fails; a later PASS does not erase the failure. The coordinator verifies linked hashes and actual Git state before accepting claims from the index.
