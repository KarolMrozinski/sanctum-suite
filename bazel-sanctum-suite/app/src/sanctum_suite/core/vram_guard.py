from typing import Any


class VramEnclaveGuardEngine:
    """Reports VRAM isolation as unimplemented without a hardware-backed guard."""

    def secure_gpu_memory_space(self, device_id: str) -> dict[str, Any]:
        return {
            "gpu_device": device_id,
            "status": "NOT_IMPLEMENTED",
            "encryption_status": "NOT_ASSESSED",
            "side_channel_mitigation": "NOT_ASSESSED",
            "prompt_leakage_risk": None,
            "device_modified": False,
        }
