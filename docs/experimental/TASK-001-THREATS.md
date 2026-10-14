# Runtime threat notes for Task 001

These are component-specific applications of the owner-approved
[`docs/THREAT-MODEL.md`](../THREAT-MODEL.md), not a replacement or scope expansion.
Deliberate local tampering, malicious/colluding agents, and outside compromise
remain out of scope. No existing gate is weakened.

| Boundary | Honest failure | Fail-closed control |
| --- | --- | --- |
| Human to proposal | Approval names another revision/run | Exact plan hash and workflow-bound simulation approval |
| Actor to runtime | Builder requests approval/delegation/review authority | Fixed role checks; no implicit grants; separate reviewer |
| Scheduler to actor | Double dispatch or aliased ownership | Transactional claim; unique branch/worktree labels; fenced leases |
| Provider to coordinator | FAIL/UNKNOWN, mismatched result, absent telemetry | Strict result identities, hashes, verdicts and resource limits |
| Journal to read model | Interrupted write or corrupted checkpoint | Atomic event/projection write; full chain/contract verification |
| Restart to worker | Stale actor or late response continues | Expiry/cancel fences result acceptance; recovery never dispatches |
| Git to scheduler | Source changed or cannot be observed | Exact branch/HEAD check before claim and result acceptance |
| Simulation to deployment | Mock pass mistaken for real authorization | Separate schema and storage; no deployment or shell capabilities |

The CLI's actor names are local trusted-operator assertions, not authenticated
identities. Anyone with database/filesystem access can impersonate them. This
matches the existing trusted local-machine model, but is inadequate for a
multi-user service or adversarial worker. SQLite triggers and hashes are audit
controls against accidents, not cryptographic attestations. Providers are trusted
code; only the mock is enabled. The future bus must enforce backend isolation and
timeouts before accepting untrusted adapters.

Git checks do not prove remote authority, ancestry, a clean real worker worktree,
or immutable source bytes during a live mutation. No runtime operation promotes
or deploys source. Frozen deployment batches continue to belong exclusively to
the existing v3 contract. Budget telemetry is synthetic in this slice; real spend
and OS-process termination are not implemented. Unknown usage is never zero.
