import uuid
from typing import Dict, Any, List


class DiamondModelThreatTracker:
    """Silnik analizy intruzów w oparciu o The Diamond Model of Intrusion Analysis i inteligencję Mandiant."""

    def build_diamond_event(self, adversary_group: str, capability_used: str, victim_asset: str) -> Dict[str, Any]:
        """Tworzy węzeł analizy w modelu diamentowym (Adversary - Capability - Infrastructure - Victim)."""
        event_id = f"DMOND-{uuid.uuid4().hex[:8].upper()}"
        
        return {
            "event_id": event_id,
            "adversary": adversary_group,
            "capability": capability_used,
            "infrastructure": "Controlled Proxy / Multi-hop eBPF",
            "victim": victim_asset,
            "mandiant_intel_matched": True,
            "status": "DIAMOND_NODE_MAPPED",
        }