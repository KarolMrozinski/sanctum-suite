from __future__ import annotations

import json
from typing import Any


class KafkaDebeziumConnector:
    """Builds Debezium-compatible change events and connector metadata for Kafka-based pipelines."""

    def __init__(self, *, bootstrap_servers: str, topic_prefix: str = "sanctum", database: str = "sanctum") -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self.database = database

    def connector_config(self, *, table_include_list: list[str] | None = None, database_hostname: str = "postgres") -> dict[str, Any]:
        return {
            "name": f"{self.topic_prefix}-dbz-connector",
            "config": {
                "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
                "database.hostname": database_hostname,
                "database.dbname": self.database,
                "database.user": "replicator",
                "database.password": "secret",
                "database.server.name": self.topic_prefix,
                "table.include.list": ",".join(table_include_list or ["public.*"]),
                "plugin.name": "pgoutput",
                "slot.name": f"{self.topic_prefix}_slot",
                "heartbeat.interval.ms": 10000,
                "bootstrap.servers": self.bootstrap_servers,
            },
        }

    @staticmethod
    def build_change_event(*, before: dict[str, Any] | None, after: dict[str, Any] | None, op: str, source: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "before": before,
            "after": after,
            "op": op,
            "source": source,
            "ts_ms": source.get("ts_ms", 0),
        }
        return {"schema": {"type": "struct", "fields": [], "optional": False, "name": "change.event"}, "payload": payload}

    def publish_event(self, *, before: dict[str, Any] | None, after: dict[str, Any] | None, op: str, source: dict[str, Any]) -> dict[str, Any]:
        return self.build_change_event(before=before, after=after, op=op, source=source)


DebeziumKafkaConnector = KafkaDebeziumConnector
