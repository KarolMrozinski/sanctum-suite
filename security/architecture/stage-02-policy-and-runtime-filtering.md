# Stage 02 — policy enforcement and runtime filtering

This stage enforces policy decisions before protected actions are executed.

## Technologies

### Rego
Location: policy definition layer

Purpose:
- model authorization, resource access, and workload policy
- encode conditions declaratively for service access

### OPA Bundles
Location: policy distribution layer

Purpose:
- package policy rules for rollout and versioning
- support controlled policy change management across environments

### OPA Gatekeeper
Location: admission and policy enforcement layer

Purpose:
- enforce policy at deployment and admission boundaries
- block unauthorized configuration or runtime drift

### Envoy
Location: API gateway and traffic control layer

Purpose:
- terminate TLS
- route authenticated traffic
- apply authorization, service-level policy, and request shaping

### eBPF
Location: kernel-level observability and enforcement

Purpose:
- inspect and monitor system behavior at the kernel boundary
- enable low-overhead runtime security telemetry

### Tetragon
Location: eBPF enforcement and runtime policy layer

Purpose:
- enforce security policy on process behavior and network activity
- detect suspicious execution patterns in real time

### Cilium
Location: service networking and security layer

Purpose:
- provide identity-aware networking at the cluster service boundary
- connect runtime filtering with policy enforcement

### Linux Security Modules (LSM)
Location: kernel security boundary

Purpose:
- enforce mandatory access controls and kernel-level isolation
- provide host-level defense in depth

### KRSI
Location: kernel and runtime hardening layer

Purpose:
- provide a resilience policy model for trusted runtime behavior
- support high-assurance system boundaries for sensitive workloads

## Placement in the program

- API gateway: Envoy delegating to OPA policy decisions
- service mesh / ingress: OPA Gatekeeper and policy packs
- runtime monitoring: eBPF, Tetragon, Cilium, LSM
- cloud or host deployment: KRSI-aware hardening rules

## Live behavior

Before a request reaches a sensitive endpoint, the path is evaluated as:

1. identity validation
2. request policy evaluation
3. gateway decision
4. runtime policy enforcement
5. logging and telemetry capture

## Real-data readiness

This stage is the first layer that turns the system into a live policy-enforced runtime rather than a static dev shell.
