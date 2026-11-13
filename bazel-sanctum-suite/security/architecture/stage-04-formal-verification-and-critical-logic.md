# Stage 04 — formal verification and critical logic

This stage focuses on the components that must be logically correct under strict constraints.

## Technologies

### Ada
Location: critical system logic layer

Purpose:
- implement trustworthy system logic in a language with strong safety and reliability patterns
- provide a baseline for mission-critical logic components

### SPARK
Location: safety-critical logic and static proof layer

Purpose:
- enforce language-level checks
- reduce undefined behavior and logic defects in critical code paths

### GNATprove
Location: proof and verification layer

Purpose:
- apply static analysis and proof checks to Ada/SPARK code
- confirm core properties before deployment

### Ada Ravenscar Profile
Location: realtime safe subset layer

Purpose:
- support constrained, deterministic software execution patterns
- reduce runtime complexity in critical components

### Ada Jorvik Profile
Location: advanced safety and reliability profile

Purpose:
- allow a more specialized high-integrity execution model where needed
- align critical services with stricter execution constraints

### Ada Contracts
Location: design-by-contract layer

Purpose:
- encode invariants and pre/postconditions in the critical logic layer
- improve correctness and reviewability of key state transitions

### Alire
Location: critical component packaging and build layer

Purpose:
- manage Ada dependencies and reproducible build environment
- provide a deterministic lifecycle for mission-critical components

### GNAT
Location: compiler and toolchain layer

Purpose:
- build trusted Ada/SPARK code with strong language support
- provide the base toolchain for proof-oriented software

### CompCert
Location: verified compiler layer

Purpose:
- reduce uncertainty in compiled critical components
- support higher-assurance builds for selected hardened modules

### Verus
Location: verification-oriented systems language layer

Purpose:
- prove correctness properties in selected critical logic paths
- support high-assurance verification for system-level code

### Creusot
Location: Rust proof support layer

Purpose:
- integrate proof-oriented Rust verification where Rust is used in security-critical components
- complement formal verification patterns across mixed-language components

### Kani
Location: Rust verification layer

Purpose:
- validate Rust code against safety and design properties
- catch risky logic before deployment

## Placement in the program

- policy decision logic: Rego + OPA remains policy definition, but critical execution logic sits in Ada/SPARK-backed modules where the logic is sensitive
- runtime trust and measured execution: modules controlling attestation, state transitions, and protected data flows
- secure app adapters: only the critical edges are formalized; the broad UI and dashboard stay in normal application code

## Live behavior

These technologies protect the hardest correctness boundaries:

- secure state transitions
- authorization outcomes
- attestation decision processing
- sensitive config change gates
- runtime permission evaluation

## Real-data readiness

This layer is required when the platform moves from prototype to mission-critical processing.
