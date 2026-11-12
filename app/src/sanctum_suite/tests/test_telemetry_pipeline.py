import json
from pathlib import Path

import pytest

pytest.importorskip("pyarrow")
pytest.importorskip("wasmtime")
pytest.importorskip("opentelemetry.sdk")

import pyarrow.parquet as pq
import wasmtime
from opentelemetry.sdk.trace.export import SpanExportResult
from typer.testing import CliRunner

from sanctum_suite import main as cli_main
from sanctum_suite.core import telemetry_pipeline
from sanctum_suite.core.telemetry_pipeline import (
    TelemetryPipelineError,
    _validate_otlp_endpoint,
)
from sanctum_suite.core.telemetry_store import TelemetryEventStore


def _write_wasm(path: Path, *, transform_body: str) -> None:
    module = f"""
    (module
      (memory (export "memory") 1)
      (func (export "alloc") (param i32) (result i32) (i32.const 1024))
      (func (export "dealloc") (param i32 i32))
      (func (export "transform_json")
        (param $pointer i32)
        (param $length i32)
        (result i64)
        {transform_body}
      )
    )
    """
    path.write_bytes(wasmtime.wat2wasm(module))


def _database(path: Path) -> None:
    store = TelemetryEventStore(path)
    store.ingest(
        "network-sensor",
        [
            {
                "source_event_id": "private-event-id",
                "event_type": "network.connection",
                "observed_at": "2026-10-19T10:00:00Z",
                "severity": "HIGH",
                "detection_scenario_id": "network",
                "detection_rule_id": "connection",
                "correlation_token": "a" * 64,
            },
            {
                "source_event_id": "another-private-id",
                "event_type": "network.dns",
                "observed_at": "2026-10-19T10:01:00Z",
            },
        ],
    )


def test_telemetry_archive_cli_exports_parquet_with_isolated_wasm_and_otlp_opt_in(
    tmp_path,
):
    database = tmp_path / "events.sqlite3"
    _database(database)
    wasm = tmp_path / "identity-transform.wasm"
    _write_wasm(
        wasm,
        transform_body="""
        (i64.or
          (i64.shl (i64.extend_i32_u (local.get $pointer)) (i64.const 32))
          (i64.extend_i32_u (local.get $length)))
        """,
    )
    output = tmp_path / "archive.parquet"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "telemetry-archive",
            "--database",
            str(database),
            "--output",
            str(output),
            "--source-id",
            "network-sensor",
            "--wasm-module",
            str(wasm),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    table = pq.read_table(output)
    assert report["status"] == "ARCHIVED"
    assert report["events_read"] == report["events_written"] == 2
    assert report["events_filtered_by_wasm"] == 0
    assert report["otlp_export_enabled"] is False
    assert report["raw_source_event_ids_exported"] is False
    assert report["correlation_token_hashes_exported"] is False
    assert "correlation_token_sha256" not in table.column_names
    assert table.schema.metadata[b"sanctum.schema"] == b"normalized-telemetry-v1"
    assert {row["event_type"] for row in table.to_pylist()} == {
        "network.connection",
        "network.dns",
    }
    assert "private-event-id" not in output.read_bytes().decode("latin1")
    assert report["output_bytes"] == output.stat().st_size


def test_telemetry_archive_wasm_can_filter_rows_and_truncation_is_explicit(tmp_path):
    database = tmp_path / "events.sqlite3"
    _database(database)
    wasm = tmp_path / "drop-transform.wasm"
    _write_wasm(wasm, transform_body="(i64.const 0)")
    output = tmp_path / "filtered.parquet"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "telemetry-archive",
            "--database",
            str(database),
            "--output",
            str(output),
            "--limit",
            "1",
            "--wasm-module",
            str(wasm),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["events_read"] == 1
    assert report["events_written"] == 0
    assert report["events_filtered_by_wasm"] == 1
    assert report["truncated"] is True
    assert pq.read_table(output).num_rows == 0


def test_telemetry_archive_rejects_host_imports_and_does_not_publish_partial_output(
    tmp_path,
):
    database = tmp_path / "events.sqlite3"
    _database(database)
    wasm = tmp_path / "host-import.wasm"
    wasm.write_bytes(
        wasmtime.wat2wasm(
            """
            (module
              (import "host" "read_file" (func))
              (memory (export "memory") 1)
              (func (export "alloc") (param i32) (result i32) (i32.const 1024))
              (func (export "dealloc") (param i32 i32))
              (func (export "transform_json")
                (param i32) (param i32) (result i64) (i64.const 0))
            )
            """
        )
    )
    output = tmp_path / "must-not-exist.parquet"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "telemetry-archive",
            "--database",
            str(database),
            "--output",
            str(output),
            "--wasm-module",
            str(wasm),
        ],
    )

    assert result.exit_code != 0
    assert "must not import host functions" in result.output
    assert not output.exists()
    assert list(tmp_path.glob(".must-not-exist.parquet.*.tmp.parquet")) == []


def test_telemetry_archive_exports_only_count_spans_to_explicit_otlp_endpoint(
    tmp_path, monkeypatch
):
    database = tmp_path / "events.sqlite3"
    _database(database)
    output = tmp_path / "otel.parquet"
    exported_spans = []
    exporter_endpoints = []

    class FakeOTLPSpanExporter:
        def __init__(self, *, endpoint, timeout):
            exporter_endpoints.append((endpoint, timeout))

        def export(self, spans):
            exported_spans.extend(spans)
            return SpanExportResult.SUCCESS

        def force_flush(self, timeout_millis=30_000):
            return True

        def shutdown(self):
            return None

    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
        FakeOTLPSpanExporter,
    )
    report = telemetry_pipeline.archive_telemetry(
        database=database,
        output=output,
        otlp_endpoint="https://otel.internal/v1/traces",
    )

    assert report["otlp_export_enabled"] is True
    assert exporter_endpoints == [("https://otel.internal/v1/traces", 5)]
    assert {
        span.name for span in exported_spans
    } >= {
        "telemetry.archive",
        "telemetry.read_sqlite",
        "telemetry.wasm_transform",
        "telemetry.write_parquet",
    }
    assert all(
        "private-event-id" not in str(span.attributes)
        and "correlation_token" not in str(span.attributes)
        for span in exported_spans
    )


def test_telemetry_archive_does_not_publish_when_explicit_otlp_export_fails(
    tmp_path, monkeypatch
):
    database = tmp_path / "events.sqlite3"
    _database(database)
    output = tmp_path / "failed-otel.parquet"

    class FailedOTLPSpanExporter:
        def __init__(self, *, endpoint, timeout):
            pass

        def export(self, spans):
            return SpanExportResult.FAILURE

        def force_flush(self, timeout_millis=30_000):
            return True

        def shutdown(self):
            return None

    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
        FailedOTLPSpanExporter,
    )
    result = CliRunner().invoke(
        cli_main.app,
        [
            "telemetry-archive",
            "--database",
            str(database),
            "--output",
            str(output),
            "--otlp-endpoint",
            "https://otel.internal/v1/traces",
        ],
    )

    assert result.exit_code != 0
    assert "could not be exported" in result.output
    assert not output.exists()


def test_telemetry_archive_rejects_wasm_output_with_unapproved_shape(tmp_path):
    database = tmp_path / "events.sqlite3"
    _database(database)
    wasm = tmp_path / "invalid-output.wasm"
    wasm.write_bytes(
        wasmtime.wat2wasm(
            """
            (module
              (memory (export "memory") 1)
              (data (i32.const 1024) "null")
              (func (export "alloc") (param i32) (result i32) (i32.const 2048))
              (func (export "dealloc") (param i32 i32))
              (func (export "transform_json")
                (param i32) (param i32) (result i64)
                (i64.const 4398046511108))
            )
            """
        )
    )
    output = tmp_path / "invalid-output.parquet"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "telemetry-archive",
            "--database",
            str(database),
            "--output",
            str(output),
            "--wasm-module",
            str(wasm),
        ],
    )

    assert result.exit_code != 0
    assert "Wasm transform must return one event" in result.output
    assert not output.exists()


def test_otlp_endpoint_requires_tls_or_loopback_http():
    assert (
        _validate_otlp_endpoint("http://127.0.0.1:4318/v1/traces")
        == "http://127.0.0.1:4318/v1/traces"
    )
    assert (
        _validate_otlp_endpoint("https://otel.internal/v1/traces")
        == "https://otel.internal/v1/traces"
    )
    for endpoint in (
        "http://otel.internal/v1/traces",
        "https://user:password@otel.internal/v1/traces",
        "file:///tmp/traces",
    ):
        try:
            _validate_otlp_endpoint(endpoint)
        except TelemetryPipelineError:
            pass
        else:
            raise AssertionError(f"accepted unsafe OTLP endpoint: {endpoint}")
