# Contract: pilot-alpha11

Frozen for this run. Changing anything here needs the owner's approval and fresh readiness.

## Source and authority

- Deployment authority: `origin` `refs/heads/main` (manifest `[deployment]`, `docs/RELEASING.md`).
- The deployed source is the exact commit the final independent review passed, fast-forwarded onto `main` without a merge commit.
- Main freeze: nothing else is merged into `main` from task P until runtime acceptance passes or any rollback is verified.

## Live batch

One dispatch of `.github/workflows/release.yml` on `main` with `version=v0.1.0-alpha.11` and `prerelease=true`, and nothing else. The exact inputs are frozen in `results/R-dispatch-inputs.json`.

## Accepted unknowns

Readiness cannot freeze these. Each is accepted with a bounded consequence:

1. **Runner tools.** `ubuntu-latest`'s git and zlib build the published ZIP. Readiness freezes the locally built hash; comparing it with the published ZIP is a live-only check. A published ZIP whose hash differs from the frozen hash fails runtime acceptance, even if its extracted files match.
2. **Release notes.** The text from `--generate-notes` is written by GitHub and is not frozen. It may be only a "Full Changelog" link.
3. **Action versions.** `actions/checkout@v7.0.1` and `actions/setup-python@v6.0.0` are pinned by tag, not by commit. Their effect on the artifact is covered by the ZIP hash check.

## Rollback

- Run fails before the tag exists: nothing to undo.
- Tag exists but no release: the owner deletes the tag.
- Release published but acceptance fails: the owner deletes the release, then its tag separately.
- The coordinator cannot delete releases in this session; it stops, asks, and then verifies against the readiness baseline.

## Retry boundary

One dispatch. Once a `v0.1.0-alpha.11` tag has existed publicly, the name is never reused: a retry is `v0.1.0-alpha.12` with fresh readiness and a new owner approval. A `PREVIEW` gate state after a failed attempt is not permission to retry.
