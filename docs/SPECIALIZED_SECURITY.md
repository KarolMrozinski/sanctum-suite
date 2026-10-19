# Specialized security workflows

These workflows produce bounded review artifacts. None of them discovers a production cryptographic deployment, enforces a kernel policy, operates a physical data diode, or certifies TEMPEST/SDIP-27.

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

The command accepts at most 1,000 entries in a 1 MiB JSON file. It classifies recognized ML-KEM, ML-DSA, and SLH-DSA family names against NIST FIPS 203/204/205 and reports classical public-key algorithms and unknown names for review. A classical key-establishment entry marked as requiring long-term confidentiality is flagged to prioritize a harvest-now/decrypt-later review. This is an explicitly supplied inventory and triage hint, not cryptographic discovery, implementation validation, migration advice for a specific system, or a compliance determination. Confirm algorithm variants, parameter sets, implementation, protocol negotiation, key lifecycle, hybrid transition, interoperability, and rollback with system owners and qualified cryptographic engineers.

## Controlled offline-transfer manifest

`AirGapDataDiodeBroker.prepare_offline_package` hashes the payload and emits a canonical JSON manifest digest. If a signature and PEM public key are supplied, the signature is checked over the payload and the public key's DER SubjectPublicKeyInfo SHA-256 is recorded. The command/module does not move the payload; transfer it through the organization's approved offline process and verify the payload digest, signature, and independently trusted signer-key fingerprint at the receiving boundary. A valid signature from a supplied key does not establish key ownership or trust. The manifest digest is not a signature and does not authenticate the manifest by itself.

Record source and destination operator approvals, media identifier, malware/content review, chain of custody, scan results, and receipt verification in the organization's controlled process. This software cannot verify a one-way physical diode, prevent a return channel, establish an air gap, or attest to media sanitization.

## eBPF / runtime enforcement

`EbpfInKernelEnforcementEngine` returns an implementation checklist only. It does not inspect the running kernel, compile/load code, attach hooks, generate an EDR signal, or enforce policy. Before any separate implementation is considered, document kernel compatibility, BTF/capabilities, source and dependency review, verifier tests, hook coverage, fail-open/fail-closed behavior, performance/event-loss testing, and a tested detach/rollback procedure on a disposable host. The returned evidence flags are all false: they are not live checks.

Generated Cilium policies are also declarative until reviewed, tested, and applied by a separately authorized cluster workflow. Do not infer enforcement from the presence of a policy document.

## TEMPEST / NATO SDIP-27

The TEMPEST helper records reference presence only. It does not assess whether a report is authentic, the assessor is accredited, the applicable SDIP-27 edition is correct, or the zone is compliant. Measurements and interpretations require the appropriate qualified authority and controlled facilities. Do not submit classified or sensitive measurement material to this application; store only approved evidence references in accordance with organizational handling rules.
