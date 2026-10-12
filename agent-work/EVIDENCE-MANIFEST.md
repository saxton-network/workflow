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
        "installedScripts": [{"path": "<path>", "sha256": "<sha256 hex>"}],
        "deploymentTargets": [
          {
            "destination": "<deployment destination>",
            "mode": "0755",
            "owner": "<owner when applicable>",
            "group": "<group when applicable>"
          }
        ]
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

The example is illustrative; placeholder hashes are not valid evidence. Store one record per accepted task result or attempt, including failed attempts. Preserve record order. Use full commit SHAs and SHA-256 hex for actual fingerprints. `taskStatus` uses the manifest lifecycle vocabulary; `readinessVerdict` is only `PASS`, `FAIL`, or `UNKNOWN` for a readiness record and `null` elsewhere. The final review PASS, readiness record, and approval must name the candidate SHA in the latest completed declared implementation/integration record before that PASS, or the declared repair record following review findings. Any later candidate-producing record requires fresh review and readiness. A `PASS` readiness record identifies the exact source and includes `frozenBatch` so another agent can recompute `frozenBatchFingerprint` from canonical sorted-key JSON. The required batch fields are source SHA, deployable artifact hash, configuration and validator path/hash lists (at least one validator; a batch frozen without a validator blocks live handoff), rollback identity/provenance, installed script path/hash list, and a nonempty `deploymentTargets` array. Paths are unique within each path/hash list and destinations are unique within `deploymentTargets`; a repeated entry blocks live handoff. A batch path is repository-relative, POSIX-absolute, or Windows-absolute, with no empty, `.`, or `..` segments and no trailing separator. A Windows batch path is spelled `C:\dir\file` with backslashes only; any other path that starts with a drive letter (`C:/dir`, `C:dir`, mixed separators) is rejected, as is a Windows segment ending in `.` or a space, containing `:`, or naming a reserved device such as `NUL`, since Windows reads `file.`, `file ` and `file::$DATA` as `file` and `NUL` as a device in every folder. Batch paths compare in Unicode NFC form, and Windows batch paths compare case-insensitively. A destination is compared as a location, not as a raw string. It may not have leading or trailing whitespace or contain control characters (URL parsers drop tabs and newlines, so `..\t` would still mean `..`).

- a URL (`scheme://...`) may not contain `\`, which web URL parsers read as `/`. An `http`, `https`, `ws`, `wss`, `ftp` or `file` URL must write `//` after the scheme (`https:host` and `file:/path` are rejected). The host ends at the first `/`, `?` or `#`; the scheme and host compare case-insensitively; the port is compared as a number, with the scheme's default port the same as none; the user info, path, query and fragment compare exactly as written, with `scheme://host?q` the same as `scheme://host/?q`. An `http`, `https`, `ws`, `wss` or `ftp` URL without a host is rejected, as is a URL whose path (before any `?` or `#`) has a `.` or `..` segment, including percent-encoded ones such as `%2e%2e`. `file:///path` and `file://localhost/path` mean the local `/path`; another scheme without a host, such as `unix:///run/app.sock`, names that path under its scheme; neither may carry a query or fragment;
- a Windows destination (`C:\...`, `C:/...`, or a UNC `\\server\share\...`) treats `\` and `/` alike, ignores repeated and trailing separators, compares case-insensitively, and never matches a POSIX destination. A drive-relative `C:dir`, a `\\?\` or `\\.\` prefix (with either separator), a UNC prefix that mixes `\` and `/`, a segment ending in `.` or a space or containing `:`, and a reserved device name such as `NUL` or `COM1` (with or without an extension) are rejected. Windows 8.3 short names (`PROGRA~1`) are not resolved, so a short and a long name for one folder count as different locations. Because a single letter followed by `:` is read as a drive, an scp-style destination on a one-letter host (`h:dir`) is rejected too;
- any other destination treats `\` as `/` and ignores repeated and trailing separators, and is compared exactly otherwise;
- every destination compares in Unicode NFC form; `.` and `..` segments outside a URL query or fragment are rejected; percent-encoding is compared as written.

Two entries naming the same location in one list block live handoff, as does one file listed in two path/hash lists with different hashes. Every target has a nonempty `destination` and an explicit `mode`; `mode` may be `null` only when it does not apply to that deployment method. Optional `owner` and `group` values are recorded when applicable. Destination/mode/ownership metadata is fingerprint-bound, so changing it requires fresh readiness and approval. The human approval reference and exact source/fingerprint belong to the live-attempt record. After deployment, that record also carries `runtimeAcceptance` (`PASS` or `FAIL`); final reconciliation requires `PASS` for the same source and batch.

The readiness record includes `gitDivergence`. For identical refs, record `identical: true` with `authoritySha` and `otherSha` equal to the reviewed source. For a proposed known additive descendant, set `identical: false` and record `authoritySha`, `otherSha`, `objectSha`, `ancestryAncestorSha`, `ancestryDescendantSha`, `proofEvidencePath`, `proofEvidenceSha256`, `changedPaths`, `deploymentInputPaths`, and explicit boolean `objectPresent`, `ancestryProven`, `changedPathsInspected`, and `deploymentInputsUnchanged`. The coordinator obtains the object and verifies ancestry and paths directly; these fields are an index to durable proof, not a substitute. `changedPaths` and `deploymentInputPaths` must be plain repository-relative paths: no leading `/`, no backslashes, and no empty, `.`, or `..` segments. Produce `changedPaths` with `git --no-replace-objects diff --no-renames --no-relative --ignore-submodules=none --name-only -z <authoritySha> <otherSha>` (git 2.28 or newer) and split the output on NUL. Prove ancestry with `GIT_GRAFT_FILE=/dev/null git --no-replace-objects merge-base --is-ancestor <authoritySha> <otherSha>` and inspect objects under the same settings: a replace ref or a local `.git/info/grafts` file can give an unrelated commit the authority as a parent. In the `changedPaths` command, each flag overrides behaviour that can hide a changed path: a replace ref (for example from a mirror clone) can make a commit read as a different one (`--no-replace-objects`); by default git reports a renamed file only under its new name, so a protected file moved away would disappear (`--no-renames`); `diff.relative` would limit output to the current directory with shortened names (`--no-relative`); and `diff.ignoreSubmodules` or a `.gitmodules` `ignore` setting would drop a changed submodule pointer (`--ignore-submodules=none`). `-z` prints names verbatim; without it git quotes names containing non-ASCII characters, `"`, or control characters, and those quoted forms are rejected. File names containing backslashes are unsupported. An unnormalized entry is treated as unknown divergence. A `deploymentInputPaths` entry protects a changed path when it is the same literal path, when the path lies under it as a directory, when it matches as an `fnmatch` glob (where `*` also crosses `/`, so `services/**` and `services/*` both cover the whole subtree), or when it ends in `/` and the path lies anywhere under that directory or glob. A `**` path segment may also stand for no directories, so `**/Dockerfile` matches `Dockerfile` and `deploy/**/*.yml` matches `deploy/app.yml`. Each `[` is tried both as the start of a glob character class and as a literal bracket, independently, so `pages/[id]/**` protects the `pages/[id]/` directory and `app/[slug]/[0-9].json` protects `app/[slug]/5.json`. A pattern whose `[` characters and `**` segments together number more than six protects every path. Paths and patterns are compared in Unicode NFC form. Every repository-relative path in the frozen batch's configuration, validator, and installed-script lists is protected automatically, whether or not it is listed in `deploymentInputPaths`. A missing proof, unknown or destructive divergence, or a changed path matching protected deployment inputs blocks live handoff. Direct remote refs and mutable paths must be checked again immediately before mutation.

`reviewFindingIds` is audit metadata for linking detailed review findings; the helper does not use it as an authorization or gate input. The authoritative repair/re-review gate is established by ordered task records, candidate identity, task status, and the declared graph.

Every record is a JSON object with a string `taskId` and a `taskStatus` key whose value is a string or `null`. The index must not repeat a key within one object. A malformed record, repeated key, or unreadable index blocks every live gate instead of being skipped.

Use `null` for unavailable scalar data and an empty array only when an observed collection is truly empty. Unknown model, tokens, cost, times, approval, or deployment state must not be inferred. Optional measured token/cost fields may be added only when a trustworthy source exists; the index is not a telemetry mandate. Validation entries may use a command instead of `checkId`, and a non-process check may set `exitCode` to `null`; always record its verdict and detailed evidence link. Hash each referenced durable evidence file with SHA-256. Keep path references relative to the repository or to an explicitly named external evidence root; do not duplicate complete logs in JSON.

Never store credentials, bearer values, private keys, raw secrets, unnecessary full response bodies, or chat transcripts. Sanitize detailed evidence before indexing it. Preserve earlier records when a task retries or a validator fails; a later PASS does not erase the failure. The coordinator verifies linked hashes and actual Git state before accepting claims from the index.
