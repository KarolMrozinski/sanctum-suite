# Confidential Computing attestation

Sanctum's production gate supports a Trustee-backed JSON claims gateway for AMD
SEV-SNP and Intel TDX workloads. Trustee's Attestation Service verifies
platform evidence; the gateway translates its verified result to the narrow
response contract below. The gateway is a separate, operator-managed service:
this repository does not contain Trustee, a TEE evidence collector, platform
endorsement certificates, or a claims gateway implementation.

The service workload must run inside the confidential guest being measured.
An ordinary container does not become a confidential VM because this client is
configured. Use a Trustee deployment appropriate for the target platform and
air-gapped certificate/collateral management process.

## Gateway trust and claims

Configure the gateway to verify the platform certificate chain, signature,
TCB/revocation status, platform-specific evidence, and the challenge-bound
workload identity. It must obtain measurement and workload-digest claims from
verified evidence; it must not trust those values from an unauthenticated
request field. Bind the fresh `challenge` and exact `workload_id` to evidence
inside the attested guest, and reject debug-enabled guests. Return exactly one
platform (`snp` or `tdx`) per verification; the combined label `snp_tdx` is not
accepted.

The gateway's HTTPS listener must require mutual TLS. Sanctum sends:

```json
{
  "workload_id": "sanctum-api-prod",
  "challenge": "<fresh random value>"
}
```

For each request the gateway returns a JSON object with this contract:

```json
{
  "status": "PASS",
  "tee_type": "snp",
  "workload_id": "sanctum-api-prod",
  "challenge": "<same fresh random value>",
  "measurement": "<96 hexadecimal SHA-384 characters>",
  "workload_digest": "<64 hexadecimal SHA-256 characters>",
  "debug_enabled": false,
  "verified_at": "2026-10-19T15:00:00Z",
  "evidence_sig": "valid"
}
```

`evidence_sig: "valid"` is the authenticated gateway's assertion that the
platform evidence signature was verified; it is not itself a digital
signature. TLS server verification and mTLS client authentication are
mandatory. Sanctum rejects a different workload/challenge, unsupported TEE
type, failed evidence status, invalid signature assertion, debug-enabled
claims, malformed or unapproved measurements/digests, and stale/future-dated
results.

Set `SANCTUM_TEE_EXPECTED_CLAIMS_FILE` to a read-only JSON file containing
operator-approved baselines for **both** platforms:

```json
{
  "snp": {
    "measurement_sha384": ["<approved 96-character SHA-384 measurement>"],
    "workload_digest_sha256": ["<approved 64-character SHA-256 digest>"]
  },
  "tdx": {
    "measurement_sha384": ["<approved 96-character SHA-384 measurement>"],
    "workload_digest_sha256": ["<approved 64-character SHA-256 digest>"]
  }
}
```

Replace every placeholder with measured, independently reviewed values before
production. The allowlist is capped at 64 KiB and requires at least one
measurement and workload digest for each platform. Multiple entries can
support an approved rollout, but broaden them only through change control.
Missing or malformed baselines block readiness and protected API operations.

## Service configuration

| Variable | Purpose |
| --- | --- |
| `SANCTUM_TEE_VERIFIER_URL` | Full HTTPS URL of the JSON claims gateway, such as `https://trustee-gateway.internal/api/v1/attestation/verify` |
| `SANCTUM_TEE_WORKLOAD_ID` | Exact workload identity expected by the gateway |
| `SANCTUM_TEE_CA_CERT_FILE` | Trusted gateway CA bundle |
| `SANCTUM_TEE_CLIENT_CERT_FILE` | mTLS client certificate |
| `SANCTUM_TEE_CLIENT_KEY_FILE` | Matching protected mTLS private key |
| `SANCTUM_TEE_EXPECTED_CLAIMS_FILE` | Read-only SNP/TDX measurement and workload-digest allowlist |
| `SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS` | Maximum age of `verified_at`; default 120 seconds, allowed 10-3600 |

The client posts to the exact configured URL, does not follow redirects, uses
a 5-second timeout, and caps responses at 32 KiB. Readiness and every
authenticated `/api/v1` request obtain a new challenge and fail closed on
configuration, TLS, gateway, freshness, or claims errors. The access audit
records `trustee` as part of the authorization engine. A fresh TPM/Measured
Boot quote from Keylime remains a separate mandatory production gate.

The [Docker Compose profile](../docker-compose.yml) mounts the CA,
certificate, key, and claims allowlist as read-only files. Supply
`SANCTUM_TEE_VERIFIER_CA_SOURCE`, `SANCTUM_TEE_CLIENT_CERT_SOURCE`,
`SANCTUM_TEE_CLIENT_KEY_SOURCE`, and `SANCTUM_TEE_EXPECTED_CLAIMS_SOURCE`.
For rootless Podman, create equivalent secrets and mount them at the paths in
the [air-gapped deployment guide](./PODMAN_AIRGAP.md).

Neither a passing client test nor this gateway contract proves that the
gateway actually implements cryptographic verification correctly. Independently
review its Trustee integration, platform collateral/endorsement update
process, debug policy, workload-digest binding, challenge handling, TCB
revocation behavior, and network isolation. Confidential Computing reduces
some host/administrator visibility into guest memory but does not protect
against malicious guest code, all side channels, TEE hardware flaws, or
incorrect application policy. It is not certification or authorization to
process classified data.
