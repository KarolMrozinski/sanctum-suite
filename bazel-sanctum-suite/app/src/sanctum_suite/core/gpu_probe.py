from typing import Any


class GPUMemorySecurityProbe:
    """Reports GPU security as unassessed until a real device integration is configured."""

    def inspect_gpu_runtime(self) -> dict[str, Any]:
        return {
            "status": "NOT_ASSESSED",
            "cuda_version": None,
            "vram_status": "NOT_ASSESSED",
            "vllm_shared_memory_leak": None,
            "isolation_verified": None,
            "detected_issues": None,
            "device_inspected": False,
        }