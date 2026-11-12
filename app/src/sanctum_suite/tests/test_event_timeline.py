from fastapi.testclient import TestClient

from sanctum_suite.api.server import app
from sanctum_suite.core.xdr_correlator import RealtimeXdrMeshCorrelator


def test_correlated_events_include_ordered_timeline_and_explainable_priority():
    result = RealtimeXdrMeshCorrelator().ingest_telemetry_stream(
        [
            {
                "event_id": "later",
                "event_type": "privilege-change",
                "correlation_key": "case-1",
                "source": "identity-provider",
                "observed_at": "2026-10-18T12:02:00+02:00",
                "severity": "HIGH",
            },
            {
                "event_id": "earlier",
                "event_type": "login",
                "correlation_key": "case-1",
                "source": "gateway",
                "observed_at": "2026-10-18T10:01:00Z",
                "severity": "LOW",
            },
        ]
    )

    correlation = result["correlations"][0]
    assert correlation["event_ids"] == ["later", "earlier"]
    assert [event["event_id"] for event in correlation["timeline"]] == [
        "earlier",
        "later",
    ]
    assert correlation["priority"] == "HIGH"
    assert "not independently verified" in correlation["priority_reasons"][1]
    assert correlation["threat_assessment"] == "NOT_ASSESSED"
    assert "malicious activity" in correlation["priority_reasons"][2]


def test_correlated_events_without_reported_severity_remain_unassessed():
    result = RealtimeXdrMeshCorrelator().ingest_telemetry_stream(
        [
            {"event_id": "e1", "event_type": "login", "correlation_key": "case-1"},
            {"event_id": "e2", "event_type": "logout", "correlation_key": "case-1"},
        ]
    )

    correlation = result["correlations"][0]
    assert correlation["priority"] == "NOT_ASSESSED"
    assert correlation["timeline"][0]["observed_at"] is None
    assert "No source-reported severity" in correlation["priority_reasons"][1]


def test_timeline_orders_subsecond_timestamps_correctly():
    result = RealtimeXdrMeshCorrelator().ingest_telemetry_stream(
        [
            {
                "event_id": "later",
                "event_type": "second",
                "correlation_key": "case-1",
                "observed_at": "2026-10-18T10:00:00.1Z",
            },
            {
                "event_id": "earlier",
                "event_type": "first",
                "correlation_key": "case-1",
                "observed_at": "2026-10-18T10:00:00Z",
            },
        ]
    )

    assert [event["event_id"] for event in result["correlations"][0]["timeline"]] == [
        "earlier",
        "later",
    ]


def test_correlation_api_accepts_timeline_fields_and_rejects_naive_timestamps(monkeypatch):
    api_key = "timeline-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    client = TestClient(app)
    headers = {"X-API-Key": api_key}
    events = [
        {
            "event_id": "e1",
            "event_type": "login",
            "correlation_key": "case-1",
            "source": "gateway",
            "observed_at": "2026-10-18T10:00:00Z",
            "severity": "MEDIUM",
        },
        {
            "event_id": "e2",
            "event_type": "privilege-change",
            "correlation_key": "case-1",
            "source": "identity-provider",
            "observed_at": "2026-10-18T10:01:00Z",
            "severity": "HIGH",
        },
    ]

    response = client.post(
        "/api/v1/events/correlate",
        headers=headers,
        json={"events": events},
    )

    assert response.status_code == 200
    correlation = response.json()["correlations"][0]
    assert correlation["priority"] == "HIGH"
    assert correlation["timeline"][0]["event_id"] == "e1"

    events[0]["observed_at"] = "2026-10-18T10:00:00"
    assert client.post(
        "/api/v1/events/correlate",
        headers=headers,
        json={"events": events},
    ).status_code == 422
