# On-chain data foundation

SANCTUM-SUITE provides an experimental, read-only foundation for fetching
Bitcoin and Ethereum blocks from operator-configured nodes. It does not connect
to any provider by default, submit transactions, assign its own address
attributions, identify people, or determine whether activity is illicit.

## Supported sources

| Chain | Source | Read operation |
| --- | --- | --- |
| Bitcoin | Bitcoin Core JSON-RPC | `getblockhash`, then `getblock` with verbosity 2 |
| Ethereum | Ethereum JSON-RPC | `eth_getBlockByNumber` with full transactions |

Both clients return the shared immutable `OnChainBlock` representation from
`sanctum_suite.core.onchain`. Amounts are integers in their smallest native
unit (`sat` or `wei`) to avoid floating-point rounding. Each block records its
chain, height, hash, parent hash, timestamp, provider identifier, and local
fetch time. Bitcoin inputs retain their previous outpoint; the client does not
infer input ownership or value from another transaction. Ethereum contract
creation transactions have no recipient output in this representation.

Raw RPC responses, credentials, and provider error messages are not persisted.
By default, normalized blocks are used in memory only. An operator can
explicitly enable bounded, case-scoped snapshot retention as described below;
this is not a general chain index or an event-ingestion queue.

## Case investigation graph

For an authenticated case, the Workbench can request one block through
`GET /api/v1/cases/{case_id}/onchain-graph?chain=bitcoin&height=840000` or
the equivalent Ethereum URL. The case must already exist. Configure a node
endpoint on the API service:

| Variable | Purpose |
| --- | --- |
| `SANCTUM_BITCOIN_RPC_URL` | Bitcoin Core JSON-RPC endpoint |
| `SANCTUM_BITCOIN_RPC_USERNAME` | Optional Bitcoin RPC username; configure with password |
| `SANCTUM_BITCOIN_RPC_PASSWORD` | Optional Bitcoin RPC password; configure with username |
| `SANCTUM_ETHEREUM_RPC_URL` | Ethereum JSON-RPC endpoint |

The endpoint is controlled by the service operator, not supplied by the API
caller. Requests require the normal authenticated, tenant-scoped case API
access. Missing provider configuration returns `503`; provider failures return
a sanitized `502`. The graph builder refuses oversized graphs rather than
truncating them; the response is capped at 5,000 nodes and 10,000 edges.

The graph shows blocks, transactions, Bitcoin outpoints/outputs, and singular
addresses explicitly returned by the node (multisig `addresses` arrays are not
collapsed to one address). Ethereum `SUBMITS_TO` edges represent the recipient
and requested value in a transaction, not a confirmed transfer; execution
status and post-state are not fetched. Relationships carry the provider,
block hash/height, observation time, and the categorical provenance
`directly_observed`; this is not an attribution or risk confidence score.
Atomic amounts are serialized as decimal strings so clients do not lose
precision. Bitcoin input outpoints are not resolved to prior transaction
outputs. The returned graph reflects the point-in-time query and may change if the node's chain view
changes. Snapshot persistence is disabled unless explicitly configured.

## Ethereum forensic events and traces

Two additional authenticated, case-scoped read endpoints are available:

- `GET /api/v1/cases/{case_id}/onchain-forensics?height=...` fetches the
  normalized block and then calls `eth_getLogs` using the exact returned
  `blockHash` (never an open-ended caller-provided filter). It checks every
  log's block hash/height and transaction membership against that block,
  rejects duplicate log indexes, and fails rather than truncating responses
  above 5,000 logs or 8 MiB of normalized log data. Standard `Transfer` event shapes with indexed sender and
  recipient are surfaced as **observations** with exact integer token
  base-unit values (`value_atomic`) or token IDs; token decimals are unknown,
  and no token metadata or contract standard is assumed. The original topics
  and bounded log data remain available for review.
- `GET /api/v1/cases/{case_id}/onchain-traces/{transaction_hash}` fetches the
  transaction, checks that its block is still canonical, and invokes only the
  fixed `debug_traceTransaction` callTracer configuration. The adapter returns
  a bounded tree (32 levels / 10,000 calls), native value and gas quantities,
  the four-byte input selector, and input length. It deliberately withholds
  calldata and return data. Nodes without the supported debug RPC fail
  explicitly; there is no generic RPC method or caller-controlled tracer.

Both results carry block/transaction provenance and explicitly mark provider
output as unverified. A `Transfer`-shaped log is evidence that the configured
node returned that event, not an independently proven asset transfer,
verified token identity, wallet ownership, or illicit activity. Forks and node
trust remain relevant. Event logs and traces are not saved in the normalized
block snapshot; snapshots retain the base block only. Production API requests
pass through the existing authentication, OPA, TPM measured-boot, and Trustee
TEE attestation middleware. Operators must still configure the Ethereum node
with least privilege and network isolation.

For Crypto OSINT enrichment, the endpoint matches observed transfer endpoints
against case assessments previously imported from an authorized provider
report. These remain `provider_reported_unverified`; the query does not call a
vendor, confirm the source, or promote the label to a Sanctum score. The
response explicitly reports AML and MiCA status as `NOT_ASSESSED`: on-chain
observations and vendor labels do not establish regulatory compliance. No
legal determination, customer due diligence, transaction monitoring program,
SAR/STR decision, or CASP/MiCA control assessment is implemented by these
endpoints.

The experimental Groth16 rating-policy proof documented in
[`ZK_AUDIT_PROOFS.md`](./ZK_AUDIT_PROOFS.md) remains a separate demonstration.
It does not bind a proof to these logs/traces, a case, a provider report, or a
regulatory control, and must not be presented as evidence of AML or MiCA
compliance.

## Optional case-scoped block snapshots

An operator may opt in to retaining normalized block snapshots in the same
tenant/case SQLite database used by incident cases:

| Variable | Purpose |
| --- | --- |
| `SANCTUM_ONCHAIN_STORAGE_ENABLED` | Must be explicitly set to `true` to enable snapshots; otherwise storage stays disabled |
| `SANCTUM_ONCHAIN_RETENTION_DAYS` | Required when enabled; integer from 1 to 36,500 days |

When enabled, a successful live graph query stores the normalized block in the
requested case. The payload includes transaction and address strings needed to
rebuild the graph; addresses are therefore retained in clear form in the
SQLite payload, not pseudonymized. Treat this database as sensitive
investigation evidence and apply filesystem/database encryption, backups,
access restrictions, and deletion controls. Case deletion cascades to snapshots.
Expired snapshots are purged during ingest, listing, and retrieval; the
retention period is measured from storage time. Storage is tenant-scoped through
the case database and the API never exposes the serialized payload through the
listing endpoint.

Snapshots are idempotent on `(case_id, chain, height, block_hash)`. Different
block hashes at the same height are retained as distinct fork/reorganization
observations. Each case is limited to 10,000 snapshots and each normalized
payload to 32 MiB; exceeding a limit returns an explicit error instead of
silently dropping or truncating data. There is no automatic eviction of
unexpired data to make room.

The authenticated `GET /api/v1/cases/{case_id}/onchain-blocks` endpoint lists
snapshot metadata with bounded pagination (`limit` 1–500, `offset` up to
10,000), optionally filtered by `chain`. To rebuild a graph from a specific
retained block without contacting the RPC node, call the graph endpoint with
the matching `chain`, `height`, and `block_hash` query parameters. A
`block_hash` request fails closed if retention is disabled or the snapshot is
missing/expired. Standard case authorization applies to both endpoints.

## Provider report import

The Workbench accepts a normalized JSON export for an existing case. It does
not call Chainalysis, Elliptic, TRM Labs, or Arkham APIs directly. Obtain and
transform reports only through an organization-authorized provider account and
according to the provider's license and terms. The importer supports these
provider identifiers: `chainalysis`, `elliptic`, `trm_labs`, `arkham`, and
`other`.

The complete format is:

```json
{
  "schema_version": "1.0",
  "records": [
    {
      "chain": "ethereum",
      "address": "0x0000000000000000000000000000000000000001",
      "provider": "chainalysis",
      "provider_rating": "high",
      "category": "sanctions",
      "report_reference": "provider-report-id",
      "assessed_at": "2026-10-19T12:00:00Z"
    }
  ]
}
```

`chain` is `bitcoin` or `ethereum`. `provider_rating` preserves the provider's
reported band (`low`, `medium`, `high`, `severe`, `unknown`); it is not
converted into a Sanctum score. `category` must be a structured identifier,
`report_reference` a printable provider-side identifier, and `assessed_at` a
timezone-aware timestamp. Imports are limited to 1 MB and 1,000 records.
Duplicate provider/address/reference records within one report are rejected;
reimporting the exact same report for the same case is idempotent.

The API stores normalized assessment fields and the SHA-256 digest of the
exact uploaded JSON bytes, but does not retain the raw report. Address values
are stored as SHA-256 tokens in development and namespace-separated keyed HMAC
pseudonyms in production; production uses the configured
`SANCTUM_AUDIT_PSEUDONYM_KEY_FILE`. The normalized provider label/category and
reference remain in the case database and are sensitive case data. Case
deletion cascades to these assessments. Follow the deployment's database
encryption, access, backup, and retention controls.

Matching reports are added to the case block graph with
`HAS_REPORTED_ASSESSMENT`; the edges are marked
`provider_reported_unverified`. The importer does not authenticate the vendor,
verify a signed export, confirm the provider reference, or validate that the
rating follows the provider's methodology. The report digest identifies the
uploaded bytes; it does not prove their origin or truth. Independently review
the provider source before acting on imported data. A graph request returns at
most 5,000 matching assessments; larger results fail rather than being
truncated.

## Example

```python
from sanctum_suite.core.onchain import BitcoinCoreClient, EthereumJsonRpcClient

bitcoin = BitcoinCoreClient(
    "http://127.0.0.1:8332/",
    username="sanctum-readonly",
    password="provided-by-secret-manager",
)
bitcoin_block = await bitcoin.get_block(840_000)

ethereum = EthereumJsonRpcClient("https://ethereum-node.internal/")
ethereum_block = await ethereum.get_block(20_000_000)
```

Supply credentials through the deployment's secret manager; do not place real
credentials in source files, command history, logs, dashboard configuration, or
the repository. Bitcoin Core supports a cookie file as an alternative
authentication method, but this initial adapter accepts explicit HTTP Basic
credentials only. For remote nodes, use HTTPS with a valid trusted certificate
and network restrictions. HTTP is suitable only when the RPC endpoint is
confined to a trusted local interface. Never expose an unauthenticated RPC
listener to an untrusted network. Use a dedicated node account and the
least-privilege access supported by the node.

RPC URLs are configured by the operator, are never followed through redirects,
and must not contain embedded username/password credentials or URL fragments.
Requests verify TLS certificates, have a bounded timeout, and reject response
bodies larger than 16 MiB. Provider error details are not reflected into the
exception text. The adapter performs reads only and does not expose a generic
method-call interface.

## Data interpretation and limitations

- A block response is a point-in-time observation from one RPC node, not a
  finality guarantee. Blocks can be reorganized; callers must compare block
  hashes at a given height and apply an explicit confirmation policy before
  relying on results.
- Provider availability, completeness, chain configuration, and node trust are
  operational responsibilities. A successful response does not independently
  authenticate the node's chain view.
- Bitcoin transaction inputs expose outpoints, not resolved prior-output
  values or addresses. This version does not calculate flow totals or cluster
  wallets.
- Ethereum values are native wei only. Token transfers, internal calls,
  traces, logs, validator data, and L2-specific semantics are not indexed.
- Address strings are on-chain identifiers and can still be sensitive when
  linked to people or cases. Apply a lawful purpose, access controls, retention
  limits, and provenance before storing or enriching them. Optional block
  snapshots retain these strings as described above.
- No automatic vendor API lookup, entity attribution, overall sanctions
  decision, or combined Sanctum risk score is produced by this module. Imported
  reports are explicitly identified as unverified provider assertions.

Run the focused tests with:

```powershell
pytest src\sanctum_suite\tests\test_onchain.py src\sanctum_suite\tests\test_onchain_graph.py src\sanctum_suite\tests\test_onchain_risk.py src\sanctum_suite\tests\test_onchain_store.py src\sanctum_suite\tests\test_onchain_properties.py
```

The property tests exercise exact satoshi/wei normalization over generated
values and graph edge/provenance consistency for generated blocks. Scenario
tests cover duplicate ingestion, competing block hashes, retention boundaries,
case deletion, API authentication, and cross-case snapshot isolation.
