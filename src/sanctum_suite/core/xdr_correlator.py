import hashlib
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


class RealtimeXdrMeshCorrelator:
    """Groups caller-supplied events by an exact shared correlation key."""

    MAX_EVENTS = 10_000

    def ingest_telemetry_stream(
        self,
        raw_events: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if len(raw_events) > self.MAX_EVENTS:
            raise ValueError(f"A batch cannot exceed {self.MAX_EVENTS} events")

        groups: dict[str, list[str]] = defaultdict(list)
        accepted = 0
        rejected = 0
        for event in raw_events:
            event_id = event.get("event_id")
            correlation_key = event.get("correlation_key")
            event_type = event.get("event_type")
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
            ):
                rejected += 1
                continue
            groups[correlation_key].append(event_id)
            accepted += 1

        correlations = [
            {
                "correlation_key_sha256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
                "event_ids": event_ids,
                "event_count": len(event_ids),
                "threat_assessment": "NOT_ASSESSED",
            }
            for key, event_ids in groups.items()
            if len(event_ids) > 1
        ]
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
