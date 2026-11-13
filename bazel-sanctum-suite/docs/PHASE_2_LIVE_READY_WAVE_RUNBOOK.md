# Phase 2 Live Ready Runbook: BAM + HIRS + paccor + RIM

## Scope
This is the second operational wave for SANCTUM-SUITE. It covers:
- BAM (Binary Analysis Metadata)
- HIRS (Host Integrity at Runtime and Start-up)
- paccor (Platform Attribute Certificate Creator)
- RIM-Tool (Reference Integrity Manifest)

## Preconditions
- [ ] `SANCTUM_BAM_METADATA_PATH` points to a valid metadata source or artifact store
- [ ] `SANCTUM_HIRS_API_URL` is reachable over TLS with a valid trust chain
- [ ] `SANCTUM_PACCOR_API_URL` is reachable and authenticated
- [ ] `SANCTUM_RIM_MANIFEST_PATH` or remote endpoint is available and readable
- [ ] `SANCTUM_AUTHORIZED_TARGETS` contains only explicit hostnames and ports
- [ ] Secret store contains token values and certificates

## Required env vars
- [ ] `SANCTUM_BAM_METADATA_PATH`
- [ ] `SANCTUM_BAM_API_TOKEN`
- [ ] `SANCTUM_HIRS_API_URL`
- [ ] `SANCTUM_HIRS_API_TOKEN`
- [ ] `SANCTUM_PACCOR_CERT_SUBJECT`
- [ ] `SANCTUM_PACCOR_API_URL`
- [ ] `SANCTUM_PACCOR_TOKEN`
- [ ] `SANCTUM_RIM_MANIFEST_PATH`
- [ ] `SANCTUM_RIM_API_URL`
- [ ] `SANCTUM_RIM_TOKEN`

## Readiness gates
- [ ] BAM metadata can be introspected and checksum-validated
- [ ] HIRS attestation endpoint returns a live attestation response
- [ ] paccor issues a certificate with the approved subject naming
- [ ] RIM manifest is readable and integrity-validated
- [ ] Evidence is normalized to the capability schema
- [ ] API status returns `READY` only after the checks pass

## Payloads
### BAM
```json
{
  "capability_id": "security-capability:binary-metadata",
  "status": "READY",
  "evidence": {
    "artifact_sha256": "...",
    "metadata_source": "/var/lib/sanctum/bam/metadata.json",
    "vendor": "example",
    "image_hash": "..."
  }
}
```

### HIRS
```json
{
  "capability_id": "security-capability:runtime-attestation",
  "status": "READY",
  "evidence": {
    "boot_measurements": ["..."],
    "runtime_state": "verified",
    "attestation_claims": {"status": "valid"}
  }
}
```

### paccor
```json
{
  "capability_id": "security-capability:platform-certificate",
  "status": "READY",
  "evidence": {
    "certificate_subject": "CN=sanctum-edge-prod,O=Sanctum",
    "issuer": "internal-pki",
    "issued_at": "2026-10-22T22:00:00Z"
  }
}
```

### RIM
```json
{
  "capability_id": "security-capability:integrity-manifest",
  "status": "READY",
  "evidence": {
    "manifest_digest": "sha256:...",
    "reference_set": ["artifact-1", "artifact-2"],
    "verification_status": "valid"
  }
}
```
