import hashlib
import hmac
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sanctum_suite.api import server
from sanctum_suite.core.audit_pseudonymizer import AuditPseudonymizer
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.onchain import (
    ChainName,
    OnChainBlock,
    OnChainTransaction,
    TransactionInput,
    TransactionOutput,
)
from sanctum_suite.core.onchain_risk import OnChainRiskImportFile, OnChainRiskStore
from sanctum_suite.core.onchain_risk import OnChainRiskResultTooLarge


ADDRESS = "0x" + "a" * 40
ASSESSMENT = {
    "chain": "ethereum",
    "address": ADDRESS,
    "provider": "chainalysis",
    "provider_rating": "high",
    "category": "sanctions",
    "report_reference": "report-123",
    "assessed_at": "2026-10-19T12:00:00Z",
}


def report_content(address=ADDRESS):
    return json.dumps(
        {"schema_version": "1.0", "records": [{**ASSESSMENT, "address": address}]}
    )


def test_risk_import_normalizes_evm_address_and_rejects_chain_mismatch():
    upper_address = "0x" + "A" * 40
    report, _ = OnChainRiskImportFile.parse_content(report_content(upper_address))
    assert report.records[0].address == ADDRESS

    mismatch = {**ASSESSMENT, "chain": "bitcoin"}
    with pytest.raises(ValidationError):
        OnChainRiskImportFile.model_validate(
            {"schema_version": "1.0", "records": [mismatch]}
        )


def test_risk_store_is_case_scoped_idempotent_and_does_not_persist_plaintext_address(
    tmp_path,
):
    database = tmp_path / "cases.sqlite3"
    cases = IncidentCaseStore(database)
    case = cases.create_case(
        title="Risk report import",
        summary="Import a provider export for this case.",
        created_by="analyst",
    )
    other_case = cases.create_case(
        title="Separate case",
        summary="Provider assessment must not leak to another case.",
        created_by="analyst",
    )
    store = OnChainRiskStore(database)
    report, digest = OnChainRiskImportFile.parse_content(report_content())

    first = store.import_report(case["case_id"], report, report_sha256=digest)
    replay = store.import_report(case["case_id"], report, report_sha256=digest)

    assert first["inserted_count"] == 1
    assert replay["inserted_count"] == 0
    assert replay["duplicate_count"] == 1
    matching = store.list_for_addresses(case["case_id"], ChainName.ETHEREUM, [ADDRESS])
    assert matching[0]["provider"] == "chainalysis"
    assert matching[0]["provider_rating"] == "high"
    assert matching[0]["verification_status"] == "provider_reported_unverified"
    assert store.list_for_addresses(other_case["case_id"], ChainName.ETHEREUM, [ADDRESS]) == []

    persisted = sqlite3.connect(database).execute(
        "SELECT address_token, report_sha256, provider FROM onchain_risk_assessments"
    ).fetchone()
    assert ADDRESS not in persisted
    assert persisted[0] == hashlib.sha256(ADDRESS.encode()).hexdigest()
    assert persisted[1] == digest


def test_production_address_token_uses_namespace_separated_hmac(monkeypatch, tmp_path):
    key_file = tmp_path / "pseudonym.key"
    key_file.write_bytes(b"k" * 32)
    monkeypatch.setenv("SANCTUM_AUDIT_PSEUDONYM_KEY_FILE", str(key_file))
    pseudonymizer = AuditPseudonymizer()
    token = pseudonymizer.pseudonymize("onchain_address", ADDRESS)
    expected = hmac.new(
        b"k" * 32,
        f"onchain_address:{ADDRESS}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert token == expected


def test_risk_query_rejects_results_over_graph_limit(monkeypatch, tmp_path):
    database = tmp_path / "risk-limit.sqlite3"
    cases = IncidentCaseStore(database)
    case = cases.create_case(
        title="Risk result cap",
        summary="Do not silently truncate provider assessments.",
        created_by="analyst",
    )
    store = OnChainRiskStore(database)
    report, digest = OnChainRiskImportFile.parse_content(report_content())
    store.import_report(case["case_id"], report, report_sha256=digest)
    monkeypatch.setattr("sanctum_suite.core.onchain_risk._MAX_ASSESSMENTS_PER_GRAPH", 0)

    with pytest.raises(OnChainRiskResultTooLarge, match="no partial result"):
        store.list_for_addresses(case["case_id"], ChainName.ETHEREUM, [ADDRESS])


def test_import_parser_rejects_duplicate_addresses_and_oversized_or_invalid_content(
    tmp_path,
):
    duplicate = json.dumps(
        {
            "schema_version": "1.0",
            "records": [ASSESSMENT, {**ASSESSMENT, "category": "different"}],
        }
    )
    with pytest.raises(ValueError, match="duplicate provider/address"):
        report, digest = OnChainRiskImportFile.parse_content(duplicate)
        database = tmp_path / "duplicate-report.sqlite3"
        cases = IncidentCaseStore(database)
        case = cases.create_case(
            title="Duplicate report",
            summary="Reject duplicate address labels.",
            created_by="analyst",
        )
        OnChainRiskStore(database).import_report(
            case["case_id"], report, report_sha256=digest
        )

    with pytest.raises(ValueError, match="1 MB"):
        OnChainRiskImportFile.parse_content("x" * 1_000_001)
    with pytest.raises(ValueError, match="invalid JSON"):
        OnChainRiskImportFile.parse_content("{")


def test_case_api_imports_normalized_report_and_graph_exposes_unverified_assessment(
    monkeypatch, tmp_path
):
    api_key = "onchain-risk-test-key-" + "x" * 32
    database = tmp_path / "cases.sqlite3"
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(server, "incident_case_store", IncidentCaseStore(database))
    monkeypatch.setattr(server, "onchain_risk_store", None)
    case = server.get_incident_case_store().create_case(
        title="Provider risk",
        summary="Review a provider-reported address assessment.",
        created_by="analyst",
    )
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}

    unauthenticated = client.post(
        f"/api/v1/cases/{case['case_id']}/onchain-risk/import",
        json={"content": report_content()},
    )
    assert unauthenticated.status_code == 401

    imported = client.post(
        f"/api/v1/cases/{case['case_id']}/onchain-risk/import",
        headers=headers,
        json={"content": report_content()},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["inserted_count"] == 1
    assert imported.json()["raw_report_persisted"] is False
    assert imported.json()["status"] == "IMPORTED_PROVIDER_REPORTS_UNVERIFIED"
    assert ADDRESS not in imported.text

    class FakeClient:
        async def get_block(self, height):
            assert height == 42
            return OnChainBlock(
                chain=ChainName.ETHEREUM,
                block_hash="0x" + "1" * 64,
                height=height,
                parent_hash="0x" + "2" * 64,
                timestamp="2026-10-19T12:00:00Z",
                fetched_at="2026-10-19T12:01:00Z",
                source="ethereum_json_rpc",
                transactions=(
                    OnChainTransaction(
                        transaction_hash="0x" + "3" * 64,
                        inputs=(TransactionInput(address="0x" + "b" * 40, unit="wei"),),
                        outputs=(
                            TransactionOutput(
                                index=0,
                                address=ADDRESS,
                                value_atomic=100,
                                unit="wei",
                            ),
                        ),
                    ),
                ),
            )

    monkeypatch.setattr(server, "get_onchain_rpc_client", lambda _chain: FakeClient())
    graph = client.get(
        f"/api/v1/cases/{case['case_id']}/onchain-graph?chain=ethereum&height=42",
        headers=headers,
    )
    assert graph.status_code == 200, graph.text
    result = graph.json()
    assessment = next(
        edge for edge in result["edges"] if edge["relation"] == "HAS_REPORTED_ASSESSMENT"
    )
    assert assessment["provider"] == "chainalysis"
    assert assessment["provider_rating"] == "high"
    assert assessment["confidence"] == "provider_reported_unverified"
    assert assessment["report_sha256"] == imported.json()["report_sha256"]
    assert "not independently authenticated" in " ".join(result["limitations"])


def test_import_endpoint_sanitizes_validation_errors(monkeypatch, tmp_path):
    api_key = "onchain-risk-invalid-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server, "incident_case_store", IncidentCaseStore(tmp_path / "cases.sqlite3")
    )
    case = server.get_incident_case_store().create_case(
        title="Invalid provider report",
        summary="Malformed input should not be echoed.",
        created_by="analyst",
    )
    client = TestClient(server.app)
    response = client.post(
        f"/api/v1/cases/{case['case_id']}/onchain-risk/import",
        headers={"X-API-Key": api_key},
        json={"content": json.dumps({"schema_version": "invalid", "records": []})},
    )

    assert response.status_code == 422
    assert ADDRESS not in response.text
