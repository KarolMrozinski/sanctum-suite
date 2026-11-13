import uuid
from collections.abc import Mapping, Sequence
from typing import Any


class SovereignThreatIntelAggregator:
    """Summarizes caller-supplied indicators without claiming feed connectivity."""

    def aggregate_threat_feeds(
        self,
        indicators: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if indicators is None:
            return {
                "feed_id": None,
                "provider_connected": False,
                "indicators_processed": 0,
                "status": "FEED_NOT_CONFIGURED",
            }
        return {
            "feed_id": f"OFFLINE-{uuid.uuid4().hex[:8].upper()}",
            "provider_connected": False,
            "indicators_processed": len(indicators),
            "status": "CALLER_SUPPLIED_INDICATORS_COUNTED",
            "limitations": (
                "No external feed is queried, and no threat actor attribution, "
                "enrichment, or STIX/TAXII validation is performed."
            ),
        }
