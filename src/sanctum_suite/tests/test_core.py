import pytest
from sanctum_suite.core.port_scanner import AsyncPortScanner
from sanctum_suite.core.correlator import ThreatCorrelationEngine


def test_threat_correlation():
    correlator = ThreatCorrelationEngine()
    open_ports = [{"port": 11434, "service": "Ollama LLM API"}]
    shadow_vulns = [{"endpoint": "api.test.com", "issue": "PROMPT_INJECTION_RISK"}]

    res = correlator.correlate_findings(open_ports, shadow_vulns)
    assert res["risk_multiplier"] == 1.5
    assert res["chain_count"] == 1


@pytest.mark.asyncio
async def test_async_port_scanner():
    scanner = AsyncPortScanner(timeout=0.1)
    results = await scanner.scan_host_ports("127.0.0.1", ports=[22])
    assert isinstance(results, list)