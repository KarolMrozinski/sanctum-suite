# Stage 03 — runtime isolation and confidential workloads

This stage isolates workloads so sensitive processing can happen behind a trusted execution boundary.

## Technologies

### Kata Containers
Location: workload isolation layer

Purpose:
- isolate workloads in lightweight VM boundaries
- keep untrusted components separated from the main runtime

### Confidential Containers (Coco)
Location: confidential workload orchestration layer

Purpose:
- run workloads under confidential-computing controls
- bind workload execution to attestation and measured trust state

### Asterinas
Location: operating-system-level isolation layer

Purpose:
- provide a hardened runtime foundation for constrained workloads
- reduce the attack surface of system execution paths

### Gramine
Location: enclave-friendly application isolation

Purpose:
- run secure applications in a reduced-trust environment
- reduce the impact of host-level compromise on the workload

### Occlum
Location: enclave and minimal runtime layer

Purpose:
- provide a library OS model for trusted execution use cases
- allow sensitive tasks to run with a smaller runtime surface area

### CHERI
Location: capability-based security boundary

Purpose:
- improve memory safety and reduce pointer misuse risk
- support stronger memory compartmentalization

### Arm Morello
Location: ARM capability-based secure platform layer

Purpose:
- enable capability-aware hardware-enforced security
- align high-assurance workloads with capability-based memory boundaries

### Arm MTE
Location: memory tagging and runtime integrity layer

Purpose:
- detect memory corruption and misuse during execution
- strengthen protection of critical software paths

### Intel TDX
Location: confidential VM boundary

Purpose:
- provide hardware-backed isolated execution for sensitive workloads
- combine with attestation and measured boot validation

### AMD SEV
Location: confidential compute layer for AMD hardware

Purpose:
- isolate VM memory from the host and hypervisor
- provide a firmware-backed confidential execution model

### AMD SEV-SNP
Location: hardened confidential VM layer

Purpose:
- provide stronger memory integrity guarantees for confidential VM execution
- support attestation flows with stronger integrity claims

### Arm CCA
Location: ARM confidential compute boundary

Purpose:
- enable secure execution domains with strong hardware separation
- make privileged workloads more trustable under attestation rules

### seL4
Location: microkernel and trusted execution boundary

Purpose:
- provide a minimal, formally reviewed kernel model
- reduce kernel attack surface for privileged operations

## Placement in the program

- untrusted or external integrations: Kata Containers or Coco
- sensitive service execution: TDX, SEV-SNP, Arm CCA, Gramine, Occlum, seL4
- memory integrity protection: CHERI, Morello, Arm MTE

## Live behavior

Sensitive components should run in a restricted environment where:

- the host cannot read memory directly
- attestation must pass before execution is accepted
- runtime policies are enforced before data is processed or exported

## Real-data readiness

This stage is what makes the platform ready for real sensitive workloads rather than demo-only execution.
