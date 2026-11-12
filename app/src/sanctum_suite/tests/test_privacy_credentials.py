import base64
import json
import sqlite3
from decimal import Decimal, localcontext

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.privacy_credentials import (
    DifferentialPrivacyCredentialIssuer,
    PrivacyBudgetExceeded,
    did_key_document,
    did_key_from_public_key,
    verify_credential_jwt,
)


PRIVATE_KEY_BYTES = bytes(range(32))
API_KEY = "privacy-credential-api-key-" + "x" * 32


def make_issuer(tmp_path, *, max_epsilon=1.0):
    return DifferentialPrivacyCredentialIssuer(
        database_path=tmp_path / "privacy-budget.sqlite3",
        signing_key=Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY_BYTES),
        max_epsilon=max_epsilon,
    )


def test_issuer_creates_verifiable_w3c_credential_and_did_document(tmp_path):
    issuer = make_issuer(tmp_path)
    credential = issuer.issue(
        dataset_id="quarterly-audit",
        categories=["critical", "high"],
        observations=[
            {"subject_id": "person-1", "category": "critical"},
            {"subject_id": "person-2", "category": "high"},
        ],
        epsilon=0.5,
    )

    payload = verify_credential_jwt(credential["credential_jwt"])
    subject = payload["vc"]["credentialSubject"]
    assert credential["issuer_did"] == did_key_from_public_key(
        Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY_BYTES).public_key()
    )
    assert credential["did_document"] == did_key_document(credential["issuer_did"])
    assert payload["iss"] == credential["issuer_did"]
    assert payload["vc"]["type"] == [
        "VerifiableCredential",
        "PrivacyPreservingAuditCredential",
    ]
    assert set(subject["categoryCounts"]) == {"critical", "high"}
    assert all(value >= 0 for value in subject["categoryCounts"].values())
    assert subject["privacy"]["epsilon"] == 0.5
    assert subject["privacy"]["delta"] == 0
    assert subject["privacy"]["mechanism"] == "discrete_laplace"
    with localcontext() as context:
        context.prec = 80
        parameter = Decimal(
            subject["privacy"]["noiseParameterNumerator"]
        ) / Decimal(subject["privacy"]["noiseParameterDenominator"])
        assert parameter >= (-Decimal("0.5")).exp()
    assert "person-1" not in credential["credential_jwt"]
    assert "quarterly-audit" not in credential["credential_jwt"]


def test_credential_signature_and_dataset_budget_survive_issuer_restart(tmp_path):
    issuer = make_issuer(tmp_path)
    credential = issuer.issue(
        dataset_id="stable-dataset",
        categories=["open"],
        observations=[{"subject_id": "subject-1", "category": "open"}],
        epsilon=0.6,
    )
    assert credential["privacy_budget"]["epsilon_spent"] == 0.6

    restarted_issuer = make_issuer(tmp_path)
    with pytest.raises(PrivacyBudgetExceeded):
        restarted_issuer.issue(
            dataset_id="stable-dataset",
            categories=["open"],
            observations=[{"subject_id": "subject-2", "category": "open"}],
            epsilon=0.6,
        )

    connection = sqlite3.connect(tmp_path / "privacy-budget.sqlite3")
    persisted = connection.execute(
        "SELECT dataset_key_sha256, epsilon_spent FROM privacy_dataset_budgets"
    ).fetchone()
    connection.close()
    assert persisted[0] != "stable-dataset"
    assert float(persisted[1]) == 0.6


def test_decimal_epsilon_composition_does_not_overrun_budget(tmp_path):
    issuer = make_issuer(tmp_path, max_epsilon=0.3)
    arguments = {
        "dataset_id": "decimal-budget",
        "categories": ["open"],
        "observations": [],
        "epsilon": 0.1,
    }
    for _ in range(3):
        issuer.issue(**arguments)
    with pytest.raises(PrivacyBudgetExceeded):
        issuer.issue(**arguments)


def test_invalid_contributions_and_nonpublic_categories_are_rejected(tmp_path):
    issuer = make_issuer(tmp_path)
    duplicate_subjects = [
        {"subject_id": "subject-1", "category": "open"},
        {"subject_id": "subject-1", "category": "open"},
    ]
    with pytest.raises(ValueError, match="at most one observation"):
        issuer.issue(
            dataset_id="dataset",
            categories=["open"],
            observations=duplicate_subjects,
            epsilon=0.5,
        )
    with pytest.raises(ValueError, match="public categories"):
        issuer.issue(
            dataset_id="dataset",
            categories=["open"],
            observations=[{"subject_id": "subject-1", "category": "secret"}],
            epsilon=0.5,
        )
    with pytest.raises(ValueError, match="public labels"):
        issuer.issue(
            dataset_id="dataset",
            categories=["sensitive free text"],
            observations=[],
            epsilon=0.5,
        )


def test_budget_store_cannot_be_volatile(tmp_path):
    with pytest.raises(ValueError, match="persistent SQLite file"):
        DifferentialPrivacyCredentialIssuer(
            database_path=":memory:",
            signing_key=Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY_BYTES),
        )


def test_tampered_credential_is_rejected(tmp_path):
    issuer = make_issuer(tmp_path)
    token = issuer.issue(
        dataset_id="dataset",
        categories=["open"],
        observations=[],
        epsilon=0.5,
    )["credential_jwt"]
    header, payload, signature = token.split(".")
    changed_payload = json.loads(
        base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    )
    changed_payload["iss"] = "did:key:zinvalid"
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(changed_payload, separators=(",", ":"), sort_keys=True).encode()
    ).rstrip(b"=").decode()
    with pytest.raises(ValueError, match="issuer and verification method"):
        verify_credential_jwt(f"{header}.{encoded_payload}.{signature}")


def configure_api(monkeypatch, tmp_path):
    monkeypatch.setenv("SANCTUM_API_KEY", API_KEY)
    monkeypatch.setenv(
        "SANCTUM_DP_VC_ED25519_PRIVATE_KEY",
        base64.b64encode(PRIVATE_KEY_BYTES).decode("ascii"),
    )
    monkeypatch.setenv(
        "SANCTUM_PRIVACY_BUDGET_DB", str(tmp_path / "api-budget.sqlite3")
    )
    monkeypatch.setenv("SANCTUM_DP_MAX_EPSILON", "1")
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    return TestClient(server.app)


def request_payload():
    return {
        "dataset_id": "quarterly-audit",
        "categories": ["critical", "high"],
        "observations": [
            {"subject_id": "person-1", "category": "critical"},
            {"subject_id": "person-2", "category": "high"},
        ],
        "epsilon": 0.6,
    }


def test_api_requires_authentication_and_returns_signed_credential(
    monkeypatch, tmp_path
):
    client = configure_api(monkeypatch, tmp_path)
    endpoint = "/api/v1/privacy/credentials"
    assert client.post(endpoint, json=request_payload()).status_code == 401

    response = client.post(
        endpoint,
        headers={"X-API-Key": API_KEY},
        json=request_payload(),
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert verify_credential_jwt(result["credential_jwt"])["iss"] == result[
        "issuer_did"
    ]
    assert result["privacy_budget"] == {
        "epsilon_spent": 0.6,
        "epsilon_remaining": 0.4,
        "maximum_epsilon": 1.0,
    }


def test_api_rejects_budget_overrun_and_missing_signing_key(monkeypatch, tmp_path):
    client = configure_api(monkeypatch, tmp_path)
    endpoint = "/api/v1/privacy/credentials"
    headers = {"X-API-Key": API_KEY}
    assert client.post(endpoint, headers=headers, json=request_payload()).status_code == 200
    overrun = client.post(endpoint, headers=headers, json=request_payload())
    assert overrun.status_code == 429

    monkeypatch.delenv("SANCTUM_DP_VC_ED25519_PRIVATE_KEY")
    unconfigured = client.post(
        endpoint,
        headers=headers,
        json={**request_payload(), "dataset_id": "another-dataset"},
    )
    assert unconfigured.status_code == 503


def test_api_rejects_invalid_categories_before_issuing(monkeypatch, tmp_path):
    client = configure_api(monkeypatch, tmp_path)
    payload = request_payload()
    payload["categories"] = ["sensitive free text"]
    response = client.post(
        "/api/v1/privacy/credentials",
        headers={"X-API-Key": API_KEY},
        json=payload,
    )
    assert response.status_code == 422


def test_api_sanitizes_validation_errors_for_sensitive_subject_ids(
    monkeypatch, tmp_path
):
    client = configure_api(monkeypatch, tmp_path)
    payload = request_payload()
    payload["observations"][0]["subject_id"] = "x" * 129
    response = client.post(
        "/api/v1/privacy/credentials",
        headers={"X-API-Key": API_KEY},
        json=payload,
    )
    assert response.status_code == 422
    assert "x" * 129 not in response.text


def test_api_fails_closed_when_budget_storage_is_unavailable(monkeypatch, tmp_path):
    client = configure_api(monkeypatch, tmp_path)
    monkeypatch.setenv("SANCTUM_PRIVACY_BUDGET_DB", str(tmp_path))
    response = client.post(
        "/api/v1/privacy/credentials",
        headers={"X-API-Key": API_KEY},
        json=request_payload(),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Privacy budget storage is unavailable"
