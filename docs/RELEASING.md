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

## Rolling back a release

The release workflow cannot delete anything. This procedure works only while GitHub's immutable-releases setting is off; an immutable release cannot be removed this way, so check the setting before publishing anything that may need rolling back. A rollback is done by someone with write access on the GitHub website, one item at a time:

1. Delete the release.
2. Then delete its tag on the Tags page.

Order and verification matter:

- **Release only.** Deleting a release leaves its tag, and the tag's source archives stay downloadable.
- **Tag first.** Deleting a tag first is understood to turn its release into a draft, which no longer lives at `/releases/tag/<tag>`; delete the draft through its own link. This was not observed in the drill, which deleted the release first.
- **Use the API to check.** While a tag exists, `/releases/tag/<tag>` still serves a plain tag page after its release is deleted. Verify each deletion through the API: the release by tag returns 404, the authenticated release list shows no release or draft with that tag, and `git ls-remote` shows no tag. Do not rely on the web page.
- **Draft visibility.** Draft releases are visible only to accounts with write access. Record which identity read the release list.
- **Final check.** Compare the full tag and release lists with a snapshot taken before publishing.

`agent-work/pilot-rollback-drill/` is a worked example.

## What the workflow does not prove

A successful release workflow proves the public repository package passed its repository validation at that commit. It does not prove that an adopting project's live deployment is safe, approved, or healthy. Those remain Workflow's project-level readiness and runtime gates.
