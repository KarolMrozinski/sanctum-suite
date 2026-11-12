import importlib.util
import json

import pytest
from typer.testing import CliRunner

from sanctum_suite import main
from sanctum_suite.core.smpc import (
    SMPCError,
    _read_party_input,
    run_local_smpc_demo,
)


def _party_input(directory, name, value):
    path = directory / f"{name}.json"
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    return path


@pytest.mark.skipif(
    importlib.util.find_spec("mpyc") is None,
    reason="Optional MPyC dependency is not installed",
)
def test_local_smpc_computes_sum_and_threshold_without_revealing_inputs(tmp_path):
    inputs = [
        _party_input(tmp_path, "party-0", 120),
        _party_input(tmp_path, "party-1", 230),
        _party_input(tmp_path, "party-2", 450),
    ]
    result = CliRunner().invoke(
        main.app,
        [
            "smpc-aggregate-demo",
            "--party-0-input-file",
            str(inputs[0]),
            "--party-1-input-file",
            str(inputs[1]),
            "--party-2-input-file",
            str(inputs[2]),
            "--decision-threshold",
            "700",
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "LOCAL_SMPC_DEMO_COMPLETED"
    assert report["participant_count"] == 3
    assert report["threshold"] == 1
    assert report["aggregate_value"] == 800
    assert report["threshold_reached"] is True
    assert report["security_model"].startswith("semi-honest")
    assert all(str(value) not in result.stdout for value in (120, 230, 450))


def test_smpc_rejects_invalid_private_input_before_starting_parties(tmp_path):
    party = _party_input(tmp_path, "party-1", True)
    with pytest.raises(SMPCError, match="integer value"):
        _read_party_input(party)


@pytest.mark.skipif(
    importlib.util.find_spec("mpyc") is None,
    reason="Optional MPyC dependency is not installed",
)
def test_local_smpc_reports_threshold_not_reached(tmp_path):
    inputs = [
        _party_input(tmp_path, "party-0", 5),
        _party_input(tmp_path, "party-1", 5),
        _party_input(tmp_path, "party-2", 5),
    ]
    report = run_local_smpc_demo(
        participant_input_files=inputs,
        decision_threshold=16,
    )

    assert report["aggregate_value"] == 15
    assert report["threshold_reached"] is False


def test_smpc_requires_distinct_input_files_and_bounded_threshold(tmp_path):
    party = _party_input(tmp_path, "party", 10)

    with pytest.raises(SMPCError, match="separate input file"):
        run_local_smpc_demo(
            participant_input_files=[party, party, party],
            decision_threshold=10,
        )

    inputs = [
        _party_input(tmp_path, "party-0", 10),
        _party_input(tmp_path, "party-1", 10),
        _party_input(tmp_path, "party-2", 10),
    ]
    with pytest.raises(SMPCError, match="0 to 3000000"):
        run_local_smpc_demo(
            participant_input_files=inputs,
            decision_threshold=3_000_001,
        )
