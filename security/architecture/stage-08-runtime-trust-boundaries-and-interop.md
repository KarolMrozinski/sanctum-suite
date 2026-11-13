# Stage 08 — runtime trust boundaries and secure interop

This stage defines the live interop boundary between host runtime services, TEE-aware workloads, and policy enforcement layers, while keeping the repo buildable on Windows and Linux-ready for production deployment.

## Technologies

### vsock / Named Pipes / AF_HYPERV
Location: live transport boundary layer

Purpose:
- prefer `AF_VSOCK` on Linux host/guest or Hyper-V scenarios
- prefer Windows Named Pipes on native Windows runtime
- keep a common logical interface for secure, low-latency trust-boundary communication

### Cap'n Proto / FlatBuffers
Location: zero-copy and compact serialization layer

Purpose:
- provide versioned, efficient binary contracts for runtime envelopes and attestation payloads
- keep inter-service message layouts compatible and extensible for production data

### WIT / Wasmtime
Location: WebAssembly component interface layer

Purpose:
- define interfaces for secure runtime modules and component execution
- keep performance-critical and cross-language modules isolated behind typed boundaries

### Parsec / TPM 2.0 / TBS / NCrypt
Location: secure key and attestation interface layer

Purpose:
- expose hardware-backed key operations through a consistent API
- keep Windows-native access via TBS / NCrypt and Linux access through Parsec daemon equivalents

### OPA / Rego / SPIFFE / SPIRE / Trustee / EAR / Veraison / Keylime
Location: policy and attestation enforcement layer

Purpose:
- evaluate runtime trust decisions based on evidence and policy context
- issue SPIFFE identities and enforce policy decisions at runtime after attestation succeeds

### eBPF / KRSI / Tetragon / Cilium / Envoy / Linux Security Modules
Location: runtime filtering and enforcement layer

Purpose:
- enforce policy at the kernel and gateway boundary when Linux-native hooks are available
- provide mock or telemetry-based substitutes on Windows when the kernel hook is unavailable

## Placement in the program

- host <-> enclave transport: vsock / Named Pipes / AF_HYPERV
- message schema: Cap'n Proto, FlatBuffers
- component contracts: WIT / Wasmtime
- trust identity: SPIFFE, SPIRE, Trustee, EAR, Veraison, Keylime
- runtime enforcement: OPA/Rego, Envoy, eBPF, LSMs, Tetragon, Cilium
- security boundary mapping: data-agnostic and live-runtime ready

## Live behavior

The runtime layer should be able to:

- exchange telemetry and attestation evidence between Windows host and Linux/TEE-enabled boundary components
- process runtime payloads through typed contracts without embedding production data into the repo
- authorize or deny execution according to policy and evidence
- emit identity, trust, and enforcement data in a structured format ready for real streams

## Windows-native integration notes

This repo keeps Linux TEE modules optional. When a kernel-level hook is unavailable on Windows, the project uses a telemetry-driven emulation layer or structured mock boundary instead of hard-failing the build. The common interface remains the same across platforms to preserve cross-environment runtime contracts.

## Real-data readiness

This stage is designed to accept real operational telemetry and evidence, while staying data-agnostic in the repository by default.

## Local validation

From PowerShell on Windows:

```powershell
$env:BAZEL_SH = "C:/Program Files/Git/bin/bash.exe"
.\.bin\bazel.exe test //... --test_output=errors
```

This confirms the live trust-boundary layer remains integrated with the main Bazel graph and the repo remains testable as a hybrid Windows/Linux architecture.
