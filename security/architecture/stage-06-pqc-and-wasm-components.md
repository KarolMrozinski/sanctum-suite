# Stage 06 — post-quantum crypto and Wasm component model

This stage future-proofs the trust and execution model for portable, secure, and evolving components.

## Technologies

### ML-KEM
Location: key encapsulation layer

Purpose:
- support post-quantum key exchange for secure communication
- harden encrypted channels against future cryptographic threats

### Kyber
Location: post-quantum KEM layer

Purpose:
- provide the canonical PQC key exchange baseline for future security evolution
- align with the ML-KEM migration path for realistic deployments

### ML-DSA
Location: signature layer

Purpose:
- provide quantum-resistant signature workflows for bounded trust boundaries

### Dilithium
Location: digital signature layer

Purpose:
- provide a widely recognized post-quantum signature mechanism
- support signature validation across secure workloads and distribution paths

### Wasmtime
Location: Wasm runtime engine

Purpose:
- execute portable secure components in a sandboxed environment
- support modular, isolated logic blocks and policy plugins

### WebAssembly Component Model
Location: portable component boundary

Purpose:
- define composable, interface-based components
- allow secure plugin or micro-workload integration without broad runtime coupling

### WASI
Location: Wasm system interface layer

Purpose:
- provide a portable, secure execution boundary for Wasm components
- standardize the system-facing interface used by components

## Placement in the program

- secure plugin system: Wasmtime + WASI + Component Model
- cryptographic boundary: ML-KEM, Kyber, ML-DSA, Dilithium
- data protection and trust layer: crypto operations behind attestation and policy enforcement

## Live behavior

These technologies are used where portability, modularity, and future-resistant cryptography matter most:

- policy plugins
- secure data adapters
- external logic modules
- long-lived trust boundaries

## Real-data readiness

They are not the first primitives to add, but they are the correct long-term layer once the foundation identity, attestation, isolation, and policy stacks are in place.
