# Stage 08 — runtime trust boundaries and secure interop

This stage defines the communication and interoperability contracts between components that must be trusted, isolated, or externally connected.

## Technologies

### vsock
Location: virtualized inter-process communication layer

Purpose:
- provide efficient communication between VMs and host or guest boundary components
- support secure, bounded interactions across trusted execution boundaries

### Cap'n Proto
Location: efficient binary serialization and RPC layer

Purpose:
- provide low-overhead structured serialization across trusted internal services
- support fast IPC and inter-service communication where performance matters

### FlatBuffers
Location: compact binary schema layer

Purpose:
- define efficient cross-language data contracts
- support controlled interoperability for telemetry, policy payloads, and runtime messages

### WIT
Location: WebAssembly interface layer

Purpose:
- define component interfaces for Wasm modules and secure runtime boundaries
- support composable and cross-runtime interoperability

## Placement in the program

- inter-service communication: Cap'n Proto, FlatBuffers
- VM and host boundaries: vsock
- component interfaces: WIT
- runtime contracts: clear trust boundary and handshake expectations between workloads

## Live behavior

These technologies provide structured interop so that sensitive components can exchange messages without informal or ambiguous contracts.

## Real-data readiness

This stage makes the architecture ready for real multi-component communication, secure boundaries, and mixed-runtime trust models.
