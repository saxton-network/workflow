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

The example is illustrative; placeholder hashes are not valid evidence. Store one record per accepted task result or attempt, including failed attempts. Preserve record order. Use full commit SHAs and SHA-256 hex for actual fingerprints. `taskStatus` uses the manifest lifecycle vocabulary; `readinessVerdict` is only `PASS`, `FAIL`, or `UNKNOWN` for a readiness record and `null` elsewhere. The final review PASS, readiness record, and approval must name the candidate SHA in the latest completed declared implementation/integration record before that PASS, or the declared repair record following review findings. Any later candidate-producing record requires fresh review and readiness. A `PASS` readiness record identifies the exact source and includes `frozenBatch` so another agent can recompute `frozenBatchFingerprint` from canonical sorted-key JSON. The required batch fields are source SHA, deployable artifact hash, configuration and validator path/hash lists (at least one validator; a batch frozen without a validator blocks live handoff), rollback identity/provenance, installed script path/hash list, and a nonempty `deploymentTargets` array. Paths and destinations have one accepted format; anything else blocks live handoff, and the helper's task output names the rule each rejected entry breaks. A *segment* is one or more letters, digits, `.`, `_`, `-` or `~`, and is not `.` or `..`. Anything else (spaces, non-ASCII, `%`, `@`, `:`, quotes, empty segments from a repeated or trailing separator) is outside the format.

- A **batch path** is repository-relative (`deploy/app.conf`, not starting with `~`, which a shell reads as a home directory), POSIX-absolute (`/etc/app/app.conf`), or a Windows drive path (`C:\ProgramData\app\app.json`: uppercase drive letter, backslashes only). A repository-relative path names the file at `deploymentSourceSha`. The one exception is a `deploymentConfiguration` path under the workflow's own `agent-work/<workflow-id>/` directory: it names a data file the coordinator wrote for this run (such as the exact dispatch inputs, an expected checksum, or an observed live setting), as committed on its records branch when readiness froze the batch. Either way, the recorded SHA-256 pins the bytes. Validators and installed scripts are always read from the reviewed source, so a `validators` or `installedScripts` path under `agent-work/<workflow-id>/` blocks live handoff.
- A **destination** is one of:
  - an absolute POSIX path (`/srv/app`), or `/` itself;
  - a Windows drive path (`C:\srv\app`), or a drive root such as `C:\`;
  - a UNC path (`\\server\share\app`);
  - a URL `scheme://host[:port][/path]` with a lowercase scheme of at least two characters and a lowercase host. The host is a DNS name of lowercase letters, digits, `-` and `.` (write internationalised names in `xn--` form), a dotted-quad IPv4 address (a host whose last label is a decimal or `0x` hex number must be one, since parsers read `127.1` and `0x7f000001` as `127.0.0.1`), or a compressed IPv6 address in brackets (`[2001:db8::1]`, not `[0:0::1]` or an IPv4-mapped form). A port is written without leading zeros, and is left out when it is the scheme's default: 80 for `http` and `ws`, 443 for `https` and `wss`, 21 for `ftp`, 990 for `ftps`, 22 for `ssh`, `sftp` and `scp`, 873 for `rsync`, 9418 for `git`, 445 for `smb`. For other schemes the helper does not know the default, so write the port the same way every time. There is no user info, query, fragment, or percent-encoding;
  - a hostless URL `scheme:///path` (`unix:///run/app.sock`); `http`, `https`, `ws`, `wss` and `ftp` always need a host.
- `file:` URLs are not accepted; write the plain path. scp-style `host:/path` is written `ssh://host/path`.
- In Windows drive and UNC paths, a segment may not end in `.`, contain `~`, or name a reserved device (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, with or without an extension), because Windows reads `file.` as `file`, `NAME~1` as an 8.3 short name for a longer one, and those names as devices in every folder. Write the full long name. Windows paths compare case-insensitively; every other accepted path or destination compares exactly as written.

When readiness depends on a live setting that is not a file (for example a forge's immutable-release or branch-protection setting), record the observed value in a results file under `agent-work/<workflow-id>/results/`, and list that file in `deploymentConfiguration` when the setting bounds the batch. The setting is still mutable live state: recheck it immediately before mutation and after any rollback, like any other baseline.

Paths are unique within each path/hash list and destinations are unique within `deploymentTargets`. Two entries naming the same location in one list block live handoff, as does one file listed in two path/hash lists with different hashes. Every target has a nonempty `destination` and an explicit `mode`; `mode` may be `null` only when it does not apply to that deployment method. Optional `owner` and `group` values are recorded when applicable. Destination/mode/ownership metadata is fingerprint-bound, so changing it requires fresh readiness and approval. The human approval reference and exact source/fingerprint belong to the live-attempt record. After deployment, that record also carries `runtimeAcceptance` (`PASS` or `FAIL`); final reconciliation requires `PASS` for the same source and batch.

The readiness record includes `gitDivergence`. For identical refs, record `identical: true` with `authoritySha` and `otherSha` equal to the reviewed source. For a proposed known additive descendant, set `identical: false` and record `authoritySha`, `otherSha`, `objectSha`, `ancestryAncestorSha`, `ancestryDescendantSha`, `proofEvidencePath`, `proofEvidenceSha256`, `changedPaths`, `deploymentInputPaths`, and explicit boolean `objectPresent`, `ancestryProven`, `changedPathsInspected`, and `deploymentInputsUnchanged`. The coordinator obtains the object and verifies ancestry and paths directly; these fields are an index to durable proof, not a substitute. `changedPaths` entries are repository-relative paths made of segments as defined above; `deploymentInputPaths` entries are the same, may also use the glob characters `*`, `?`, `[`, `]` and `!` (each `[` closed by a `]` in the same segment, as `fnmatch` reads it: a `]` right after `[` or `[!` is a class member, so `[]` and `[!]` never close while `[]a]` does; a `]` with no open `[` before it in the same segment is rejected), and may end in `/`. An entry outside this format makes the divergence unknown, so a descendant that changes a file whose name uses other characters cannot be classified as additive. Run the git commands below with no inherited `GIT_*` environment variables, so settings left by other tools cannot change their output. This rule covers the local proof commands (`diff`, `merge-base`, `rev-parse`, and object inspection). `fetch` and `push` may need git configuration that the environment supplies as `GIT_CONFIG_*` variables, such as proxy URL rewrites or a CA bundle, so run them as usual and then inspect what they fetched with the local commands. Produce `changedPaths` with `git --no-replace-objects -c core.commitGraph=false diff --no-renames --no-relative --ignore-submodules=none --name-only -z <authoritySha> <otherSha>` (git 2.28 or newer) and split the output on NUL. Prove ancestry with `GIT_GRAFT_FILE=/dev/null git --no-replace-objects -c core.commitGraph=false -c advice.graftFileDeprecated=false merge-base --is-ancestor <authoritySha> <otherSha>` and inspect objects under the same settings: a replace ref, a local `.git/info/grafts` file, or a forged `.git/objects/info/commit-graph` can give an unrelated commit the authority as a parent. In the `changedPaths` command, each flag overrides behaviour that can hide a changed path: a replace ref (for example from a mirror clone) can make a commit read as a different one (`--no-replace-objects`); a forged commit-graph can give a commit another commit's tree (`-c core.commitGraph=false`); by default git reports a renamed file only under its new name, so a protected file moved away would disappear (`--no-renames`); `diff.relative` would limit output to the current directory with shortened names (`--no-relative`); and `diff.ignoreSubmodules` or a `.gitmodules` `ignore` setting would drop a changed submodule pointer (`--ignore-submodules=none`). `-z` prints names verbatim, so a name outside the format is rejected rather than silently quoted. A `deploymentInputPaths` entry protects a changed path when it is the same literal path, when the path lies under it as a directory, when it matches as an `fnmatch` glob (where `*` also crosses `/`, so `services/**` and `services/*` both cover the whole subtree), or when it ends in `/` and the path lies anywhere under that directory or glob. A `**` path segment may also stand for no directories, so `**/Dockerfile` matches `Dockerfile` and `deploy/**/*.yml` matches `deploy/app.yml`. `[...]` is a glob character class. A pattern with more than six `**` segments protects every path. Every repository-relative path in the frozen batch's configuration, validator, and installed-script lists is protected automatically, whether or not it is listed in `deploymentInputPaths`. A missing proof, unknown or destructive divergence, or a changed path matching protected deployment inputs blocks live handoff. Direct remote refs and mutable paths must be checked again immediately before mutation.

`reviewFindingIds` is audit metadata for linking detailed review findings; the helper does not use it as an authorization or gate input. The authoritative repair/re-review gate is established by ordered task records, candidate identity, task status, and the declared graph.

Every record is a JSON object with a string `taskId` and a `taskStatus` key whose value is a string or `null`. The index must not repeat a key within one object. A malformed record, repeated key, or unreadable index blocks every live gate instead of being skipped.

Use `null` for unavailable scalar data and an empty array only when an observed collection is truly empty. Unknown model, tokens, cost, times, approval, or deployment state must not be inferred. `model` names the model behind the role when known. A repository that keeps model identifiers out of committed files records `null` and states the reviewer's independence in words in the result file, for example "a separate agent on a different model from the builder". Optional measured token/cost fields may be added only when a trustworthy source exists; the index is not a telemetry mandate. Validation entries may use a command instead of `checkId`, and a non-process check may set `exitCode` to `null`; always record its verdict and detailed evidence link. Hash each referenced durable evidence file with SHA-256. Keep path references relative to the repository or to an explicitly named external evidence root; do not duplicate complete logs in JSON.

Never store credentials, bearer values, private keys, raw secrets, unnecessary full response bodies, or chat transcripts. Sanitize detailed evidence before indexing it. Preserve earlier records when a task retries or a validator fails; a later PASS does not erase the failure. The coordinator verifies linked hashes and actual Git state before accepting claims from the index.
