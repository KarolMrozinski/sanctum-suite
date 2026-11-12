import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from sanctum_suite import describe_integrated_language_modules
from sanctum_suite.api import server
from sanctum_suite.main import app as cli_app


def test_modules_cli_lists_full_catalog(monkeypatch):
    api_key = "module-cli-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)

    result = CliRunner().invoke(cli_app, ["modules"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total_languages"] >= 4
    assert "ada" in payload["modules"]
    assert any(
        item["module_name"] == "sanctum_crypto_vault"
        for item in payload["modules"]["ada"]
    )


def test_modules_api_returns_full_catalog(monkeypatch):
    api_key = "module-api-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)

    response = TestClient(server.app).get(
        "/api/v1/modules",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_languages"] >= 4
    assert payload["total_modules"] >= 1
    assert "ada" in payload["modules"]
    assert any(
        item["module_name"] == "sanctum_crypto_vault"
        for item in payload["modules"]["ada"]
    )
    assert describe_integrated_language_modules()["ada"][0]["capability_id"].startswith(
        "security-capability:ada-module:"
    )
