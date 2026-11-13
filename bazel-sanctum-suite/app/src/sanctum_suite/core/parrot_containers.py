import uuid
from typing import Dict, Any, List


class ParrotContainerOrchestrator:
    """Prepares a pinned-image container plan without controlling a Docker daemon."""

    def __init__(self) -> None:
        self.active_containers: List[str] = []

    def spawn_parrot_microcontainer(self, profile: str = "FULL_RECON") -> Dict[str, Any]:
        """Return a container plan; no Docker image is downloaded or launched."""
        container_id = f"PRT-SEC-{uuid.uuid4().hex[:8].upper()}"

        return {
            "container_id": container_id,
            "image": None,
            "profile": profile,
            "status": "NOT_STARTED",
            "image_digest_required": True,
            "isolated_network": None,
            "container_started": False,
        }

    def terminate_container(self, container_id: str) -> Dict[str, Any]:
        """Report that no local container lifecycle action is available."""
        return {"container_id": container_id, "status": "NO_CONTAINER_WAS_STARTED"}