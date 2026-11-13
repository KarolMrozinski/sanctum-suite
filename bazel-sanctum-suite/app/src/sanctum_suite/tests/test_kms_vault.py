import base64
import json

import httpx
import pytest

from sanctum_suite.core import kms_vault
from sanctum_suite.core.kms_vault import (
    KMSConfigurationError,
    VaultTransitError,
    ZeroTrustKMSVault,
)


_KMS_ENVIRONMENT = (
    "SANCTUM_ENVIRONMENT",
    "SANCTUM_KMS_BACKEND",
    "SANCTUM_VAULT_ADDR",
    "SANCTUM_VAULT_TOKEN",
    "SANCTUM_VAULT_TOKEN_FILE",
    "SANCTUM_VAULT_TRANSIT_MOUNT",
    "SANCTUM_VAULT_TRANSIT_KEY",
    "SANCTUM_VAULT_NAMESPACE",
    "SANCTUM_VAULT_CA_CERT",
)


def _clear_kms_environment(monkeypatch):
    for name in _KMS_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)


def test_production_requires_vault_transit(monkeypatch):
    _clear_kms_environment(monkeypatch)
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")

    with pytest.raises(KMSConfigurationError, match="requires SANCTUM_KMS_BACKEND"):
        ZeroTrustKMSVault()


def test_vault_settings_cannot_be_silently_ignored(monkeypatch):
    _clear_kms_environment(monkeypatch)
    monkeypatch.setenv("SANCTUM_VAULT_ADDR", "https://vault.internal")

    with pytest.raises(KMSConfigurationError, match="Set SANCTUM_KMS_BACKEND"):
        ZeroTrustKMSVault()


def test_vault_transit_encrypts_and_decrypts_through_configured_key(
    monkeypatch, tmp_path
):
    _clear_kms_environment(monkeypatch)
    token_file = tmp_path / "vault-token"
    token_file.write_text("vault-test-token\n", encoding="utf-8")
    monkeypatch.setenv("SANCTUM_KMS_BACKEND", "vault-transit")
    monkeypatch.setenv("SANCTUM_VAULT_ADDR", "https://vault.internal:8200")
    monkeypatch.setenv("SANCTUM_VAULT_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("SANCTUM_VAULT_TRANSIT_MOUNT", "transit")
    monkeypatch.setenv("SANCTUM_VAULT_TRANSIT_KEY", "sanctum-payload")
    monkeypatch.setenv("SANCTUM_VAULT_NAMESPACE", "security/lab")

    payload = "sensitive lab record"
    seen_operations = []

    def handle_request(request):
        assert request.headers["X-Vault-Token"] == "vault-test-token"
        assert request.headers["X-Vault-Namespace"] == "security/lab"
        seen_operations.append(request.url.path)
        body = request.read()
        if request.url.path.endswith("/encrypt/sanctum-payload"):
            encoded = json.loads(body)["plaintext"]
            return httpx.Response(
                200,
                json={"data": {"ciphertext": f"vault:v1:{encoded}"}},
            )
        assert request.url.path.endswith("/decrypt/sanctum-payload")
        encoded_ciphertext = json.loads(body)["ciphertext"].removeprefix("vault:v1:")
        return httpx.Response(
            200,
            json={"data": {"plaintext": encoded_ciphertext}},
        )

    real_client = httpx.Client
    transport = httpx.MockTransport(handle_request)

    def mock_client(**kwargs):
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(kms_vault.httpx, "Client", mock_client)
    vault = ZeroTrustKMSVault()
    envelope = vault.encrypt_payload(payload)

    assert envelope == {
        "ciphertext": "vault:v1:"
        + base64.b64encode(payload.encode("utf-8")).decode("ascii"),
        "key_management": "HASHICORP_VAULT_TRANSIT",
        "production_kms_configured": "true",
        "vault_transit_mount": "transit",
        "vault_transit_key": "sanctum-payload",
    }
    assert vault.decrypt_payload(envelope) == payload
    vault.verify_production_access()
    assert seen_operations == [
        "/v1/transit/encrypt/sanctum-payload",
        "/v1/transit/decrypt/sanctum-payload",
        "/v1/transit/encrypt/sanctum-payload",
        "/v1/transit/decrypt/sanctum-payload",
    ]
    assert "vault-test-token" not in str(envelope)


def test_vault_transit_rejects_envelopes_for_another_key(monkeypatch):
    _clear_kms_environment(monkeypatch)
    monkeypatch.setenv("SANCTUM_KMS_BACKEND", "vault-transit")
    monkeypatch.setenv("SANCTUM_VAULT_ADDR", "https://vault.internal")
    monkeypatch.setenv("SANCTUM_VAULT_TOKEN", "vault-test-token")
    monkeypatch.setenv("SANCTUM_VAULT_TRANSIT_KEY", "sanctum-payload")
    vault = ZeroTrustKMSVault()

    with pytest.raises(VaultTransitError, match="does not match"):
        vault.decrypt_payload(
            {
                "key_management": "HASHICORP_VAULT_TRANSIT",
                "vault_transit_mount": "transit",
                "vault_transit_key": "another-key",
                "ciphertext": "vault:v1:encrypted-value",
            }
        )


def test_vault_transit_errors_do_not_expose_response_body_or_token(monkeypatch):
    _clear_kms_environment(monkeypatch)
    monkeypatch.setenv("SANCTUM_KMS_BACKEND", "vault-transit")
    monkeypatch.setenv("SANCTUM_VAULT_ADDR", "https://vault.internal")
    monkeypatch.setenv("SANCTUM_VAULT_TOKEN", "vault-test-token")
    monkeypatch.setenv("SANCTUM_VAULT_TRANSIT_KEY", "sanctum-payload")

    real_client = httpx.Client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, json={"errors": ["do-not-log-this"]})
    )
    monkeypatch.setattr(
        kms_vault.httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )
    vault = ZeroTrustKMSVault()

    with pytest.raises(VaultTransitError) as error:
        vault.encrypt_payload("sensitive")
    assert "HTTP 403" in str(error.value)
    assert "vault-test-token" not in str(error.value)
    assert "do-not-log-this" not in str(error.value)
