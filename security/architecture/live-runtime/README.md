# Live runtime contracts

This directory hosts the first live-ready trust boundary for Sanctum Suite. It is intentionally separate from the desktop launcher and dashboard, so the runtime-only contracts can evolve without duplicating existing application files.

## Components

- `BUILD.bazel` — Bazel metadata for the runtime contract surface.
- `idl/runtime-trust.capnp` — schema for the runtime envelope and attestation record.
- `streams/vsock-runtime.cue` — declarative stream topology for host/enclave policy flows.

## Trust-flow model

1. Host and enclave establish a `AF_VSOCK` path.
2. Runtime payloads are wrapped in a typed `RuntimeEnvelope`.
3. Attestation evidence is attached to each message.
4. Policy decisions are evaluated by OPA and enforcement layers.
5. Contracts remain data-agnostic and ready for production data injection.

## Verification

Run the lightweight repo validation from the root:

```bash
bazel query //security/architecture/live-runtime:all
```

If the project is being exercised through a reproducible Nix shell:

```bash
nix develop -c bazel query //security/architecture/live-runtime:all
```

The query confirms that the build graph contains the runtime contract layer, while the Cap'n Proto and CUE files maintain the live contract definitions without hardcoded production payloads.
