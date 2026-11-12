"""Offline evaluation of synthetic Purple Team telemetry."""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any


class PurpleTeamEmulationCoordinator:
    """Compare caller-supplied synthetic scenario identifiers with observed alerts."""

    def coordinate_emulation_cycle(
        self,
        red_vector: str,
        blue_detection_rule: str,
        observed_alerts: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Evaluate supplied telemetry only; this method does not execute attack behavior."""
        scenario_id = red_vector.strip()
        expected_rule_id = blue_detection_rule.strip()
        if not scenario_id or not expected_rule_id:
            raise ValueError("Scenario and detection rule identifiers are required")

        if observed_alerts is None:
            return {
                "cycle_id": f"PT-EMU-{uuid.uuid4().hex[:8].upper()}",
                "scenario_id": scenario_id,
                "expected_rule_id": expected_rule_id,
                "detection_verified": None,
                "status": "PENDING_EXTERNAL_TELEMETRY",
                "execution_mode": "OFFLINE_EVALUATION_ONLY",
            }

        matched_alert = next(
            (
                alert
                for alert in observed_alerts
                if alert.get("scenario_id") == scenario_id
                and alert.get("rule_id") == expected_rule_id
            ),
            None,
        )
        return {
            "cycle_id": f"PT-EMU-{uuid.uuid4().hex[:8].upper()}",
            "scenario_id": scenario_id,
            "expected_rule_id": expected_rule_id,
            "detection_verified": matched_alert is not None,
            "matched_alert": dict(matched_alert) if matched_alert is not None else None,
            "status": "DETECTION_OBSERVED" if matched_alert is not None else "DETECTION_NOT_OBSERVED",
            "execution_mode": "OFFLINE_EVALUATION_ONLY",
        }
