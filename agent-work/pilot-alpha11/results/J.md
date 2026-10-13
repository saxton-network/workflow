# Task J: live release and runtime acceptance

**Runtime acceptance: PASS**

- Source: `d568c5f18986ea122018bde2d1badb257346dd92`
- Fingerprint: `a4724dc9718a7bf3cc11a4dd0de9139d2e660001ae59ddf75c8443c68818d83b`
- Approval: `results/J-approval.md` (owner `y`, 2026-10-13)

## Rechecks immediately before dispatch (2026-10-13T06:04:25Z)

All matched readiness:

- `origin/main` = source; checked by `rev-parse` with no inherited `GIT_*` variables, and by `ls-remote`.
- No `v0.1.0-alpha.11` tag in `ls-remote`. `get_release_by_tag` returned 404, and `list_releases` showed the same ten releases with no draft.
- Immutable releases: `{"enabled": false, "enforced_by_owner": false}`.
- All seven frozen file hashes and the local ZIP hash were unchanged. The source worktree was clean at the source.
- The latest `release.yml` run before dispatch was run 9 (alpha.10).

## Dispatch

One call: `actions_run_trigger` `run_workflow`, `workflow_id=release.yml`, `ref=main`, `inputs={"version": "v0.1.0-alpha.11", "prerelease": true}`. Response 204, "Workflow run has been queued".

Exactly one `workflow_dispatch` run of `release.yml` on `main` was created after the dispatch: run 38354718090 (run number 10, created 06:04:34Z). Its `head_sha` = source, so it was not cancelled. It completed with conclusion `success` at 06:04:51Z.

## Runtime acceptance

| Check | Result |
| --- | --- |
| Run concluded successfully, `head_sha` = source | PASS |
| Release published, prerelease, not draft | PASS: release 411336897, published 06:04:47Z, `prerelease: true`, `draft: false` |
| Not "latest" | PASS: `GET /releases/latest` returns Not Found (every release is a prerelease) |
| Exactly the two expected files | PASS: `workflow-v0.1.0-alpha.11.zip` (66734 bytes) and `workflow-v0.1.0-alpha.11.zip.sha256` (95 bytes), nothing else |
| ZIP hash = frozen hash | PASS: GitHub digest and downloaded bytes are both `b8c4c8c0a4ce76bd6851ae18a161e556a95f8c765639a62ab064ed3c2bd6c2f1`, and `cmp` with the local build is identical |
| `.sha256` bytes = expected bytes | PASS: `cmp` with `R-expected-checksum.txt` is identical (SHA-256 `5dccd42e…3241921f`) |
| Unpacked ZIP = `git archive` of the source | PASS: `diff -r` shows no differences |
| Tag is lightweight at the source | PASS: `ls-remote` shows `refs/tags/v0.1.0-alpha.11` at the source with no peeled `^{}` line, and `git/ref/tags/v0.1.0-alpha.11` has object type `commit` |
| alpha.10 and all other tags and releases match the baseline | PASS: the ten baseline tags point at the same commits, the ten baseline releases keep their IDs and publish times, alpha.10's asset digests are unchanged, and its downloaded files still hash to `3e6dab07…0da097` and `5336c255…45a083` |
| `main` still = source | PASS |

## Notes

- The release notes are GitHub's generated text: only a "Full Changelog" link from alpha.10 to alpha.11 (accepted unknown 2, owner decision 7).
- The release API reports `created_at` 03:49:15Z, which is the source commit's time, not the publish time. `published_at` is 06:04:47Z.
- The download URLs were fetched without credentials, so the files are public as expected.
