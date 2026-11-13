# TEE-gated private-ledger checkpoint anchoring

`sanctum ledger-anchor` verifies an existing signed audit checkpoint and its
exported records, obtains a fresh TEE attestation, then submits only the exact
checkpoint-file SHA-256 digest and minimal anchor metadata to a ledger. It
never uploads the checkpoint, archive records, identities, workload
measurements, or the attestation response.

The feature can accept an operator-approved AMD SEV-SNP or Intel SGX
measurement. A single invocation runs on one platform and requires one fresh
passing attestation; it does not require impossible simultaneous SNP and SGX
hardware. The existing TEE claims client can also accept SGX claims from an
operator-managed gateway that verifies Intel DCAP quotes. See
[`CONFIDENTIAL_COMPUTING.md`](./CONFIDENTIAL_COMPUTING.md) for the gateway
contract and platform-specific measurement formats.

## Before anchoring

1. Create and independently verify an audit checkpoint using the existing
   [`audit-checkpoint` and `audit-verify` procedures](./INSTALLATION.md#minio-immutable-access-audit).
   Keep the signed checkpoint, archive and trusted public key under separate
   access controls.
2. Configure the required TEE gateway, its mutual-TLS credentials, workload
   ID, freshness limit and read-only measurement allowlist. The verifier must
   bind each fresh challenge, workload ID and checkpoint digest to verified
   SNP evidence or an SGX DCAP quote. The digest is carried as
   `operation_digest`; see the exact report-data binding requirement in
   [`CONFIDENTIAL_COMPUTING.md`](./CONFIDENTIAL_COMPUTING.md). Sanctum only
   trusts the verifier's authenticated claims; it does not parse or validate
   raw SNP reports or SGX quotes itself.
3. Choose either the local demonstration ledger or the Fabric gateway. Both
   backends receive exactly:

   ```json
   {
     "schema_version": 1,
     "checkpoint_sha256": "<64 lowercase hexadecimal characters>",
     "anchored_at": "<UTC timestamp>"
   }
   ```

   The SHA-256 is over the exact checkpoint file bytes. No audit record or
   checkpoint content is included.

## Local demonstration ledger

The local backend stores anchors in SQLite and appends a hash-linked sequence.
Database triggers reject ordinary row updates/deletes; `ledger-verify` checks
the complete current sequence and returns an RFC 6962 SHA-256 Merkle tree head.
`ledger-consistency` returns an RFC 6962 consistency proof from an earlier
tree head to the current one. Retain the old tree size and root outside the
ledger, and verify the proof with
`sanctum_suite.core.audit_chain.verify_merkle_consistency_proof` before
accepting the new head. A failed proof detects a rewritten or truncated prefix
relative to that independently retained head.

This is a local integrity demonstration only: it has no distributed
consensus, independent witnesses, hardware-backed immutability, or protection
from an administrator who can rewrite the database and its chain. It cannot
prove that a database suffix was not removed unless a prior tree head was
retained independently. Merkle proofs do not themselves publish, sign, or
timestamp tree heads; use an independently operated witness or transparency
service for cross-organization monitoring.

```powershell
sanctum ledger-anchor `
  --checkpoint-file C:\secure\audit-checkpoint.json `
  --archive-directory C:\secure\audit-archive `
  --checkpoint-public-key-file C:\trusted\report-signing-public.pem `
  --checkpoint-pqc-public-key-file C:\trusted\sanctum-mldsa65-public.bin `
  --backend local `
  --database-file C:\secure\private-ledger.sqlite

sanctum ledger-verify --database-file C:\secure\private-ledger.sqlite
```

Repeating an anchor for an existing checkpoint digest is idempotent and
returns the original sequence entry. Save the `tree_size` and
`tree_root_sha256` from a verified result in a separately controlled system,
then request a consistency proof after new anchors are added:

```powershell
sanctum ledger-consistency `
  --database-file C:\secure\private-ledger.sqlite `
  --old-tree-size 25 `
  --old-tree-root-sha256 "<previously-retained-root>"
```

The result contains the old/new tree heads and the proof nodes. The verifier
must independently confirm the proof and retain the accepted new tree head;
do not trust a root supplied only by the same ledger operator.

## Hyperledger Fabric gateway

Sanctum uses a small, operator-managed HTTPS/mTLS gateway in front of the
Hyperledger Fabric Gateway API. The repository does **not** bundle Fabric
peers/orderers, chaincode, Fabric CA, or that HTTP adapter. Deploy and
independently review those components. The adapter's chaincode operation must
store only the schema version, digest and supplied timestamp; it must reject
additional client fields and treat a repeated digest idempotently. It must
return success only after Fabric confirms the transaction committed, not
merely submitted.

The adapter implements this contract:

- `POST /api/v1/channels/{channel}/chaincodes/{chaincode}/anchors`
- Request body is the three-field JSON anchor shown above.
- `Idempotency-Key` equals `checkpoint_sha256`.
- On commit, return HTTP `201` (or `200`) and
  `{"status":"COMMITTED","checkpoint_sha256":"<same digest>","tx_id":"<transaction id>"}`.
- Reject any other anchor fields. Do not accept audit payloads on this route.

Configure mutual TLS and channel/chaincode names using protected deployment
configuration:

```powershell
$env:SANCTUM_LEDGER_FABRIC_GATEWAY_URL = "https://fabric-gateway.internal"
$env:SANCTUM_LEDGER_FABRIC_CHANNEL = "audit"
$env:SANCTUM_LEDGER_FABRIC_CHAINCODE = "checkpoint-anchor"
$env:SANCTUM_LEDGER_FABRIC_CA_FILE = "C:\secure\fabric-ca.pem"
$env:SANCTUM_LEDGER_FABRIC_CLIENT_CERT_FILE = "C:\secure\fabric-client.pem"
$env:SANCTUM_LEDGER_FABRIC_CLIENT_KEY_FILE = "C:\secure\fabric-client-key.pem"
```

```powershell
sanctum ledger-anchor `
  --checkpoint-file C:\secure\audit-checkpoint.json `
  --archive-directory C:\secure\audit-archive `
  --checkpoint-public-key-file C:\trusted\report-signing-public.pem `
  --checkpoint-pqc-public-key-file C:\trusted\sanctum-mldsa65-public.bin `
  --backend fabric
```

TLS verification is mandatory, redirects are not followed, responses are
size-limited, and the returned digest must match the requested checkpoint
before success is reported. Treat the returned transaction ID as a locator,
not a proof of Fabric membership by itself; use an independently trusted
Fabric peer or block-verification procedure when verifying ledger inclusion.

## Operational limits

- The CLI verifies the checkpoint signature and exported audit archive before
  requesting TEE attestation or contacting the ledger; invalid inputs fail
  closed without submission.
- The TEE result gates the operation but is **not written to the ledger**.
  Workload IDs, SGX MRENCLAVE, SNP measurements, report contents and event
  details stay out of ledger transaction input.
- The enclave/gateway must independently enforce that it only emits evidence
  bound to a checkpoint digest after its approved workload checks. The Python
  client verifies the signed audit checkpoint outside the TEE and cannot prove
  that verification or the ledger write executed inside confidential hardware.
- Freshness is checked by the configured claims client on every invocation.
  SGX support depends on an external verifier correctly validating the DCAP
  quote, QE identity, TCB/revocation state, report data and debug status.
- Fabric ledger transaction time and consensus evidence are provided by the
  Fabric deployment, not this Python client. Review chaincode authorization,
  endorsement policy, identities, ordering service, backups, privacy
  collections and retention before production.
- Automated tests exercise SQLite and a mocked Fabric gateway; they do not
  validate a live Fabric network, chaincode, verifier, DCAP collateral, or
  physical TEE hardware.
