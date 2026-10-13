# Rollback identity: GitHub release v0.1.0-alpha.10

Rollback for this pilot does not redeploy anything. It removes the v0.1.0-alpha.11 release and tag (the owner does this on GitHub, per owner decision 4), which leaves v0.1.0-alpha.10 as the newest prerelease, unchanged.

Verified on 2026-10-13 through the GitHub connection (`get_release_by_tag`):

- Release ID 411170622, tag `v0.1.0-alpha.10` at `b2316d116d09d91788b9b653a126cb3edd702281`; it is a published prerelease, not a draft, and not immutable.
- `workflow-v0.1.0-alpha.10.zip`: asset 635581124, 66270 bytes, digest `sha256:3e6dab07ccfaffdcc39a9e77800bb3eec61e975a0cc3f51be1965658730da097`.
- `workflow-v0.1.0-alpha.10.zip.sha256`: asset 635581126, 95 bytes, digest `sha256:5336c25583e8c7ff26874adb184c607a72f0cce9221298f9c2d7c9163545a083`.
- Rebuilt locally today with `git archive --format=zip --prefix=workflow-v0.1.0-alpha.10/ b2316d1…` (git 2.43.0): SHA-256 `3e6dab07…0da097`, equal to the published ZIP digest.

After any rollback, the coordinator checks that these values and every entry in `R-baseline.json` are unchanged.
