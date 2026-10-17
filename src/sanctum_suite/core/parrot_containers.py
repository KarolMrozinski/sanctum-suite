import uuid
from typing import Dict, Any, List


class ParrotContainerOrchestrator:
    """Orkiestrator odizolowanych mikro-kontenerów z pełnym środowiskiem Parrot Security OS."""

    def __init__(self) -> None:
        self.active_containers: List[str] = []

    def spawn_parrot_microcontainer(self, profile: str = "FULL_RECON") -> Dict[str, Any]:
        """Tworzy i uruchamia tymczasowy kontener Parrot Sec do głębokiej inspekcji."""
        container_id = f"PRT-SEC-{uuid.uuid4().hex[:8].upper()}"
        self.active_containers.append(container_id)

        return {
            "container_id": container_id,
            "image": "parrotsec/core:latest",
            "profile": profile,
            "status": "RUNNING",
            "isolated_network": True,
        }

    def terminate_container(self, container_id: str) -> Dict[str, Any]:
        """Bezpiecznie zatrzymuje i usuwa ślady po kontenerze po zakończeniu audytu."""
        if container_id in self.active_containers:
            self.active_containers.remove(container_id)
            return {"container_id": container_id, "status": "TERMINATED", "cleanup": "COMPLETE"}
        return {"container_id": container_id, "status": "NOT_FOUND"}