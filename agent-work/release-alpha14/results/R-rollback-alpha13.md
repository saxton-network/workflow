# Rollback artifact: github-release-v0.1.0-alpha.13

- **Identity:** `github-release-v0.1.0-alpha.13`, the newest published prerelease before alpha.14. Rolling back alpha.14 means removing alpha.14's release and tag so that alpha.13 is again the newest; alpha.13 itself is never touched.
- **Release:** ID 412320357, `Workflow v0.1.0-alpha.13`, published 2026-10-14T03:49:47Z, prerelease, not a draft, not immutable.
- **Tag:** `v0.1.0-alpha.13` → `84d826a40b8f8567439ab15eb270a1a752f92a82`. It is lightweight: the connection's tag read and `curl`'s ref read both give `object.type` `commit`, and `git ls-remote --tags` agrees.
- **Assets.** For each, the API `digest` field equals the SHA-256 of the bytes downloaded with `curl`:
  - `workflow-v0.1.0-alpha.13.zip`: 161870 bytes, `sha256:e520b61c3c48572b73001d333b2c79499e33b3e5c19f34988d5be2f3e191d5d4`;
  - `workflow-v0.1.0-alpha.13.zip.sha256`: 95 bytes, `sha256:682c24ea849181807521e89b938cab9bde3e3712daecd4e05233d18ab603c939`.
- **Verified:** `git archive --format=zip --prefix=workflow-v0.1.0-alpha.13/ 84d826a` (git 2.43.0) reproduces the ZIP digest exactly.
- **Note:** `release.yml` packages `main` HEAD, so it cannot republish alpha.13 faithfully. That is why a rollback deletes only alpha.14 items and never acts on alpha.13.
