# Supply Chain Policy

## Purpose

This policy defines the operating model for secure software delivery within SANCTUM-SUITE. It is intentionally plan-only and verification-first: the repository provides governance guidance and evidence requirements, but does not execute live cloud, runtime, or deployment actions by itself.

## Scope

This policy covers:

- artifact signing and provenance
- SBOM generation and maintenance
- vulnerability review and CVE mapping
- runtime security controls for containers / Kubernetes
- release verification gates and approval flows

## Policy statements

### 1. Artifact integrity

Every release artifact must be signed with a trusted identity and verified before promotion.

Required controls:

- OIDC-backed signing identity
- trusted certificate chain
- subject and issuer verification
- digest match against the intended artifact
- Rekor provenance review or equivalent transparency logging

### 2. Provenance and attestation

The release must include attestations that bind the artifact to the source revision, build metadata, and expected environment. Where applicable, in-toto attestations must be reviewed before acceptance.

### 3. Software bill of materials (SBOM)

Every release should provide an SBOM in a recognized format:

- CycloneDX: preferred for machine-readable supply-chain workflows, tooling integration, and vulnerability correlation
- SPDX: preferred for legal and compliance reporting, license tracking, and formal documentation requirements

Recommendation:

- Use CycloneDX for engineering and release automation
- Use SPDX for legal/compliance review and export-oriented reports
- For mixed reporting, generate both and cross-check them for consistency

### 4. Vulnerability and compliance mapping

The SBOM must be correlated to:

- package inventories
- known CVEs or advisory feeds
- asset criticality and business context
- compliance requirements and policy exceptions

Any unresolved critical or high vulnerability must be explicitly documented and approved before production promotion.

### 5. Runtime controls for workloads

Runtime controls must be aligned to workload type. At minimum, the project considers:

- API / web workloads: egress monitoring, sensitive file write detection, crypto misuse detection
- database workloads: credential access, unusual child process execution, suspicious network binding
- LLM / inference workloads: model artifact access, package manager execution, exfiltration patterns
- general workloads: shell invocation, tampering attempts, privilege escalation signals

Falco rule sets should be profile-driven and reviewed with namespace, service, and team ownership.

### 6. Release verification gates

Release gates must be treated as mandatory review checkpoints and not as optional best practices.

Required gate order:

1. Build artifact generated from approved source revision
2. Sign artifact with approved identity
3. Verify certificate, subject, issuer, and digest
4. Validate provenance and attestation
5. Generate and review SBOM
6. Match SBOM with CVE feeds and policy exceptions
7. Check runtime control coverage for workload profile
8. Obtain security and compliance approval
9. Promote only after all open issues are resolved or explicitly accepted

## Exceptions

Exceptions must be:

- time-bound
- owned by an accountable team or role
- documented with risk rationale
- accompanied by compensating controls
- reviewed before production promotion

## Evidence retention

Approved release evidence must be retained in an auditable, tamper-aware record. This includes:

- source revision and build metadata
- signature and attestation artifacts
- SBOM files and comparison outputs
- vulnerability review records
- runtime policy maps
- approval and exception records

## Related artifacts

- `SECURITY-REVIEW.md`
- `docs/release_policy_checklist.json`
- `README.md`
