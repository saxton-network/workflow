# Contributing

Workflow is intentionally conservative. Changes to graph validation, evidence binding, approval semantics, source identity, or deployment gates should be treated as safety-sensitive.

For substantial changes:

1. Describe the invariant being changed.
2. Add or update regression tests that demonstrate the previous and intended behavior.
3. Keep builder and reviewer roles independent.
4. Prefer fail-closed behavior when evidence is missing or ambiguous.
5. Do not weaken a gate merely to make an example or pilot pass.

Bug reports are especially useful when they include a minimal manifest or evidence fixture showing an unsafe state the helper accepts, or a safe state it incorrectly rejects.
