# Stage 01 — identity, trust, and attestation

This stage establishes trust before any service is allowed to act on real data.

## Technologies

### SPIFFE
Location: service identity layer

Purpose:
- assign a workload identity to every component, service, and plugin
- make authorization decisions identity-based instead of host-based
- propagate workload identity through API, queue, and control-plane paths

### SPIRE
Location: identity issuance and workload attestation

Purpose:
- issue identity documents and certificates to services
- validate workload registration and trust state
- integrate with workload attestation for a stronger runtime posture

### Veraison
Location: verification layer for attestation claims

Purpose:
- validate attestation evidence from confidential workloads
- confirm that claims match the approved platform state
- reject stale or mismatched evidence before allowing sensitive actions

### Keylime
Location: host integrity and measured boot layer

Purpose:
- enforce measured boot and remote attestation for node-level integrity
- verify that machines are not tampered with before sensitive workloads start
- support a stronger boot-time trust baseline

## Placement in the program

- launcher and desktop shell: monitor identity readiness and attestation status only
- API gateway: require SPIFFE identity propagation and workload trust checks
- service mesh / gateway route: enforce mTLS and identity-aware routing
- runtime health checks: fail closed when attestation is missing or invalid

## Live behavior

When a service starts with a real workload identity, it must be able to prove:

- who it is
- which workload it represents
- whether the host/VM passed attestation checks
- whether the evidence is fresh and approved

Only after those conditions are satisfied may the service open real data flows.

## Real-data readiness

These components are prepared for live data once the trust baseline is wired in.
