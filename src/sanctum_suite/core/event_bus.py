import asyncio
from typing import Dict, Any, List, Callable


class DistributedEventBus:
    """Rozproszona magistrala zdarzeń dla klastrów agentów SANCTUM-SUITE (Kafka/RabbitMQ Pattern)."""

    def __init__(self) -> None:
        self._topics: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subskrybuje dany temat w magistrali zdarzeń."""
        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(callback)

    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publikuje wiadomość w temacie i powiadamia subskrybentów."""
        if topic in self._topics:
            for callback in self._topics[topic]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)