# Differentially private verifiable credentials

The experimental `POST /api/v1/privacy/credentials` endpoint releases a bounded
category histogram as a signed W3C Verifiable Credential JWT. It combines:

- the subject-level discrete Laplace mechanism, with `add_remove` adjacency and a maximum
  of one category contribution per subject (`L1` sensitivity 1);
- a persisted, sequentially composed epsilon budget per stable `dataset_id`;
- an Ed25519 VC-JWT issuer identified by a self-certifying `did:key`.

This is an MVP integration, not a privacy certification or production identity
system. The implementation does not use Halo2, Plonky2, Nova, ML-KEM, or ML-DSA.
The credential is signed with classical Ed25519, so it is not post-quantum.

## Configuration

Configure the API key using the existing API setup, plus:

| Variable | Required | Description |
|---|---|---|
| `SANCTUM_DP_VC_ED25519_PRIVATE_KEY` | Yes | Standard Base64 encoding of exactly 32 raw Ed25519 private-key bytes. Supply it via a secret manager; never commit it or put it in a request. |
| `SANCTUM_PRIVACY_BUDGET_DB` | Production | Persistent SQLite file for epsilon accounting. Production fails closed if it is omitted. |
| `SANCTUM_DP_MAX_EPSILON` | No | Per-dataset cumulative epsilon limit; defaults to `3`. Must be greater than `0` and at most `100`. |

In non-production environments the budget database defaults to
`sanctum_privacy_budget.sqlite3`. Keep this database on durable storage and
include it in protected backups: deleting or restoring an older copy resets
accounting and can invalidate the privacy guarantee. The SQLite budget ledger
is intended for a single API instance. Do not run multiple replicas with
independent local budget files. Restrict write access and protect the ledger's
integrity: this SQLite prototype is not tamper-evident, and unauthorized edits
or rollback can undercount spent privacy budget.

Use one stable, non-sensitive `dataset_id` for all releases from the same
underlying dataset. The service stores only a namespaced SHA-256 digest of that
identifier, but it cannot detect when an operator uses different identifiers
for the same data. Budget consumption uses basic sequential composition: each
successful release adds its requested epsilon to the dataset's total.

## Request

The endpoint requires `X-API-Key`. Categories must be a fixed, public taxonomy
selected before examining the data. Each subject may appear at most once, with
one category; duplicate subject IDs are rejected rather than counted twice.
Normalize subject identifiers before submission so one person cannot appear
under multiple identifiers.

```json
{
  "dataset_id": "quarterly-audit-2026-q3",
  "categories": ["critical", "high", "medium", "low"],
  "observations": [
    {"subject_id": "internal-subject-001", "category": "high"},
    {"subject_id": "internal-subject-002", "category": "medium"}
  ],
  "epsilon": 0.5
}
```

`epsilon` must be at least `0.01` and at most `1` for each release. A successful
response contains `issuer_did`, its `did_document`, a compact
`credential_jwt`, its SHA-256 digest, the remaining budget, and limitations.
Verify a credential in Python:

```python
from sanctum_suite.core.privacy_credentials import verify_credential_jwt

payload = verify_credential_jwt(credential_jwt)
print(payload["vc"]["credentialSubject"]["categoryCounts"])
```

The credential contains only the noisy histogram, an opaque hash of the
dataset identifier, and privacy parameters. Raw subject identifiers and raw
counts are not persisted in the privacy-budget database or included in the
credential. Histograms are post-processed to non-negative numbers; this does
not weaken the differential-privacy guarantee.

## Limitations and deployment cautions

- Differential privacy applies only if the same dataset is consistently
  identified and the budget database is durable and shared by all issuers.
  Operators are responsible for defining the dataset boundary, stable ID, and
  canonical subject identifiers.
- The category taxonomy is public by contract. Data-dependent or sensitive
  labels can disclose information outside the histogram guarantee.
- The epsilon budget is not a privacy accountant for other systems or releases.
  This prototype uses a two-sided geometric (discrete Laplace) mechanism with
  `q >= exp(-epsilon)`, pure epsilon-DP, `delta = 0`, and basic sequential
  composition; it does not provide formal review of the source data.
- `did:key` embeds the issuer public key and needs no external resolver, but
  offers no key rotation, revocation, service endpoints, or issuer governance.
  The API does not provide a credential-status list.
- The compact signed credential uses Ed25519 (`EdDSA`) and can be independently
  verified from its `did:key`. It is not post-quantum and has not been checked
  for interoperability with external VC wallets or conformance suites.
- Protect and rotate the issuer key through an approved secret-management
  process. Changing keys changes the issuer DID; it does not reset the epsilon
  ledger.
- This endpoint is API-key protected and does not implement per-tenant budget
  isolation. Restrict callers and dataset IDs accordingly.

The module can also be used directly as a Python library through
`DifferentialPrivacyCredentialIssuer`; see
[`test_privacy_credentials.py`](../src/sanctum_suite/tests/test_privacy_credentials.py)
for executable examples.
