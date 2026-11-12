import hashlib
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


class RealtimeXdrMeshCorrelator:
    """Groups caller-supplied events by an exact shared correlation key."""

    MAX_EVENTS = 10_000
    REPORTED_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")

    def ingest_telemetry_stream(
        self,
        raw_events: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if len(raw_events) > self.MAX_EVENTS:
            raise ValueError(f"A batch cannot exceed {self.MAX_EVENTS} events")

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        accepted = 0
        rejected = 0
        for event in raw_events:
            event_id = event.get("event_id")
            correlation_key = event.get("correlation_key")
            event_type = event.get("event_type")
            observed_at = self._normalize_timestamp(event.get("observed_at"))
            source = event.get("source")
            severity = event.get("severity")
            detection_scenario_id = event.get("detection_scenario_id")
            detection_rule_id = event.get("detection_rule_id")
            normalized_severity = severity.upper() if isinstance(severity, str) else None
            if (
                not isinstance(event_id, str)
                or not event_id
                or len(event_id) > 128
                or not isinstance(correlation_key, str)
                or not correlation_key
                or len(correlation_key) > 256
                or not isinstance(event_type, str)
                or not event_type
                or len(event_type) > 128
                or (event.get("observed_at") is not None and observed_at is None)
                or (source is not None and (
                    not isinstance(source, str) or not source or len(source) > 128
                ))
                or (
                    severity is not None
                    and normalized_severity not in self.REPORTED_SEVERITIES
                )
                or ((detection_scenario_id is None) != (detection_rule_id is None))
                or (
                    detection_scenario_id is not None
                    and (
                        not isinstance(detection_scenario_id, str)
                        or not detection_scenario_id.strip()
                        or len(detection_scenario_id) > 128
                        or not isinstance(detection_rule_id, str)
                        or not detection_rule_id.strip()
                        or len(detection_rule_id) > 128
                    )
                )
            ):
                rejected += 1
                continue
            groups[correlation_key].append(
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "source": source,
                    "observed_at": observed_at,
                    "reported_severity": normalized_severity,
                    "detection_scenario_id": detection_scenario_id,
                    "detection_rule_id": detection_rule_id,
                }
            )
            accepted += 1

        correlations = []
        severity_rank = {severity: rank for rank, severity in enumerate(self.REPORTED_SEVERITIES)}
        for key, events in groups.items():
            if len(events) < 2:
                continue
            reported_severities = [
                event["reported_severity"]
                for event in events
                if event["reported_severity"] is not None
            ]
            priority = (
                min(reported_severities, key=severity_rank.__getitem__)
                if reported_severities
                else "NOT_ASSESSED"
            )
            priority_reasons = [
                f"{len(events)} events share an exact caller-provided correlation key."
            ]
            if reported_severities:
                priority_reasons.append(
                    f"Highest source-reported severity: {priority}; not independently verified."
                )
            else:
                priority_reasons.append("No source-reported severity was provided.")
            priority_reasons.append(
                "This descriptive priority is not a threat assessment; exact-key grouping "
                "does not establish malicious activity."
            )
            correlations.append({
                "correlation_id": f"LOCAL-CORR-{uuid.uuid4().hex[:8].upper()}",
                "correlation_key_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
                "event_ids": [event["event_id"] for event in events],
                "event_count": len(events),
                "priority": priority,
                "priority_reasons": priority_reasons,
                "timeline": sorted(
                    events,
                    key=lambda event: (
                        event["observed_at"] is None,
                        event["observed_at"] or "",
                    ),
                ),
                "threat_assessment": "NOT_ASSESSED",
            })
        return {
            "correlation_id": f"LOCAL-CORR-{uuid.uuid4().hex[:8].upper()}",
            "events_received": len(raw_events),
            "events_accepted": accepted,
            "events_rejected": rejected,
            "correlations": correlations,
            "status": "LOCAL_CORRELATION_ONLY",
            "external_stream_connected": False,
            "limitations": (
                "Exact-key grouping only; no threat detection, time-window correlation, "
                "vendor EDR/XDR integration, or STIX/TAXII export is performed."
            ),
        }

    @staticmethod
    def _normalize_timestamp(value: Any) -> str | None:
        if value is None:
            return None
        try:
            timestamp = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return None
        return (
            timestamp.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
