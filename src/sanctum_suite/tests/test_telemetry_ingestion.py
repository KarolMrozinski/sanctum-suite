import hashlib
import json
import sqlite3

from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.telemetry_adapters import CEFEventFileParser
from sanctum_suite.core.telemetry_store import TelemetryEventStore


API_KEY = "telemetry-api-test-key-" + "a" * 32
SOURCE_KEY = "telemetry-source-test-key-" + "b" * 32
TOKEN = "c" * 64
TIMESTAMP = "2026-10-18T10:00:00Z"


def configure_telemetry(monkeypatch, tmp_path):
    database = tmp_path / "telemetry.sqlite3"
    monkeypatch.setenv("SANCTUM_API_KEY", API_KEY)
    monkeypatch.setenv(
        "SANCTUM_EVENT_SOURCE_KEYS",
        json.dumps({"identity-provider": SOURCE_KEY, "network-sensor": "n" * 40}),
    )
    monkeypatch.setenv("SANCTUM_EVENT_RETENTION_DAYS", "30")
    monkeypatch.setenv("SANCTUM_CASES_DB", str(database))
    monkeypatch.delenv("SANCTUM_CASE_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("SANCTUM_ACCESS_AUDIT_RETENTION_DAYS", raising=False)
    monkeypatch.setattr(server, "incident_case_store", None)
    monkeypatch.setattr(server, "incident_governance_store", None)
    monkeypatch.setattr(server, "telemetry_event_store", TelemetryEventStore(database))
    return TestClient(server.app), database


def test_push_ingestion_authenticates_source_and_correlates_across_batches(
    monkeypatch, tmp_path
):
    client, database = configure_telemetry(monkeypatch, tmp_path)
    headers = {
        "X-Sanctum-Source-ID": "identity-provider",
        "X-Sanctum-Source-Key": SOURCE_KEY,
    }
    first = client.post(
        "/api/v1/telemetry/ingest",
        headers=headers,
        json={
            "events": [
                {
                    "source_event_id": "external-user-123",
                    "event_type": "identity.login",
                    "observed_at": TIMESTAMP,
                    "severity": "MEDIUM",
                    "correlation_token": TOKEN,
                }
            ]
        },
    )
    assert first.status_code == 200
    assert first.json()["inserted_count"] == 1
    assert first.json()["raw_payload_persisted"] is False
    duplicate = client.post(
        "/api/v1/telemetry/ingest",
        headers=headers,
        json={
            "events": [
                {
                    "source_event_id": "external-user-123",
                    "event_type": "changed.event",
                    "observed_at": TIMESTAMP,
                    "correlation_token": "d" * 64,
                }
            ]
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["inserted_count"] == 0
    assert duplicate.json()["duplicate_count"] == 1

    second = client.post(
        "/api/v1/telemetry/ingest",
        headers={
            "X-Sanctum-Source-ID": "network-sensor",
            "X-Sanctum-Source-Key": "n" * 40,
        },
        json={
            "events": [
                {
                    "source_event_id": "external-flow-456",
                    "event_type": "network.connection",
                    "observed_at": "2026-10-18T10:01:00+00:00",
                    "correlation_token": TOKEN,
                }
            ]
        },
    )
    assert second.status_code == 200
    assert len(second.json()["correlations"]) == 1
    assert second.json()["correlations"][0]["event_count"] == 2

    catalog = client.get("/api/v1/telemetry/connectors", headers={"X-API-Key": API_KEY})
    assert catalog.status_code == 200
    assert SOURCE_KEY not in catalog.text
    assert "identity-provider" in catalog.json()["sources"][0]["source_id"]

    unauthorized = client.post(
        "/api/v1/telemetry/ingest",
        headers={**headers, "X-Sanctum-Source-Key": "wrong"},
        json={"events": []},
    )
    assert unauthorized.status_code == 401

    rows = sqlite3.connect(database).execute(
        "SELECT source_event_id_sha256, correlation_token_sha256, event_type "
        "FROM normalized_telemetry_events"
    ).fetchall()
    persisted = " ".join(value for row in rows for value in row if value)
    assert "external-user-123" not in persisted
    assert "external-flow-456" not in persisted
    assert TOKEN not in persisted


def test_telemetry_to_purple_team_report_workflow(monkeypatch, tmp_path):
    client, _ = configure_telemetry(monkeypatch, tmp_path)
    source_headers = {
        "X-Sanctum-Source-ID": "identity-provider",
        "X-Sanctum-Source-Key": SOURCE_KEY,
    }
    ingest = client.post(
        "/api/v1/telemetry/ingest",
        headers=source_headers,
        json={
            "events": [
                {
                    "source_event_id": "alert-1",
                    "event_type": "detection.alert",
                    "observed_at": TIMESTAMP,
                    "severity": "HIGH",
                    "correlation_token": TOKEN,
                    "detection_scenario_id": "identity-change-review",
                    "detection_rule_id": "ID-PRIV-CHANGE",
                },
                {
                    "source_event_id": "event-2",
                    "event_type": "identity.privilege_change",
                    "observed_at": "2026-10-18T10:01:00Z",
                    "correlation_token": TOKEN,
                },
            ]
        },
    )
    assert ingest.status_code == 200, ingest.text
    assert len(ingest.json()["correlations"]) == 1
    timeline = ingest.json()["correlations"][0]["timeline"]
    detection = next(event for event in timeline if event["detection_rule_id"])
    assert detection["detection_scenario_id"] == "identity-change-review"
    assert detection["detection_rule_id"] == "ID-PRIV-CHANGE"

    headers = {"X-API-Key": API_KEY}
    created = client.post(
        "/api/v1/cases",
        headers=headers,
        json={
            "title": "Identity change detection replay",
            "summary": "Review normalized identity and detection telemetry.",
            "created_by": "analyst-1",
            "priority": "HIGH",
            "correlation_id": ingest.json()["correlations"][0]["correlation_id"],
            "priority_reasons": ["Source-reported HIGH severity."],
            "timeline": timeline,
        },
    )
    assert created.status_code == 201, created.text
    case_id = created.json()["case_id"]

    replay = client.post(
        f"/api/v1/cases/{case_id}/purple-team/replays",
        headers=headers,
        json={
            "scenario_id": "identity-change-review",
            "expected_rule_id": "ID-PRIV-CHANGE",
            "evaluated_by": "analyst-1",
        },
    )
    assert replay.status_code == 201, replay.text
    replay_record = replay.json()
    assert replay_record["result"]["detection_verified"] is True
    assert replay_record["result"]["matched_alert"]["event_id"] == detection["event_id"]
    assert replay_record["result"]["execution_mode"] == "OFFLINE_EVALUATION_ONLY"

    missing_detection = client.post(
        f"/api/v1/cases/{case_id}/purple-team/replays",
        headers=headers,
        json={
            "scenario_id": "identity-change-review",
            "expected_rule_id": "UNEXPECTED-RULE",
            "evaluated_by": "analyst-1",
        },
    )
    assert missing_detection.status_code == 201
    assert missing_detection.json()["result"]["detection_verified"] is False

    case = client.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert case.status_code == 200
    assert len(case.json()["purple_team_replays"]) == 2
    report_response = client.get(
        f"/api/v1/cases/{case_id}/report",
        headers=headers,
    )
    assert report_response.status_code == 200
    report = report_response.json()
    digest = report.pop("report_sha256")
    assert digest == hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert report["case"]["case_id"] == case_id
    assert len(report["case"]["purple_team_replays"]) == 2
    assert "truth" in " ".join(report["limitations"])

    invalid_replay = client.post(
        f"/api/v1/cases/{case_id}/purple-team/replays",
        headers=headers,
        json={
            "scenario_id": "identity-change-review",
            "expected_rule_id": "ID-PRIV-CHANGE",
            "evaluated_by": "analyst-1",
            "observed_alerts": [],
        },
    )
    assert invalid_replay.status_code == 422


def test_file_import_supports_json_jsonl_and_cef_without_echoing_payload(
    monkeypatch, tmp_path
):
    client, database = configure_telemetry(monkeypatch, tmp_path)
    headers = {"X-API-Key": API_KEY}
    imports = [
        (
            "json",
            json.dumps(
                [
                    {
                        "source_event_id": "json-event",
                        "event_type": "auth.login",
                        "observed_at": TIMESTAMP,
                        "correlation_token": TOKEN,
                    }
                ]
            ),
        ),
        (
            "jsonl",
            json.dumps(
                {
                    "source_event_id": "jsonl-event",
                    "event_type": "endpoint.alert",
                    "observed_at": TIMESTAMP,
                    "severity": "HIGH",
                }
            ),
        ),
        (
            "cef",
            "CEF:0|Example|Sensor|1|sig-7|Login event|8|"
            "externalId=cef-event rt=2026-10-18T10:00:00Z "
            f"cs1Label=correlation_token cs1={TOKEN}",
        ),
    ]
    for format_name, content in imports:
        response = client.post(
            "/api/v1/telemetry/import",
            headers=headers,
            json={
                "source_id": "identity-provider",
                "format": format_name,
                "content": content,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["raw_payload_persisted"] is False
        assert content not in response.text

    events = client.get("/api/v1/telemetry/events", headers=headers)
    assert events.status_code == 200
    assert events.json()["retained_event_count"] == 3
    assert {event["event_type"] for event in events.json()["events"]} == {
        "auth.login",
        "endpoint.alert",
        "cef.Example.Sensor.sig-7",
    }

    persisted = " ".join(
        str(value)
        for row in sqlite3.connect(database).execute(
            "SELECT * FROM normalized_telemetry_events"
        )
        for value in row
    )
    assert "json-event" not in persisted
    assert "jsonl-event" not in persisted
    assert "cef-event" not in persisted
    assert TOKEN not in persisted
    assert "Login event" not in persisted


def test_telemetry_requires_retention_and_import_source_configuration(
    monkeypatch, tmp_path
):
    client, _ = configure_telemetry(monkeypatch, tmp_path)
    monkeypatch.delenv("SANCTUM_EVENT_RETENTION_DAYS")
    response = client.post(
        "/api/v1/telemetry/import",
        headers={"X-API-Key": API_KEY},
        json={
            "source_id": "identity-provider",
            "format": "json",
            "content": "[]",
        },
    )
    assert response.status_code == 503

    monkeypatch.setenv("SANCTUM_EVENT_RETENTION_DAYS", "30")
    response = client.post(
        "/api/v1/telemetry/import",
        headers={"X-API-Key": API_KEY},
        json={
            "source_id": "not-configured",
            "format": "json",
            "content": "[]",
        },
    )
    assert response.status_code == 403

    monkeypatch.delenv("SANCTUM_EVENT_RETENTION_DAYS")
    push_response = client.post(
        "/api/v1/telemetry/ingest",
        headers={
            "X-Sanctum-Source-ID": "identity-provider",
            "X-Sanctum-Source-Key": SOURCE_KEY,
        },
        json={
            "events": [
                {
                    "source_event_id": "event-1",
                    "event_type": "identity.login",
                    "observed_at": TIMESTAMP,
                }
            ]
        },
    )
    assert push_response.status_code == 503


def test_retention_removes_expired_events_and_batch_metadata(monkeypatch, tmp_path):
    client, database = configure_telemetry(monkeypatch, tmp_path)
    store = server.get_telemetry_event_store()
    store.ingest(
        "identity-provider",
        [
            {
                "source_event_id": "expired-event",
                "event_type": "identity.login",
                "observed_at": TIMESTAMP,
            }
        ],
    )
    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE normalized_telemetry_events SET ingested_at = '2020-01-01T00:00:00+00:00'"
    )
    connection.execute(
        "UPDATE telemetry_ingestion_batches SET received_at = '2020-01-01T00:00:00+00:00'"
    )
    connection.commit()
    connection.close()

    response = client.get(
        "/api/v1/telemetry/events",
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 200
    assert response.json()["events"] == []
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM telemetry_ingestion_batches"
    ).fetchone()[0] == 0
    connection.close()


def test_invalid_correlation_window_fails_before_persisting_events(
    monkeypatch, tmp_path
):
    client, database = configure_telemetry(monkeypatch, tmp_path)
    monkeypatch.setenv("SANCTUM_EVENT_CORRELATION_WINDOW_HOURS", "not-a-number")
    response = client.post(
        "/api/v1/telemetry/ingest",
        headers={
            "X-Sanctum-Source-ID": "identity-provider",
            "X-Sanctum-Source-Key": SOURCE_KEY,
        },
        json={
            "events": [
                {
                    "source_event_id": "must-not-persist",
                    "event_type": "identity.login",
                    "observed_at": TIMESTAMP,
                }
            ]
        },
    )
    assert response.status_code == 503
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM normalized_telemetry_events"
    ).fetchone()[0] == 0
    connection.close()


def test_cef_parser_requires_timestamp_and_valid_correlation_token():
    parser = CEFEventFileParser()
    valid = (
        "CEF:0|Example|Sensor|1|sig-7|Login event|8|"
        f"rt={TIMESTAMP} cs1Label=correlation_token cs1={TOKEN}"
    )
    event = parser.parse(valid, max_events=1)[0]
    assert event["severity"] == "HIGH"
    assert event["correlation_token"] == TOKEN

    try:
        parser.parse("CEF:0|Example|Sensor|1|sig-7|Login event|8|", max_events=1)
    except ValueError as error:
        assert "requires an rt timestamp" in str(error)
    else:
        raise AssertionError("CEF events without rt must be rejected")

    try:
        parser.parse(
            "CEF:0|Example|Sensor|1|sig-7|Login event|8|"
            "rt=2026-10-18T10:00:00Z "
            "cs1Label=correlation_token cs1=not-a-hash",
            max_events=1,
        )
    except ValueError as error:
        assert "lowercase SHA-256 token" in str(error)
    else:
        raise AssertionError("Invalid correlation tokens must be rejected")


def test_invalid_import_response_does_not_echo_raw_payload(monkeypatch, tmp_path):
    client, _ = configure_telemetry(monkeypatch, tmp_path)
    secret_payload = "sensitive-raw-event-content"
    response = client.post(
        "/api/v1/telemetry/import",
        headers={"X-API-Key": API_KEY},
        json={
            "source_id": "identity-provider",
            "format": "json",
            "content": secret_payload,
        },
    )
    assert response.status_code == 422
    assert secret_payload not in response.text

    sensitive_identifier = "private-source-identifier-" + ("x" * 300)
    response = client.post(
        "/api/v1/telemetry/import",
        headers={"X-API-Key": API_KEY},
        json={
            "source_id": "identity-provider",
            "format": "json",
            "content": json.dumps(
                [
                    {
                        "source_event_id": sensitive_identifier,
                        "event_type": "identity.login",
                        "observed_at": TIMESTAMP,
                    }
                ]
            ),
        },
    )
    assert response.status_code == 422
    assert sensitive_identifier not in response.text
    assert "private-source-identifier-" not in response.text
