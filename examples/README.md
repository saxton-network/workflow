# Examples

These examples demonstrate manifest shapes. They use placeholder commit IDs, branch names, and authority refs. Adapt them to the target repository.

- nondeployment/manifest.toml: implementation to independent review to conditional repair to Git-only integration.
- deployment/manifest.toml: implementation to independent review to optional repair to release readiness to human-gated live deployment to final reconciliation.

The deployment example omits an authority-promotion task because it assumes the reviewed source is already authoritative. It still declares authority_remote and authority_ref, which are mandatory.
