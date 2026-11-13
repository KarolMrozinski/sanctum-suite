from pathlib import Path

import pytest
from typer.testing import CliRunner

from sanctum_suite import main
from sanctum_suite.core.privacy_graph import (
    PrivacyGraphError,
    _encrypt_scores,
    fhe_accelerator_capabilities,
)


class FakeAccelerator:
    backend_name = "test-fhe-accelerator"

    def encrypt_and_aggregate(self, *, public_key_path, parameters_path, scores):
        assert public_key_path.name == "public.seal"
        assert parameters_path.name == "parameters.json"
        return (
            [(entry["node_id"], b"encrypted") for entry in scores],
            b"aggregate",
            {"scheme": "test"},
        )


def test_fhe_accelerator_protocol_is_injectable_and_labels_execution_backend():
    encrypted, aggregate, metadata = _encrypt_scores(
        public_key_path=Path("public.seal"),
        parameters_path=Path("parameters.json"),
        scores=[{"node_id": "node-a", "score": 42}],
        accelerator_backend=FakeAccelerator(),
    )

    assert encrypted == [("node-a", b"encrypted")]
    assert aggregate == b"aggregate"
    assert metadata == {
        "scheme": "test",
        "execution_backend": "test-fhe-accelerator",
    }


def test_fhe_accelerator_protocol_rejects_missing_score_ciphertexts():
    class InvalidAccelerator:
        backend_name = "invalid"

        def encrypt_and_aggregate(self, **_kwargs):
            return [], b"aggregate", {}

    with pytest.raises(PrivacyGraphError, match="one ciphertext per score"):
        _encrypt_scores(
            public_key_path=Path("public.seal"),
            parameters_path=Path("parameters.json"),
            scores=[{"node_id": "node-a", "score": 42}],
            accelerator_backend=InvalidAccelerator(),
        )


def test_fhe_capability_report_does_not_claim_accelerator_support(monkeypatch):
    monkeypatch.setattr(
        "sanctum_suite.core.privacy_graph.importlib.util.find_spec",
        lambda _name: None,
    )
    monkeypatch.setattr(
        "sanctum_suite.core.privacy_graph.shutil.which",
        lambda _name: None,
    )

    status = fhe_accelerator_capabilities()

    assert status["status"] == "CAPABILITY_REPORT_ONLY"
    assert status["cpu_backend"]["execution"] == "CPU"
    assert status["cpu_backend"]["python_binding_available"] is False
    assert status["accelerator_backends"]["gpu"]["status"] == "NOT_IMPLEMENTED"
    assert status["accelerator_backends"]["fpga"]["status"] == "NOT_IMPLEMENTED"
    assert "do not prove" in status["limitations"]


def test_fhe_accelerator_status_cli_reports_capability_without_claiming_offload(
    monkeypatch,
):
    monkeypatch.setattr(
        "sanctum_suite.core.privacy_graph.importlib.util.find_spec",
        lambda _name: None,
    )
    monkeypatch.setattr(
        "sanctum_suite.core.privacy_graph.shutil.which",
        lambda _name: None,
    )

    result = CliRunner().invoke(main.app, ["fhe-accelerator-status"])

    assert result.exit_code == 0, result.output
    assert '"status": "NOT_IMPLEMENTED"' in result.stdout
    assert '"execution": "CPU"' in result.stdout
