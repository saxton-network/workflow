# Releasing

Releases are intentionally manual. A release should identify one exact commit that has already been reviewed and is present on `main`.

## Publish

1. Merge the reviewed release candidate to `main`.
2. Open **Actions → Publish release → Run workflow**.
3. Select `main`.
4. Enter a SemVer-style tag such as `v0.1.0-alpha.2`.
5. Leave **prerelease** enabled for experimental builds, or disable it only when intentionally publishing a normal release.

The workflow refuses to publish from any ref other than `main`. It runs the repository validation gate against the exact checked-out commit before packaging anything.

## Artifacts

The release workflow creates:

- `workflow-<version>.zip`, produced with `git archive` from the exact release commit;
- `workflow-<version>.zip.sha256`, containing its SHA-256 checksum.

GitHub also creates the release tag at the exact workflow commit. Existing tags are rejected rather than moved or overwritten.

## What the workflow does not prove

A successful release workflow proves the public repository package passed its repository validation at that commit. It does not prove that an adopting project's live deployment is safe, approved, or healthy. Those remain Workflow's project-level readiness and runtime gates.
