# Results: pilot-rollback-drill

One file per task attempt, using `agent-work/RESULT-TEMPLATE.md`. The readiness data files that the frozen batch names (`R-*.json`, `R-expected-checksum*.txt`) live here too.

- Only the coordinator commits here, on `pilot/rollback-drill-records`.
- The coordinator indexes these files in `../evidence.json`.
- This workflow is a drill (`drill: true`). Its live attempt is expected to fail on an injected fault and to be rolled back. That failure is the drill working, not an accidental failed release.
