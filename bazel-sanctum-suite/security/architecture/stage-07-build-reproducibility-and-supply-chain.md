# Stage 07 — build reproducibility and software supply chain

This stage tightens the build and provenance chain around the existing Bazel/Nix foundation without duplicating any of the project’s current build files.

## Technologies

### Bazel / Bazel Remote / BuildBuddy / NativeLink / Buildifier / Buildozer
Location: incremental, hermetic build graph and toolchain automation layer

Purpose:
- enforce hermetic build execution for the repo
- support incremental validation and remote caching for local and CI builds
- automate build file maintenance while keeping the project graph reproducible and reviewable

### Alire / GPRbuild
Location: Ada/SPARK toolchain integration layer

Purpose:
- keep Ada and SPARK builds reproducible in the same monorepo flow
- integrate with Bazel-compatible local validation for formal-check entry points and generated artefacts

### Gazelle
Location: Bazel dependency generation layer

Purpose:
- auto-generate Bazel build metadata for new source trees
- keep the repo graph aligned with actual source layouts without manual duplication

### Buildifier / Buildozer
Location: build-file formatting and mutation layer

Purpose:
- ensure Bazel files remain consistent and machine-reviewable
- keep the repo’s build metadata deterministic across automation and CI操作

### Nix Flakes / CUE
Location: environment and configuration contract layer

Purpose:
- freeze toolchain versions and shell inputs
- validate directory structure and configuration semantics before release or deployment

### in-toto / SLSA
Location: supply-chain attestation and provenance layer

Purpose:
- bind build outputs to source and environment provenance
- provide verifiable material for release and material-trace confidence

### Trustee / EAR / Parsec
Location: trust decision and security service layer

Purpose:
- bridge attestation results to policy and runtime trust decisions
- provide a production-ready interface for secure key and policy operations in hybrid Windows/Linux deployments

## Placement in the program

- monorepo automation and graph hygiene: Bazel, Gazelle, Buildifier, Buildozer, Bazel Diff, remote cache integrations
- language toolchains: Alire, GPRbuild, GNAT, SPARK, Rust, Wasmtime
- environment reproducibility: Nix Flakes, CUE
- release evidence and provenance: in-toto, SLSA, Trustee, EAR, Parsec

## Live behavior

The system should be able to answer before any artifact is accepted:

- Was the source tree consistent with the generated build graph?
- Was the toolchain environment reproducible?
- Was the build signed and provenance-attested?
- Did the runtime trust layer accept the evidence and policy chain?

## Real-data readiness

The pipeline is intentionally data-agnostic and ready to attach real provenance, release metadata, and runtime evidence without hardcoded production payloads.

## Windows-native integration notes

This repo remains buildable on Windows through Bazel + MSVC while preserving a Linux-ready path via Nix and optional TEE modules. The active logic is:

- use Bazel for the repo graph and local validation
- use Nix Flakes for hermetic shell reproducibility when available
- keep Linux-targeted trust features under conditional compilation or emulation layers rather than direct runtime assumptions

## Local validation

From PowerShell on Windows:

```powershell
$env:BAZEL_SH = "C:/Program Files/Git/bin/bash.exe"
.\.bin\bazel.exe test //... --test_output=errors
```

This validates the repo graph and confirms the staged reproducibility layer remains integrated with the rest of the monorepo.
