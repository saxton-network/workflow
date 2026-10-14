# Rollback artifact: github-release-v0.1.0-alpha.12

- **Identity:** `github-release-v0.1.0-alpha.12`, the newest published prerelease before alpha.13. Rolling back alpha.13 means removing alpha.13's release and tag so that alpha.12 is again the newest; alpha.12 itself is never touched.
- **Release:** ID 411440138, published 2026-10-13T08:11:58Z, prerelease, not a draft, not immutable.
- **Tag:** `v0.1.0-alpha.12` → `c7ad3c3b1ae3e0a07d7af0322f0688e7d4533c9f` (lightweight, `git ls-remote --tags origin`).
- **Assets (API digests):**
  - `workflow-v0.1.0-alpha.12.zip`, 104494 bytes, `sha256:8d93a574d942867db7a8ad7bad5d15a2cb213d863e2637050d8541aa2a211ba6`;
  - `workflow-v0.1.0-alpha.12.zip.sha256`, 95 bytes, `sha256:3c253fa2727edc144a975d0a29d0295f5e41ae1fb6ef4f6405b2ae726087dd64`.
- **Verified:** `git archive --format=zip --prefix=workflow-v0.1.0-alpha.12/ c7ad3c3` (git 2.43.0) reproduces the ZIP digest exactly.
- **Note:** alpha.12 cannot be republished faithfully by `release.yml`, which packages `main` HEAD; that is why rollback deletes only alpha.13 items and never acts on alpha.12.
