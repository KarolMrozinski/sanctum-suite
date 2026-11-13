# Stage 05 — binary analysis, fuzzing, and proving tools

This stage covers security analysis and validation of the broader system and its compiled or external components.

## Technologies

### LibAFL
Location: fuzzing and exploit discovery layer

Purpose:
- test parsers, protocol handlers, and runtime components under stress
- find input-induced weaknesses and crash conditions before deployment

### Snapchange
Location: security delta analysis layer

Purpose:
- identify risky differences between revisions
- focus security analysis on the actual surface that changed

### SymCC
Location: symbolic execution for compiled code

Purpose:
- analyze compiled code paths and identify conditions that trigger vulnerabilities
- complement static checks and fuzzing results

### Ghidra
Location: reverse engineering and binary analysis layer

Purpose:
- inspect external components, imported binaries, and plugin behavior
- review trust boundaries and upstream dependency behavior

### angr
Location: binary symbolic execution layer

Purpose:
- model execution paths and security bugs in compiled components
- evaluate complex control-flow conditions not visible in pure source review

### Triton
Location: dynamic symbolic execution layer

Purpose:
- instrument execution to reason about runtime state and security-critical paths
- support deeper analysis of unsafe and exploitable code paths

### KLEE
Location: symbolic execution and test generation layer

Purpose:
- generate edge-case inputs for parsers and logic-rich components
- validate behavior under tricky inputs and security constraints

### Tamarin Prover
Location: protocol verification layer

Purpose:
- prove properties of secure protocols and authentication flows
- validate the correctness of protocol logic before live rollout

### ProVerif
Location: protocol and cryptographic verification layer

Purpose:
- model authentication and secrecy properties for the system’s communication boundaries
- validate that live protocol interactions preserve security properties

## Placement in the program

- security CI pipeline: LibAFL, SymCC, KLEE, Snapchange
- external dependency review: Ghidra, angr, Triton
- protocol verification: Tamarin Prover, ProVerif

## Live behavior

These tools operate primarily in validation and review, not in the steady-state user path. Their role is to continuously challenge the system before and during deployment changes.

## Real-data readiness

They are not direct runtime dependencies for the launcher, but they are essential for safe real-data production adoption.
