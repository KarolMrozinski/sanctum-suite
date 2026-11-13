# Stage 07 — build reproducibility and software supply chain

This stage addresses how the system is built, signed, reproduced, and verified across environments.

## Technologies

### Bazel
Location: build reproducibility and dependency graph layer

Purpose:
- enforce hermetic builds
- produce reproducible, auditable build graphs
- improve build trust across team and CI environments

### Buck2
Location: fast, scalable build graph layer

Purpose:
- provide a high-performance build system for large dependency graphs
- support reproducible and incremental trusted builds

### Nix
Location: package and environment reproducibility layer

Purpose:
- define deterministic environments and toolchains
- reduce drift between local development and deployment systems

### Nix Flakes
Location: declarative environment layer

Purpose:
- package reproducible input sets and runtime environments
- support dependable build and deployment snapshots

### in-toto
Location: supply-chain attestation layer

Purpose:
- record and verify steps in the software supply chain
- provide evidence that build and release steps were executed as expected

### SLSA
Location: supply-chain integrity and provenance layer

Purpose:
- establish the security level of the software production process
- provide provenance expectations for artifact trust and release quality

### Trustee
Location: trusted execution and attestation orchestration layer

Purpose:
- coordinate trust decisions and secure workload claims
- help bridge attestation and policy across execution environments

### EAR
Location: evidence and authorization layer

Purpose:
- model evidence-based authorization and trust decisions
- support runtime and release-time access decisions grounded in provenance

### Parsec
Location: platform security service layer

Purpose:
- provide a secure mechanism for key management and cryptographic operations
- support stronger hardware-backed trust for signing and key use

### CUE
Location: declarative policy and configuration validation layer

Purpose:
- validate configuration and deployment semantics before rollout
- reduce misconfiguration and drift across environments

## Placement in the program

- CI and release pipeline: Bazel, Buck2, Nix, Nix Flakes, in-toto, SLSA
- system trust layer: Trustee, EAR, Parsec
- configuration and deployment contracts: CUE

## Live behavior

The system should be able to answer these questions before trusting an artifact or deployment:

- Was this built from the declared source?
- Was the environment reproducible?
- Were the build steps attested?
- Was the artifact signed and provenance-verified?

## Real-data readiness

This is required for real deployment confidence, not only demo execution.
