import pytest
from sanctum_suite.core.signer import SecurityReportSigner
from sanctum_suite.core.mitre import MitreMapperEngine
from sanctum_suite.core.remediation import RemediationPlaybookEngine


def test_mitre_mapping():
    mitre = MitreMapperEngine()
    shadow_vulns = [{"endpoint": "api.test.com", "issue": "PROMPT_INJECTION_RISK"}]
    open_ports = [{"port": 11434, "service": "Ollama LLM API"}]

    tactics = mitre.map_findings(shadow_vulns, open_ports)
    assert len(tactics) == 2
    assert tactics[0]["technique_id"] == "AML.T0051"


def test_remediation_playbook():
    engine = RemediationPlaybookEngine()
    open_ports = [{"port": 11434, "service": "Ollama LLM API"}]
    playbook = engine.generate_playbook(open_ports, [])
    assert "iptables" in playbook["firewall_hardening_script"]


def test_report_signer(tmp_path):
    dummy_file = tmp_path / "test_report.pdf"
    dummy_file.write_text("Dummy PDF Content")

    signer = SecurityReportSigner(key_dir=str(tmp_path / ".keys"))
    signature = signer.sign_file(str(dummy_file))
    assert len(signature) > 0
    assert (tmp_path / "test_report.pdf.sig").exists()