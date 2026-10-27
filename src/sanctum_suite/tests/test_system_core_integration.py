#!/usr/bin/env python3

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from sanctum_suite.api.server import app
from sanctum_suite.core.system_orchestrator import SystemOrchestrator
from sanctum_suite.core.telemetry_buffer import TelemetryBuffer
from sanctum_suite.core.manifest_verifier import ManifestVerifier

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"

def test_ready_check_endpoint():
    response = client.get("/readyz")
    # Sprawdzamy, czy odpowiedź zwraca status HTTP (200 lub 503 w zależności od zmiennych środowiskowych)
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data

def test_telemetry_buffer_lifecycle(tmp_path: Path):
    buffer_dir = tmp_path / "telemetry"
    buffer = TelemetryBuffer(buffer_dir=buffer_dir, max_buffer_size=2)
    
    event = buffer.push_event("TEST_EVENT", {"detail": "unit_test"})
    assert "record_hash" in event
    assert buffer.get_buffered_count() == 1
    
    # Dodanie drugiego zdarzenia powinno wywołać automatyczny zrzut (flush) do pliku przy przekroczeniu max_buffer_size=2
    buffer.push_event("TEST_EVENT_2", {"detail": "unit_test_2"})
    assert buffer.get_buffered_count() == 0
    
    files = list(buffer_dir.glob("*.json"))
    assert len(files) == 1

def test_system_orchestrator_initialization(tmp_path: Path):
    orchestrator = SystemOrchestrator(root_dir=tmp_path)
    assert orchestrator.root_dir == tmp_path
    
    report = orchestrator.run_system_preflight()
    assert report["overall_status"] in ["healthy", "degraded"]
    assert "checks" in report