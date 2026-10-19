# Specialized security workflows

These workflows produce bounded review artifacts. None of them discovers a production cryptographic deployment, enforces a kernel policy, operates a physical data diode, or certifies TEMPEST/SDIP-27.

## Sigstore / Cosign artifact verification

`sanctum supply-chain-verify` verifies a local artifact's Sigstore DSSE in-toto attestation by invoking the installed Cosign CLI. It requires the exact expected certificate identity, OIDC issuer, and predicate type; it does not accept an implicit signer identity. Cosign must support `verify-blob-attestation --new-bundle-format`, and the supplied bundle must contain a `dsseEnvelope`. The verifier additionally checks that the decoded in-toto statement has a supported Statement v0.1/v1 type, the requested predicate type, and a SHA-256 subject digest matching the local artifact.

Optional Trivy and Grype JSON reports are parsed and summarized, not executed, authenticated, or cryptographically bound to the artifact. Missing reports are labeled `NOT_PROVIDED`; report data cannot establish that a scan was complete or that it covered this artifact. Findings are reported only: the command does not apply a vulnerability threshold or provide a clean/secure verdict. Obtain the bundle, scan outputs, and expected signer identity through independently trusted release procedures.

```powershell
sanctum supply-chain-verify `
  --artifact .\release\sanctum-suite.whl `
  --attestation-bundle .\release\sanctum-suite.whl.sigstore.json `
  --certificate-identity "https://github.com/OWNER/REPOSITORY/.github/workflows/release.yml@refs/tags/v1.2.3" `
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" `
  --predicate-type "https://slsa.dev/provenance/v1" `
  --trivy-report .\release\trivy-report.json `
  --grype-report .\release\grype-report.json
```

Trivy and Grype reports must be their respective JSON output formats. This CLI does not download attestations from GitHub or registries, create signatures, run either scanner, verify the reports' authenticity, or convert the repository's existing `gh attestation verify` workflow into a Cosign bundle. GitHub artifact attestations and Cosign bundles are not assumed interchangeable: use an explicitly supported bundle export and independently verify the expected identity/issuer before relying on it. A successful Cosign check authenticates the attestation under the specified trust policy; it does not establish that the build, source, SBOM, or scanner results are trustworthy or complete.

## Cross-technology security readiness

Run `sanctum security-readiness --input readiness.json` to produce a JSON summary of operator-reported checks for eBPF, Rust, SPIFFE/SPIRE, and cryptographic inventory. The input is a UTF-8 JSON object, limited to 1 MiB. Sections may be omitted; omitted domains are reported as `NOT_ASSESSED`. Boolean checks that are missing are reported as `INCOMPLETE`, and a declared `false` is reported as an operator-reported gap. The report does not verify any declaration or award a readiness score.

```json
{
  "ebpf": {
    "kernel_compatibility_checked": true,
    "verifier_tests_passed": true,
    "hook_coverage_reviewed": true,
    "fail_mode_documented": true,
    "performance_tested": false,
    "detach_rollback_tested": true
  },
  "rust": {
    "cargo_lock_reviewed": true,
    "cargo_audit_passed": true,
    "unsafe_code_reviewed": true,
    "sbom_available": true
  },
  "spiffe": {
    "trust_domain_configured": true,
    "svid_rotation_tested": true,
    "workload_api_access_controlled": true,
    "mtls_enforced": true,
    "authorization_policy_reviewed": true
  },
  "cryptography": {
    "inventory": [
      {
        "algorithm": "PQXDH",
        "location": "messaging-service",
        "use_case": "key_establishment"
      }
    ]
  }
}
```

Run the example with:

```powershell
sanctum security-readiness --input .\readiness.json
```

The `ebpf`, `rust`, and `spiffe` sections accept only the boolean fields shown above. A crypto inventory contains at most 1,000 entries and uses the `algorithm`, `location`, `use_case`, and optional `requires_long_term_confidentiality` fields described below. `PQXDH` is reported as a key-establishment protocol requiring specification, implementation, and interoperability review; it is not labeled as a NIST-standardized algorithm. This command does not inspect a kernel or Rust workspace, connect to SPIRE, validate an SVID or mTLS session, or discover cryptographic use. Use independently collected evidence and qualified review before relying on any reported result.

## PQC inventory and migration review

Create a UTF-8 JSON array from an approved inventory source. Each row requires `algorithm` and `location`; optional `use_case` accepts `key_establishment`, `digital_signature`, `other`, or `unknown`. Set `requires_long_term_confidentiality` to `true` only when the data owner has confirmed the requirement.

```json
[
  {
    "algorithm": "ECDH-P256",
    "location": "archive-transfer-service",
    "use_case": "key_establishment",
    "requires_long_term_confidentiality": true
  },
  {
    "algorithm": "ML-KEM-768",
    "location": "new-service",
    "use_case": "key_establishment"
  }
]
```

Run:

```powershell
sanctum pqc-inventory --inventory "C:\Lab\crypto-inventory.json"
```

The command accepts at most 1,000 entries in a 1 MiB JSON file. It classifies recognized ML-KEM, ML-DSA, and SLH-DSA family names against NIST FIPS 203/204/205 and reports classical public-key algorithms and unknown names for review. `PQXDH` is identified as a reported key-establishment protocol and requires separate review of the selected specification, implementation, and interoperability; it is not a NIST-standardized algorithm. A classical key-establishment entry marked as requiring long-term confidentiality is flagged to prioritize a harvest-now/decrypt-later review. This is an explicitly supplied inventory and triage hint, not cryptographic discovery, implementation validation, migration advice for a specific system, or a compliance determination. Confirm algorithm variants, parameter sets, implementation, protocol negotiation, key lifecycle, hybrid transition, interoperability, and rollback with system owners and qualified cryptographic engineers.

## Hybrid PQC signatures and encrypted checkpoint files

New audit checkpoints are dual-signed with RSA-PSS/SHA-256 and NIST ML-DSA-65. Both signatures cover the same canonical checkpoint bytes, and verification requires independently trusted public keys for both algorithms. Legacy RSA-PSS checkpoints remain verifiable. In development, `SecurityReportSigner` creates local ML-DSA-65 keys beside its RSA keys. Production checkpoint signing requires the existing RSA key pair plus `SANCTUM_REPORT_SIGNING_MLDSA_PRIVATE_KEY_FILE` and `SANCTUM_REPORT_SIGNING_MLDSA_PUBLIC_KEY_FILE`; the private-key file contains the raw 32-byte ML-DSA-65 seed and the public-key file the raw ML-DSA-65 public key. Configure and retain the ML-DSA public key independently at each verifier.

ML-KEM is a key-encapsulation mechanism, not a signature. The `pqc-kem-keygen`, `pqc-encrypt` and `pqc-decrypt` commands implement an authenticated file envelope combining NIST ML-KEM-768 and X25519 through HKDF-SHA-256 and AES-256-GCM:

```powershell
sanctum pqc-kem-keygen --key-directory C:\secure\recipient-keys
sanctum pqc-encrypt `
  --input-file C:\secure\audit-checkpoint.json `
  --mlkem-public-key-file C:\secure\recipient-keys\mlkem768-public.bin `
  --x25519-public-key-file C:\secure\recipient-keys\x25519-public.bin `
  --output-file C:\secure\audit-checkpoint.json.hybrid.enc
sanctum pqc-decrypt `
  --input-file C:\secure\audit-checkpoint.json.hybrid.enc `
  --mlkem-private-key-file C:\secure\recipient-keys\mlkem768-private.bin `
  --x25519-private-key-file C:\secure\recipient-keys\x25519-private.bin `
  --output-file C:\secure\audit-checkpoint.json
```

This encrypts only the explicitly supplied file; it does not encrypt the exported audit archive, replace checkpoint signatures, protect recipient private keys, or authenticate a recipient identity. Independently verify the checkpoint after decryption, and protect the archive and key material using the deployment's separate access-control and backup procedures. The implementation uses the installed `cryptography` provider's standardized primitives but has not undergone an independent cryptographic review or certification.

## FHE accelerator, QKD, and self-healing integration boundaries

### FHE on GPU/FPGA

`sanctum fhe-accelerator-status` and `sanctum security-capabilities` report whether the SEAL Python binding and selected vendor runtime tools are present. Tool presence is not proof of a connected/attested accelerator. The existing Microsoft SEAL BFV path executes on CPU and explicitly labels its execution backend. `FHEAcceleratorBackend` is an injection contract for an independently validated adapter passed to `create_private_graph_bundle(..., fhe_backend=...)`; the repository does not include a GPU/FPGA implementation, automatically offload work, or claim a performance improvement. A backend must be reviewed for ciphertext correctness, side channels, device isolation, memory cleanup, provenance, and reproducible benchmarks before use.

### QKD key-provider adapter

`sanctum_suite.core.qkd.QKDKeyProvider` defines the vendor boundary for acquiring a key for an authenticated peer. The provider must implement peer authentication, key-ID uniqueness/replay prevention, access controls, key expiry, authenticated classical-channel protection and hardware-specific link monitoring. `QKDKeyMaterial` enforces a minimum key length and timezone-aware expiry; `derive_qkd_mlkem_hybrid_key` refuses expired material and derives a key from both the supplied QKD secret and a 32-byte ML-KEM shared secret. Keep the QKD key in memory only, use unique protocol context and salt, and follow the vendor's key-consumption/zeroization procedures. No QKD hardware, key manager, or vendor adapter is configured or simulated by this repository; `sanctum security-capabilities` therefore reports `NOT_CONFIGURED`.

### Human-approved remediation proposals

The self-healing workflow records proposed OPA policy updates and key rotations in a hash-linked, append-only SQLite journal. It stores evidence and proposed-change digests, not policy source or secret key material. A different operator must approve or reject the proposal:

```powershell
sanctum self-healing-propose `
  --database-file C:\secure\remediation.sqlite `
  --target-module sanctum.api.authz `
  --action opa_policy_update `
  --reason-code anomaly_detected `
  --evidence-sha256 "<64 lowercase hex characters>" `
  --current-policy-version policy-v1 `
  --proposed-change-sha256 "<64 lowercase hex characters>" `
  --created-by monitoring-service

sanctum self-healing-decide `
  --database-file C:\secure\remediation.sqlite `
  --proposal-id "<proposal UUID>" `
  --approver-id security-operator `
  --approve

sanctum self-healing-list --database-file C:\secure\remediation.sqlite
```

Approval is only authorization to proceed through a separate, reviewed deployment/rotation procedure; these commands never apply OPA policy, alter access control, isolate systems, hot-patch processes, or rotate keys. Store and back up the journal under separate controls: its local hash chain and SQLite triggers do not prevent an administrator from rewriting the database and recomputing the chain. There is no anomaly detector or local model runtime configured. `TEEAnomalyAssessmentProvider` is an integration contract only, and `sanctum security-capabilities` reports local TEE inference as `NOT_CONFIGURED`.

## Controlled offline-transfer manifest

`AirGapDataDiodeBroker.prepare_offline_package` hashes the payload and emits a canonical JSON manifest digest. If a signature and PEM public key are supplied, the signature is checked over the payload and the public key's DER SubjectPublicKeyInfo SHA-256 is recorded. The command/module does not move the payload; transfer it through the organization's approved offline process and verify the payload digest, signature, and independently trusted signer-key fingerprint at the receiving boundary. A valid signature from a supplied key does not establish key ownership or trust. The manifest digest is not a signature and does not authenticate the manifest by itself.

Record source and destination operator approvals, media identifier, malware/content review, chain of custody, scan results, and receipt verification in the organization's controlled process. This software cannot verify a one-way physical diode, prevent a return channel, establish an air gap, or attest to media sanitization.

## eBPF / runtime enforcement

`EbpfInKernelEnforcementEngine` returns an implementation checklist only. It does not inspect the running kernel, compile/load code, attach hooks, generate an EDR signal, or enforce policy. Before any separate implementation is considered, document kernel compatibility, BTF/capabilities, source and dependency review, verifier tests, hook coverage, fail-open/fail-closed behavior, performance/event-loss testing, and a tested detach/rollback procedure on a disposable host. The returned evidence flags are all false: they are not live checks.

Generated Cilium policies are also declarative until reviewed, tested, and applied by a separately authorized cluster workflow. Do not infer enforcement from the presence of a policy document.

## TEMPEST / NATO SDIP-27

The TEMPEST helper records reference presence only. It does not assess whether a report is authentic, the assessor is accredited, the applicable SDIP-27 edition is correct, or the zone is compliant. Measurements and interpretations require the appropriate qualified authority and controlled facilities. Do not submit classified or sensitive measurement material to this application; store only approved evidence references in accordance with organizational handling rules.
