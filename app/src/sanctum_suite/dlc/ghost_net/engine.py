from typing import Any


class GhostNetC2SimulationEngine:
    """Reports that covert-channel and command-and-control simulation is disabled."""

    def simulate_covert_channel(self, protocol_type: str = "DNS_TUNNELING") -> dict[str, Any]:
        return {
            "addon": "SANCTUM-DLC-GHOST-NET",
            "protocol": protocol_type,
            "status": "NOT_IMPLEMENTED",
            "simulation_started": False,
            "mesh_telemetry": None,
            "dga_generated_nodes": None,
            "exfiltration_details": None,
        }
