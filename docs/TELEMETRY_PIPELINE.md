# Local telemetry archive: Wasmtime, Arrow/Parquet, and OpenTelemetry

`sanctum telemetry-archive` creates a columnar Parquet snapshot from the
existing normalized telemetry SQLite store. It can optionally run a
WebAssembly transform inside Wasmtime and export operation-count traces to an
explicit OpenTelemetry Protocol (OTLP/HTTP) Collector. The command is
read-only with respect to the SQLite database and does not run scanners or
external actions.

## Install the optional runtime

The data-plane dependencies are optional so standard installs remain small:

```sh
python -m pip install "sanctum-suite[telemetry]"
```

This extra installs PyArrow, Wasmtime, the OpenTelemetry SDK, and its OTLP/HTTP
trace exporter. Prepare and verify these dependencies in the approved connected
staging zone before an air-gapped deployment. Do not install packages from a
public index on the isolated host.

## Archive normalized events

Choose one local telemetry database and output path that are access-controlled
for the same operator/tenant. The command intentionally uses a specific
database file instead of bypassing API authentication or selecting a tenant
implicitly:

```sh
sanctum telemetry-archive \
  --database ./data/tenant-a-cases.sqlite3 \
  --source-id network-sensor \
  --output ./evidence/network-events.parquet \
  --limit 100000
```

`--source-id` is optional. `--limit` defaults to 100,000 and is capped at
1,000,000. The JSON summary reports `truncated: true` if additional matching
events exist beyond the requested limit. Re-run with an approved higher limit
or source filter if a complete export is required.

The Parquet schema is `normalized-telemetry-v1`. Event timestamps are UTC
microsecond timestamp columns. The archive includes only normalized event
fields; raw source event identifiers and correlation-token hashes are
deliberately excluded. The local event UUID is an internal record identifier.
Parquet compression uses Zstandard. Output is written to a temporary file and
atomically published after a successful export; an existing output is replaced
only when the complete export succeeds.

## Wasmtime transform ABI

An optional module can filter events or normalize their structured detection
labels:

```sh
sanctum telemetry-archive \
  --database ./data/tenant-a-cases.sqlite3 \
  --output ./evidence/normalized-events.parquet \
  --wasm-module ./plugins/telemetry-transform.wasm
```

The module is an untrusted core Wasm module and must export:

- `memory`: linear memory
- `alloc(size: i32) -> i32`: allocate a writable input buffer
- `transform_json(pointer: i32, length: i32) -> i64`: transform one UTF-8 JSON
  event and return `(output_pointer << 32) | output_length`
- `dealloc(pointer: i32, length: i32)`: release allocated buffers

Returning zero filters the event. Otherwise, the output must be a UTF-8 JSON
object with exactly the normalized Parquet event fields. Event ID, source ID,
and timestamps must remain unchanged. A transform may update only the event
type, reported severity, and detection scenario/rule labels. Labels use the
structured identifier format enforced by the telemetry ingester; free text is
rejected. An in-place output may shrink but not exceed its input allocation;
expanded results must use a separate allocation.

Wasmtime is instantiated without a host-function linker, so modules importing
filesystem, network, clock, or other host capabilities are rejected. Each
invocation has a 64 MiB linear-memory cap, a 10-million instruction fuel
budget, and a 64 KiB input/output event limit. The application validates the
result before including it. A trap, invalid output, or limit violation aborts
the export; incomplete Parquet output is not published. Review and pin module
builds through the organization's normal supply-chain process; sandboxing is
not proof that a transform is correct.

## OpenTelemetry traces

The pipeline creates spans for SQLite reading, Wasm transformation, Parquet
writing, and the overall archive. Span attributes contain operation counts and
configuration booleans only—not source event IDs, telemetry payloads, or
correlation-token hashes. No spans are sent anywhere unless an endpoint is
explicitly supplied:

```sh
sanctum telemetry-archive \
  --database ./data/tenant-a-cases.sqlite3 \
  --output ./evidence/events.parquet \
  --otlp-endpoint https://otel-collector.internal/v1/traces
```

HTTPS is required for remote endpoints; plaintext HTTP is accepted only for a
loopback Collector such as `http://127.0.0.1:4318/v1/traces`. The exporter uses
the local system CA trust by default; configure the standard
`OTEL_EXPORTER_OTLP_CERTIFICATE` setting for an approved internal CA. Do not
point the exporter at an untrusted endpoint: traces disclose operational
metadata and their network transmission is an explicit side effect.

## Operational boundaries

- The selected SQLite file must be the intended tenant's database. Do not
  combine tenant databases into one export without an approved data-sharing
  basis.
- The command does not decrypt, authenticate, sign, or make Parquet files
  immutable. Apply approved file permissions, encryption, retention, backups,
  and signatures separately.
- An archive contains the stored normalized event window only; it is not proof
  of source completeness, alert accuracy, a malicious event, or policy
  compliance.
- Wasm transforms can filter or relabel evidence. Preserve the original source
  database and record the approved module digest alongside any derived
  archive.
