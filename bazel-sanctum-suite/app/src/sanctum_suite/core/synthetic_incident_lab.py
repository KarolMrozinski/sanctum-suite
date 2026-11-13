"""In-memory synthetic incident scenarios for offline demonstrations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sanctum_suite.core.xdr_correlator import RealtimeXdrMeshCorrelator


_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "scenario_id": "identity-change-review",
        "title": "Synthetic identity change review",
        "description": (
            "An illustrative sign-in, access change, and follow-up alert from "
            "fictional sources."
        ),
        "learning_objectives": [
            "Read related events in timestamp order.",
            "Distinguish source-reported severity from an assessed threat.",
            "Record a case and review a recommendation-only playbook.",
        ],
        "events": (
            ("identity.sign_in", "synthetic-identity", "INFO"),
            ("identity.privilege_change", "synthetic-identity", "HIGH"),
            ("detection.access_review_alert", "synthetic-detection", "MEDIUM"),
        ),
    },
    {
        "scenario_id": "service-configuration-review",
        "title": "Synthetic service configuration review",
        "description": (
            "A fictional service setting change, exposure observation, and "
            "configuration alert for analyst triage practice."
        ),
        "learning_objectives": [
            "Correlate configuration observations using an exact synthetic key.",
            "Review evidence references without uploading evidence content.",
            "Practice case status and assignment workflows.",
        ],
        "events": (
            ("service.configuration_change", "synthetic-config", "MEDIUM"),
            ("service.exposure_observed", "synthetic-inventory", "HIGH"),
            ("detection.configuration_alert", "synthetic-detection", "MEDIUM"),
        ),
    },
)
_SCENARIOS_BY_ID = {scenario["scenario_id"]: scenario for scenario in _SCENARIOS}


class SyntheticIncidentLab:
    """Creates synthetic event batches in memory; never reads or writes real telemetry."""

    def __init__(self, correlator: RealtimeXdrMeshCorrelator | None = None) -> None:
        self._correlator = correlator or RealtimeXdrMeshCorrelator()

    @staticmethod
    def list_scenarios() -> list[dict[str, Any]]:
        return [
            {
                "scenario_id": scenario["scenario_id"],
                "title": scenario["title"],
                "description": scenario["description"],
                "learning_objectives": list(scenario["learning_objectives"]),
                "event_count": len(scenario["events"]),
                "data_classification": "SYNTHETIC",
                "external_connections": False,
                "writes_case_data": False,
            }
            for scenario in _SCENARIOS
        ]

    def run(self, scenario_id: str) -> dict[str, Any] | None:
        scenario = _SCENARIOS_BY_ID.get(scenario_id)
        if scenario is None:
            return None

        run_id = uuid.uuid4().hex[:12].upper()
        correlation_key = f"SYNTHETIC-{scenario_id}-{run_id}"
        start = datetime.now(timezone.utc).replace(microsecond=0)
        events = [
            {
                "event_id": f"SYN-{run_id}-{index + 1:02d}",
                "event_type": event_type,
                "correlation_key": correlation_key,
                "source": source,
                "observed_at": (start + timedelta(minutes=index * 3)).isoformat().replace(
                    "+00:00", "Z"
                ),
                "severity": severity,
            }
            for index, (event_type, source, severity) in enumerate(scenario["events"])
        ]
        correlation_result = self._correlator.ingest_telemetry_stream(events)
        correlations = [
            {
                **correlation,
                "synthetic": True,
                "scenario_id": scenario_id,
                "scenario_title": scenario["title"],
                "synthetic_run_id": run_id,
            }
            for correlation in correlation_result["correlations"]
        ]
        return {
            "status": "SYNTHETIC_DEMO_ONLY",
            "data_classification": "SYNTHETIC",
            "synthetic": True,
            "scenario": {
                "scenario_id": scenario["scenario_id"],
                "title": scenario["title"],
                "description": scenario["description"],
                "learning_objectives": list(scenario["learning_objectives"]),
            },
            "run_id": run_id,
            "events": events,
            "correlations": correlations,
            "persisted": False,
            "external_connections": False,
            "limitations": (
                "Generated in memory from fixed fictional fixtures. No production "
                "telemetry is read, no external connection is made, and no event, "
                "case, response, or system change is persisted or executed."
            ),
        }
