import pytest

from sanctum_suite.core.siem import SIEMIntegrationExporter


@pytest.mark.asyncio
async def test_configured_siem_webhook_uses_bearer_token(monkeypatch):
    monkeypatch.setenv("SANCTUM_SIEM_WEBHOOK_URL", "https://siem.example.test/events")
    monkeypatch.setenv("SANCTUM_SIEM_WEBHOOK_TOKEN", "test-secret")
    exporter = SIEMIntegrationExporter()
    captured = {}

    class Response:
        is_success = True

        def raise_for_status(self):
            return None

    class MockClient:
        def __init__(self, **kwargs):
            captured["client_options"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, json, headers):
            captured["url"] = url
            captured["payload"] = json
            captured["headers"] = headers
            return Response()

    monkeypatch.setattr("sanctum_suite.core.siem.httpx.AsyncClient", MockClient)
    assert await exporter.dispatch_webhook_alert({"event": "test"}) is True
    assert captured["headers"] == {"Authorization": "Bearer test-secret"}
    assert captured["client_options"]["follow_redirects"] is False


def test_siem_webhook_rejects_query_strings_and_credentials():
    with pytest.raises(ValueError, match="query"):
        SIEMIntegrationExporter("https://siem.example.test/events?token=secret")
    with pytest.raises(ValueError, match="credentials"):
        SIEMIntegrationExporter("https://user:pass@siem.example.test/events")
