# Design notes

## Problem

Multi-agent coding becomes risky when branch isolation, review independence, deployment authority, evidence freshness, and live approval are left to conversational convention.

Workflow makes those expectations durable and machine-checkable enough to fail closed on common mistakes.

## Two layers

### Static graph validation

The manifest describes tasks, dependency status requirements, terminal state, deployment stages, authority, and human gates. Static validation rejects malformed graphs before dispatch.

### Dynamic evidence gating

Static readiness is not enough for deployment. Coordinator-owned evidence binds:

- the exact reviewed candidate;
- readiness verdict;
- artifact, configuration, script, and validator identities;
- rollback provenance;
- Git divergence proof;
- frozen batch fingerprint;
- approval reference;
- runtime acceptance.

## Why source identity is explicit

Implementation commits, review commits, result commits, evidence commits, merge commits, and later canonical descendants can all be different Git objects. Deployment must not silently substitute one for another.

## Why approval is not just a manifest boolean

Human approval is external reality. The helper can verify that evidence contains a reference bound to the exact source and fingerprint, but the coordinator must independently verify the real approval before mutation.

## Why UNKNOWN exists

Some readiness facts cannot always be observed. Treating absence of evidence as success is a deployment bug. UNKNOWN therefore blocks unless a frozen contract explicitly accepts that named unknown with bounded consequences and the overall readiness verdict is intentionally resolved.

## Why failed attempts remain

A later pass does not make an earlier validator defect, rollback, or failed attempt cease to exist. Preserved failures make review, auditing, and process improvement possible.
