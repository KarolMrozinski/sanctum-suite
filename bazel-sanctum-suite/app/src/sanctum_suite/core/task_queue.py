import uuid
import asyncio
from typing import Dict, Any, Optional


class AsyncTaskQueueManager:
    """Manager kolejkujący zadania audytowe w tle (Celery/Redis Queue pattern)."""

    def __init__(self) -> None:
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def enqueue_audit_task(self, target_domain: str) -> str:
        """Kolejkuje nowe zadanie audytowe i zwraca UUID taska."""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        self.tasks[task_id] = {
            "task_id": task_id,
            "target": target_domain,
            "status": "QUEUED",
            "result": None,
        }
        return task_id

    async def process_task(self, task_id: str, orchestrator_func) -> Dict[str, Any]:
        """Wykonuje asynchronicznie zadanie audytu i aktualizuje stan."""
        if task_id not in self.tasks:
            raise KeyError("Task ID not found")

        self.tasks[task_id]["status"] = "RUNNING"
        
        # Wykonanie audytu w pętli asynchronicznej
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, orchestrator_func, self.tasks[task_id]["target"])

        self.tasks[task_id]["status"] = "COMPLETED"
        self.tasks[task_id]["result"] = result
        return self.tasks[task_id]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Pobiera status i wynik wykonania zadania."""
        return self.tasks.get(task_id)