from __future__ import annotations

import ipaddress
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

from sanctum_suite.core.telemetry_store import validate_event_label, validate_source_id


_MAX_EVENTS = 1_000_000
_BATCH_SIZE = 1_000
_MAX_EVENT_BYTES = 64 * 1024
_MAX_WASM_MEMORY_BYTES = 64 * 1024 * 1024
_MAX_WASM_FUEL = 10_000_000
_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
_FIELDS = (
    "event_id",
    "source_id",
    "event_type",
    "observed_at",
    "reported_severity",
    "detection_scenario_id",
    "detection_rule_id",
    "ingested_at",
)
_IMMUTABLE_FIELDS = ("event_id", "source_id", "observed_at", "ingested_at")
_OPTIONAL_LABEL_FIELDS = ("detection_scenario_id", "detection_rule_id")
class TelemetryPipelineError(ValueError):
    """Raised when the local telemetry export cannot safely complete."""


def _read_events(
    database: Path, *, source_id: str | None, limit: int
) -> Iterator[dict[str, Any]]:
    if not database.is_file():
        raise TelemetryPipelineError("Telemetry database must be an existing file")
    if not 1 <= limit <= _MAX_EVENTS:
        raise TelemetryPipelineError(
            f"limit must be between 1 and {_MAX_EVENTS}"
        )
    if source_id is not None:
        try:
            validate_source_id(source_id)
        except ValueError as error:
            raise TelemetryPipelineError(str(error)) from error

    uri = database.resolve().as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        try:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(normalized_telemetry_events)"
                )
            }
            required_columns = {
                "event_id",
                "source_id",
                "event_type",
                "observed_at",
                "reported_severity",
                "detection_scenario_id",
                "detection_rule_id",
                "ingested_at",
            }
            if not required_columns.issubset(columns):
                raise TelemetryPipelineError(
                    "Database does not contain the normalized telemetry event schema"
                )
            selected = ", ".join(_FIELDS)
            if source_id is None:
                cursor = connection.execute(
                    f"SELECT {selected} FROM normalized_telemetry_events "
                    "ORDER BY observed_at DESC, event_id LIMIT ?",
                    (limit + 1,),
                )
            else:
                cursor = connection.execute(
                    f"SELECT {selected} FROM normalized_telemetry_events "
                    "WHERE source_id = ? ORDER BY observed_at DESC, event_id LIMIT ?",
                    (source_id, limit + 1),
                )
            for row in cursor:
                yield dict(row)
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise TelemetryPipelineError(
            f"Cannot read telemetry database: {error}"
        ) from error


def _validate_transformed_event(
    original: dict[str, Any], transformed: Any
) -> dict[str, Any]:
    if not isinstance(transformed, dict) or set(transformed) != set(_FIELDS):
        raise TelemetryPipelineError(
            "Wasm transform must return one event with the exact normalized fields"
        )
    if any(transformed[field] != original[field] for field in _IMMUTABLE_FIELDS):
        raise TelemetryPipelineError(
            "Wasm transform must not change event identity, source, or timestamps"
        )
    try:
        validate_event_label(transformed["event_type"])
    except (TypeError, ValueError) as error:
        raise TelemetryPipelineError(
            "Wasm transform returned an invalid event_type"
        ) from error

    severity = transformed["reported_severity"]
    if severity is not None and (
        not isinstance(severity, str) or severity not in _SEVERITIES
    ):
        raise TelemetryPipelineError(
            "Wasm transform returned an unsupported reported_severity"
        )
    for field in _OPTIONAL_LABEL_FIELDS:
        value = transformed[field]
        if value is not None:
            try:
                validate_event_label(value)
            except (TypeError, ValueError) as error:
                raise TelemetryPipelineError(
                    f"Wasm transform returned an invalid {field}"
                ) from error
    if (transformed["detection_scenario_id"] is None) != (
        transformed["detection_rule_id"] is None
    ):
        raise TelemetryPipelineError(
            "Wasm transform must keep detection identifiers as a pair"
        )
    return transformed


class _CheckedSpanExporter:
    def __init__(self, exporter: Any, success_result: Any) -> None:
        self._exporter = exporter
        self._success_result = success_result
        self.failed = False

    def export(self, spans: Any) -> Any:
        result = self._exporter.export(spans)
        if result is not self._success_result:
            self.failed = True
        return result

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return self._exporter.force_flush(timeout_millis)

    def shutdown(self) -> None:
        self._exporter.shutdown()


class WasmTelemetryTransform:
    """Runs an imported-function-free Wasm event transformer with bounded fuel."""

    def __init__(self, module_path: Path) -> None:
        if not module_path.is_file():
            raise TelemetryPipelineError("Wasm module must be an existing file")
        try:
            import wasmtime
        except ImportError as error:
            raise TelemetryPipelineError(
                "Wasm support is optional; install sanctum-suite[telemetry]"
            ) from error

        try:
            config = wasmtime.Config()
            config.consume_fuel = True
            self._engine = wasmtime.Engine(config)
            self._module = wasmtime.Module.from_file(self._engine, str(module_path))
            if self._module.imports:
                raise TelemetryPipelineError(
                    "Wasm transform modules must not import host functions"
                )
            store = wasmtime.Store(self._engine)
            store.set_limits(
                memory_size=_MAX_WASM_MEMORY_BYTES,
                table_elements=0,
                instances=1,
                tables=0,
                memories=1,
            )
            store.set_fuel(_MAX_WASM_FUEL)
            linker = wasmtime.Linker(self._engine)
            instance = linker.instantiate(store, self._module)
            exports = instance.exports(store)
            self._memory = exports["memory"]
            self._alloc = exports["alloc"]
            self._transform = exports["transform_json"]
            self._dealloc = exports["dealloc"]
            if not all(
                isinstance(function, wasmtime.Func)
                for function in (self._alloc, self._transform, self._dealloc)
            ) or not isinstance(self._memory, wasmtime.Memory):
                raise TelemetryPipelineError(
                    "Wasm module must export memory, alloc, transform_json, and dealloc"
                )
            self._store = store
            self._wasmtime = wasmtime
        except TelemetryPipelineError:
            raise
        except (OSError, wasmtime.WasmtimeError, KeyError, TypeError, ValueError) as error:
            raise TelemetryPipelineError(
                f"Cannot initialize Wasm transform: {error}"
            ) from error

    def transform(self, event: dict[str, Any]) -> dict[str, Any] | None:
        payload = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        if len(payload) > _MAX_EVENT_BYTES:
            raise TelemetryPipelineError(
                f"Normalized event exceeds {_MAX_EVENT_BYTES} bytes"
            )
        input_pointer = None
        output_pointer = None
        try:
            self._store.set_fuel(_MAX_WASM_FUEL)
            input_pointer = self._alloc(self._store, len(payload))
            if not isinstance(input_pointer, int) or input_pointer <= 0:
                raise TelemetryPipelineError("Wasm allocator returned an invalid pointer")
            self._memory.write(self._store, payload, input_pointer)
            packed_result = self._transform(self._store, input_pointer, len(payload))
            if not isinstance(packed_result, int):
                raise TelemetryPipelineError(
                    "Wasm transform_json must return a packed pointer and length"
                )
            packed_result &= (1 << 64) - 1
            output_pointer = packed_result >> 32
            output_length = packed_result & 0xFFFFFFFF
            if output_pointer == 0 and output_length == 0:
                return None
            if output_pointer <= 0 or not 1 <= output_length <= _MAX_EVENT_BYTES:
                raise TelemetryPipelineError(
                    "Wasm transform returned an invalid output pointer or length"
                )
            if output_pointer == input_pointer and output_length > len(payload):
                raise TelemetryPipelineError(
                    "Wasm in-place output must not exceed the input buffer"
                )
            if output_pointer != input_pointer and (
                output_pointer < input_pointer + len(payload)
                and input_pointer < output_pointer + output_length
            ):
                raise TelemetryPipelineError(
                    "Wasm transform output must not overlap the input buffer"
                )
            memory_size = self._memory.data_len(self._store)
            if output_pointer + output_length > memory_size:
                raise TelemetryPipelineError(
                    "Wasm transform output is outside its linear memory"
                )
            output = self._memory.read(
                self._store, output_pointer, output_pointer + output_length
            )
            try:
                transformed = json.loads(output)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise TelemetryPipelineError(
                    "Wasm transform returned invalid JSON"
                ) from error
            return _validate_transformed_event(event, transformed)
        except TelemetryPipelineError:
            raise
        except (self._wasmtime.WasmtimeError, TypeError, ValueError) as error:
            raise TelemetryPipelineError(
                f"Wasm transform trapped or exceeded its execution budget: {error}"
            ) from error
        finally:
            allocations = []
            if output_pointer is not None and output_pointer > 0:
                if output_pointer != input_pointer:
                    allocations.append(
                        (output_pointer, packed_result & 0xFFFFFFFF)
                    )
            if input_pointer is not None and input_pointer > 0:
                allocations.append((input_pointer, len(payload)))
            for pointer, dealloc_length in allocations:
                if pointer is not None and pointer > 0:
                    try:
                        self._dealloc(self._store, pointer, dealloc_length)
                    except self._wasmtime.WasmtimeError as error:
                        raise TelemetryPipelineError(
                            "Wasm transform deallocator trapped"
                        ) from error


def _validate_otlp_endpoint(endpoint: str) -> str:
    try:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError
        if parsed.scheme == "http":
            hostname = parsed.hostname.lower()
            try:
                is_loopback = ipaddress.ip_address(hostname).is_loopback
            except ValueError:
                is_loopback = hostname == "localhost" or hostname.endswith(
                    ".localhost"
                )
            if not is_loopback:
                raise TelemetryPipelineError(
                    "OTLP over HTTP is permitted only for a loopback Collector"
                )
        parsed.port
    except ValueError as error:
        raise TelemetryPipelineError(
            "OTLP endpoint must be a valid HTTPS URL or loopback HTTP URL"
        ) from error
    return endpoint


def _arrow_schema(pa: Any) -> Any:
    return pa.schema(
        [
            pa.field("event_id", pa.string(), nullable=False),
            pa.field("source_id", pa.string(), nullable=False),
            pa.field("event_type", pa.string(), nullable=False),
            pa.field("observed_at", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("reported_severity", pa.string()),
            pa.field("detection_scenario_id", pa.string()),
            pa.field("detection_rule_id", pa.string()),
            pa.field("ingested_at", pa.timestamp("us", tz="UTC"), nullable=False),
        ],
        metadata={
            b"sanctum.schema": b"normalized-telemetry-v1",
            b"sanctum.limitations": (
                b"Local operator-selected SQLite snapshot; raw source IDs and "
                b"correlation token hashes are excluded."
            ),
        },
    )


def _arrow_record(event: dict[str, Any]) -> dict[str, Any]:
    result = dict(event)
    try:
        for field in ("observed_at", "ingested_at"):
            timestamp = datetime.fromisoformat(
                result[field].replace("Z", "+00:00")
            )
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError
            result[field] = timestamp.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError) as error:
        raise TelemetryPipelineError(
            "Telemetry event contains an invalid timestamp"
        ) from error
    return result


def archive_telemetry(
    *,
    database: Path,
    output: Path,
    source_id: str | None = None,
    limit: int = 100_000,
    wasm_module: Path | None = None,
    otlp_endpoint: str | None = None,
) -> dict[str, Any]:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:
        raise TelemetryPipelineError(
            "Arrow/Parquet support is optional; install sanctum-suite[telemetry]"
        ) from error
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            SimpleSpanProcessor,
            SpanExportResult,
        )
    except ImportError as error:
        raise TelemetryPipelineError(
            "OpenTelemetry support is optional; install sanctum-suite[telemetry]"
        ) from error

    if not output.parent.is_dir():
        raise TelemetryPipelineError("Output parent directory must already exist")
    if output.suffix.lower() != ".parquet":
        raise TelemetryPipelineError("Output file must use the .parquet extension")
    if not 1 <= limit <= _MAX_EVENTS:
        raise TelemetryPipelineError(
            f"limit must be between 1 and {_MAX_EVENTS}"
        )
    if source_id is not None:
        try:
            validate_source_id(source_id)
        except ValueError as error:
            raise TelemetryPipelineError(str(error)) from error
    if database.resolve() == output.resolve():
        raise TelemetryPipelineError("Output must not overwrite the telemetry database")
    if wasm_module is not None and not wasm_module.is_file():
        raise TelemetryPipelineError("Wasm module must be an existing file")
    if wasm_module is not None and wasm_module.resolve() == output.resolve():
        raise TelemetryPipelineError("Output must not overwrite the Wasm module")
    if otlp_endpoint is not None:
        otlp_endpoint = _validate_otlp_endpoint(otlp_endpoint)

    provider = TracerProvider(
        resource=Resource.create({"service.name": "sanctum.telemetry.archive"})
    )
    checked_exporter = None
    if otlp_endpoint is not None:
        checked_exporter = _CheckedSpanExporter(
            OTLPSpanExporter(endpoint=otlp_endpoint, timeout=5),
            SpanExportResult.SUCCESS,
        )
        provider.add_span_processor(
            SimpleSpanProcessor(checked_exporter)
        )
    tracer = provider.get_tracer("sanctum_suite.telemetry_pipeline", "1.0.0")

    temporary_path: Path | None = None
    event_count = 0
    filtered_count = 0
    truncated = False
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.",
            suffix=".tmp.parquet",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with tracer.start_as_current_span(
            "telemetry.archive",
            record_exception=False,
            set_status_on_exception=False,
        ) as archive_span:
            transformer = (
                WasmTelemetryTransform(wasm_module)
                if wasm_module is not None
                else None
            )
            with tracer.start_as_current_span(
                "telemetry.read_sqlite",
                record_exception=False,
                set_status_on_exception=False,
            ) as read_span:
                with closing(
                    _read_events(database, source_id=source_id, limit=limit)
                ) as events:
                    with pq.ParquetWriter(
                        temporary_path,
                        _arrow_schema(pa),
                        compression="zstd",
                    ) as writer:
                        batch: list[dict[str, Any]] = []
                        with tracer.start_as_current_span(
                            "telemetry.wasm_transform",
                            record_exception=False,
                            set_status_on_exception=False,
                        ) as transform_span:
                            for original in events:
                                if event_count == limit:
                                    truncated = True
                                    break
                                event_count += 1
                                transformed = (
                                    transformer.transform(original)
                                    if transformer is not None
                                    else original
                                )
                                if transformed is None:
                                    filtered_count += 1
                                    continue
                                batch.append(_arrow_record(transformed))
                                if len(batch) >= _BATCH_SIZE:
                                    with tracer.start_as_current_span(
                                        "telemetry.write_parquet",
                                        record_exception=False,
                                        set_status_on_exception=False,
                                    ) as write_span:
                                        writer.write_table(
                                            pa.Table.from_pylist(
                                                batch, schema=_arrow_schema(pa)
                                            )
                                        )
                                        write_span.set_attribute(
                                            "telemetry.events.written", len(batch)
                                        )
                                    batch.clear()
                            transform_span.set_attribute(
                                "telemetry.events.filtered", filtered_count
                            )
                        if batch:
                            with tracer.start_as_current_span(
                                "telemetry.write_parquet",
                                record_exception=False,
                                set_status_on_exception=False,
                            ) as write_span:
                                writer.write_table(
                                    pa.Table.from_pylist(
                                        batch, schema=_arrow_schema(pa)
                                    )
                                )
                                write_span.set_attribute(
                                    "telemetry.events.written", len(batch)
                                )
                read_span.set_attribute("telemetry.events.read", event_count)
                read_span.set_attribute("telemetry.events.truncated", truncated)

            archive_span.set_attribute("telemetry.events.filtered", filtered_count)
            archive_span.set_attribute(
                "telemetry.wasm.enabled", transformer is not None
            )
            archive_span.set_attribute("telemetry.source_filter.enabled", source_id is not None)

        if not provider.force_flush(timeout_millis=5_000) or (
            checked_exporter is not None and checked_exporter.failed
        ):
            raise TelemetryPipelineError(
                "OpenTelemetry spans could not be exported to the configured endpoint"
            )
        os.replace(temporary_path, output)
        temporary_path = None
        output_bytes = output.stat().st_size
        return {
            "status": "ARCHIVED",
            "output": str(output),
            "format": "parquet",
            "schema": "normalized-telemetry-v1",
            "events_read": event_count,
            "events_written": event_count - filtered_count,
            "events_filtered_by_wasm": filtered_count,
            "truncated": truncated,
            "output_bytes": output_bytes,
            "otlp_export_enabled": otlp_endpoint is not None,
            "raw_source_event_ids_exported": False,
            "correlation_token_hashes_exported": False,
            "limitations": (
                "The archive contains only normalized telemetry fields from the "
                "selected local SQLite database. Wasm transforms are untrusted, "
                "fuel- and memory-limited, and have no host imports. OTel spans "
                "include operation counts only and are sent only when an explicit "
                "OTLP endpoint is provided. The archive is not signed, encrypted, "
                "immutable, or evidence of a security verdict."
            ),
        }
    except TelemetryPipelineError:
        raise
    except (OSError, sqlite3.Error, pa.ArrowException) as error:
        raise TelemetryPipelineError(
            f"Telemetry archive could not be completed: {error}"
        ) from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as error:
                raise TelemetryPipelineError(
                    f"Cannot clean up incomplete Parquet archive: {error}"
                ) from error
        provider.shutdown()
