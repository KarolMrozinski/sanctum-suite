import asyncio

import pytest

from sanctum_suite.core.port_scanner import AsyncPortScanner
from sanctum_suite.core.scanner import AsyncEndpointScanner
from sanctum_suite.core.target_authorization import (
    TargetAuthorizationError,
    normalize_target_host,
    require_authorized_target,
)


def test_target_authorization_requires_exact_operator_allowlist():
    assert normalize_target_host("EXAMPLE.com.") == "example.com"
    assert require_authorized_target(
        "example.com",
        "approval-ticket-123",
        authorized_targets="example.com,127.0.0.1",
    ) == "example.com"
    with pytest.raises(TargetAuthorizationError, match="exact match"):
        require_authorized_target(
            "sub.example.com",
            "approval-ticket-123",
            authorized_targets="example.com",
        )
    with pytest.raises(TargetAuthorizationError, match="written authorization"):
        require_authorized_target("example.com", "", authorized_targets="example.com")


def test_scanner_rejects_non_https_and_non_allowlisted_targets(monkeypatch):
    monkeypatch.setenv("SANCTUM_AUTHORIZED_TARGETS", "example.com")
    scanner = AsyncEndpointScanner()
    assert scanner._target_url("https://example.com", "ticket-1") == "https://example.com"
    with pytest.raises(ValueError, match="HTTPS"):
        scanner._target_url("http://example.com", "ticket-1")
    with pytest.raises(TargetAuthorizationError, match="exact match"):
        scanner._target_url("other.example.com", "ticket-1")


def test_port_scanner_requires_authorization_before_connecting(monkeypatch):
    monkeypatch.delenv("SANCTUM_AUTHORIZED_TARGETS", raising=False)
    with pytest.raises(TargetAuthorizationError, match="exact match"):
        AsyncPortScanner().run_sync_port_scan(
            "127.0.0.1",
            authorization_reference="ticket-1",
            ports=[1],
        )


@pytest.mark.asyncio
async def test_port_scanner_surfaces_unexpected_connection_errors(monkeypatch):
    monkeypatch.setenv("SANCTUM_AUTHORIZED_TARGETS", "example.com")

    async def fail_connection(*args, **kwargs):
        raise OSError("network is unreachable")

    monkeypatch.setattr(asyncio, "open_connection", fail_connection)
    with pytest.raises(OSError, match="network is unreachable"):
        await AsyncPortScanner().scan_host_ports(
            "example.com",
            authorization_reference="ticket-1",
            ports=[443],
        )


def test_port_scanner_rejects_invalid_timeouts():
    with pytest.raises(ValueError, match="timeout"):
        AsyncPortScanner(timeout=0)
    with pytest.raises(ValueError, match="timeout"):
        AsyncPortScanner(timeout=31)
