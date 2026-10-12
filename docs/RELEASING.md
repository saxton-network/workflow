# Releasing

Releases are intentionally manual. A release should identify one exact commit that has already been reviewed and is present on `main`.

## Publish

1. Merge the reviewed release candidate to `main`.
2. Open **Actions → Publish release → Run workflow**.
3. Select `main`.
4. Enter a `v`-prefixed SemVer 2.0.0 tag such as `v0.1.0-alpha.3`. Build metadata (`+...`) is not accepted; `scripts/check-release-version.sh` defines the exact rule.
5. Leave **prerelease** enabled for experimental builds, or disable it only when intentionally publishing a normal release.

The workflow fails, rather than silently skipping, when dispatched from any ref other than `main`. It runs the repository validation gate against the exact checked-out commit before packaging anything.

## Artifacts

The release workflow creates:

- `workflow-<version>.zip`, produced with `git archive` from the exact release commit;
- `workflow-<version>.zip.sha256`, containing its SHA-256 checksum.

The workflow creates the release tag itself at the exact workflow commit, using a single API call that fails if the tag already exists, then publishes the release against that tag and verifies the tag still points at the packaged commit. Existing tags are rejected rather than moved or overwritten, and concurrent runs for the same version are serialized.

If a run fails after creating the tag but before publishing, the tag remains and a rerun is refused. Inspect the tag, delete it deliberately if it points at the intended commit and has no release, and dispatch again.

## What the workflow does not prove

A successful release workflow proves the public repository package passed its repository validation at that commit. It does not prove that an adopting project's live deployment is safe, approved, or healthy. Those remain Workflow's project-level readiness and runtime gates.
