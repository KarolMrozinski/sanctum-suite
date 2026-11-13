from collections.abc import Mapping, Sequence
from typing import Any

from sanctum_suite.core.purple_team import PurpleTeamEmulationCoordinator


class ContinuousBasSimulator:
    """Evaluates operator-supplied detection telemetry for a synthetic scenario only."""

    def execute_lateral_movement_simulation(
        self,
        target_segment: str,
        expected_rule_id: str = "operator-configured-rule",
        observed_alerts: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        segment = target_segment.strip()
        if not segment:
            raise ValueError("An authorized segment label is required")
        result = PurpleTeamEmulationCoordinator().coordinate_emulation_cycle(
            red_vector=f"synthetic-lateral-movement:{segment}",
            blue_detection_rule=expected_rule_id,
            observed_alerts=observed_alerts,
        )
        return {
            **result,
            "target_segment": segment,
            "execution_mode": "SYNTHETIC_TELEMETRY_EVALUATION_ONLY",
            "lateral_movement_executed": False,
        }
