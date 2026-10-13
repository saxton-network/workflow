# Rollback identity: GitHub release v0.1.0-alpha.12

Rollback for this drill does not redeploy anything. It removes the drill release and tag, which leaves `v0.1.0-alpha.12` as the newest prerelease, unchanged.

Verified on 2026-10-13:

- **The release:** release ID 411440138; tag `v0.1.0-alpha.12` at `c7ad3c3b1ae3e0a07d7af0322f0688e7d4533c9f`; a published prerelease, not a draft.
- **`workflow-v0.1.0-alpha.12.zip`:** asset 636354943, 104494 bytes, digest `sha256:8d93a574d942867db7a8ad7bad5d15a2cb213d863e2637050d8541aa2a211ba6`.
- **`workflow-v0.1.0-alpha.12.zip.sha256`:** asset 636354942, 95 bytes, digest `sha256:3c253fa2727edc144a975d0a29d0295f5e41ae1fb6ef4f6405b2ae726087dd64`.
- **If lost:** the alpha.12 tag could be recreated at `c7ad3c3`. Its files cannot be republished identically by `release.yml`, which packages `main` HEAD.
