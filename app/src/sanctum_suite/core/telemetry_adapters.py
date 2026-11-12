"""Vendor-neutral extension points and bounded parsers for security telemetry."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from sanctum_suite.core.telemetry_store import validate_source_id


_CORRELATION_TOKEN = re.compile(r"^[0-9a-f]{64}$")
_CEF_EXTENSION_KEY = re.compile(r"(?:^|\s)([A-Za-z][A-Za-z0-9]*)=")


@runtime_checkable
class PullEventSourceAdapter(Protocol):
    """Fetch bounded batches that map to the shared normalized event fields."""

    source_id: str

    async def fetch_events(
        self, *, cursor: str | None, limit: int
    ) -> tuple[Sequence[Mapping[str, Any]], str | None]: ...


@runtime_checkable
class EventFileParser(Protocol):
    """Converts one operator-selected file format into normalized event mappings."""

    format_name: str

    def parse(self, content: str, *, max_events: int) -> list[dict[str, Any]]: ...


class JsonEventFileParser:
    format_name = "json"

    def parse(self, content: str, *, max_events: int) -> list[dict[str, Any]]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError("JSON import contains invalid JSON") from error
        events = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(events, list):
            raise ValueError("JSON import must be an event array or an object with an events array")
        if len(events) > max_events:
            raise ValueError(f"An import cannot exceed {max_events} events")
        if not events:
            raise ValueError("JSON import must contain at least one event")
        if not all(isinstance(event, dict) for event in events):
            raise ValueError("Every JSON import event must be an object")
        return events


class JsonLinesEventFileParser:
    format_name = "jsonl"

    def parse(self, content: str, *, max_events: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"JSONL import has invalid JSON on line {line_number}") from error
            if not isinstance(event, dict):
                raise ValueError(f"JSONL line {line_number} must contain an event object")
            events.append(event)
            if len(events) > max_events:
                raise ValueError(f"An import cannot exceed {max_events} events")
        if not events:
            raise ValueError("JSONL import must contain at least one event")
        return events


class CEFEventFileParser:
    format_name = "cef"

    def parse(self, content: str, *, max_events: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            if not line.strip():
                continue
            if len(line) > 64_000:
                raise ValueError(f"CEF line {line_number} exceeds 64000 characters")
            header = self._split_header(line)
            if len(header) != 8 or not header[0].startswith("CEF:"):
                raise ValueError(f"CEF line {line_number} has an invalid header")
            cef_version = header[0][4:]
            signature_id = header[4]
            name = header[5]
            if not cef_version.isdigit() or not signature_id or not name:
                raise ValueError(f"CEF line {line_number} has an invalid version or event identity")
            severity = self._severity(header[6], line_number)
            extension = self._parse_extension(header[7])
            observed_at = self._timestamp(extension.get("rt"), line_number)
            source_event_id = extension.get("externalId") or hashlib.sha256(
                line.encode("utf-8")
            ).hexdigest()
            event_type = f"cef.{header[1]}.{header[2]}.{signature_id}"
            if len(event_type) > 128:
                event_type = f"cef.{hashlib.sha256(event_type.encode('utf-8')).hexdigest()[:32]}"
            correlation_token = None
            if extension.get("cs1Label", "").casefold() == "correlation_token":
                correlation_token = extension.get("cs1")
                if not isinstance(correlation_token, str) or not _CORRELATION_TOKEN.fullmatch(
                    correlation_token
                ):
                    raise ValueError(
                        f"CEF line {line_number} correlation_token must be a lowercase SHA-256 token"
                    )
            events.append(
                {
                    "source_event_id": source_event_id,
                    "event_type": event_type,
                    "observed_at": observed_at,
                    "severity": severity,
                    "correlation_token": correlation_token,
                }
            )
            if len(events) > max_events:
                raise ValueError(f"An import cannot exceed {max_events} events")
        if not events:
            raise ValueError("CEF import must contain at least one event")
        return events

    @staticmethod
    def _split_header(line: str) -> list[str]:
        fields: list[str] = []
        current: list[str] = []
        escaped = False
        for character in line:
            if escaped:
                current.extend(("\\", character))
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "|" and len(fields) < 7:
                fields.append("".join(current))
                current = []
            else:
                current.append(character)
        if escaped:
            current.append("\\")
        fields.append("".join(current))
        return [CEFEventFileParser._unescape(value) for value in fields]

    @staticmethod
    def _unescape(value: str) -> str:
        return re.sub(r"\\([\\|=])", r"\1", value)

    @staticmethod
    def _parse_extension(value: str) -> dict[str, str]:
        matches = list(_CEF_EXTENSION_KEY.finditer(value))
        extension: dict[str, str] = {}
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
            extension[match.group(1)] = CEFEventFileParser._unescape(
                value[match.end() : end].strip()
            )
        return extension

    @staticmethod
    def _severity(value: str, line_number: int) -> str:
        try:
            numeric = float(value)
        except ValueError as error:
            raise ValueError(f"CEF line {line_number} severity must be numeric from 0 to 10") from error
        if not 0 <= numeric <= 10:
            raise ValueError(f"CEF line {line_number} severity must be between 0 and 10")
        if numeric <= 3:
            return "LOW"
        if numeric <= 6:
            return "MEDIUM"
        if numeric <= 8:
            return "HIGH"
        return "CRITICAL"

    @staticmethod
    def _timestamp(value: str | None, line_number: int) -> str:
        if not value:
            raise ValueError(f"CEF line {line_number} requires an rt timestamp")
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                timestamp = datetime.strptime(value, "%b %d %Y %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError as error:
                raise ValueError(f"CEF line {line_number} has an unsupported rt timestamp") from error
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError(f"CEF line {line_number} rt timestamp must include a timezone")
        return (
            timestamp.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )


class TelemetryAdapterRegistry:
    """Small explicit registry for future vendor adapters and approved file parsers."""

    def __init__(self) -> None:
        self._pull_adapters: dict[str, PullEventSourceAdapter] = {}
        self._file_parsers: dict[str, EventFileParser] = {
            parser.format_name: parser
            for parser in (
                JsonEventFileParser(),
                JsonLinesEventFileParser(),
                CEFEventFileParser(),
            )
        }

    def register_pull_adapter(self, adapter: PullEventSourceAdapter) -> None:
        validate_source_id(adapter.source_id)
        if adapter.source_id in self._pull_adapters:
            raise ValueError(f"Pull adapter already registered for {adapter.source_id}")
        self._pull_adapters[adapter.source_id] = adapter

    def get_pull_adapter(self, source_id: str) -> PullEventSourceAdapter | None:
        return self._pull_adapters.get(source_id)

    def list_pull_sources(self) -> list[str]:
        return sorted(self._pull_adapters)

    def get_file_parser(self, format_name: str) -> EventFileParser | None:
        return self._file_parsers.get(format_name.casefold())

    def list_file_formats(self) -> list[str]:
        return sorted(self._file_parsers)
