# Task J: owner approval

On 2026-10-13 the coordinator showed the owner the concrete live preview in plain language. It covered:

- the source and fingerprint;
- the declared deviation and the expected-failure signature;
- the commands, effects and exposure, including that the drill stays public until the owner deletes it;
- the owner's rollback steps and the request not to touch other releases or tags;
- the verification, the stop conditions and the retry boundary.

It ended with the question "Do you approve, and are you available now to delete the drill release and tag within 30 minutes? (y/n)". The owner answered `y`.

The approval covers exactly one batch:

- Source: `92c51e6c69d7ed29ee6e879733ad4b801a82814e`
- Frozen batch fingerprint: `f29928f7347068111db6495e702ae4c129f14aca8ff26b0453afe9992b65f52a`
- One dispatch of `release.yml` on `main` with `version: v0.0.0-drill.1`, `prerelease: true`

It does not cover a retry, another version, or any other source or batch.
