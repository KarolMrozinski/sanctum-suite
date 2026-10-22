from __future__ import annotations

from typing import Any


class FalcoSecurityModule:
    """Represents Falco rules and runtime detection controls as a planning model only."""

    def assess_runtime_security(
        self,
        workload: str = "sanctum-suite",
        namespace: str = "prod",
    ) -> dict[str, Any]:
        workload_name = (workload or "unnamed-workload").strip() or "unnamed-workload"
        namespace_name = (namespace or "default").strip() or "default"

        rules = [
            {
                "rule_id": "unexpected_outbound_connection",
                "description": "Detect unexpected egress or tunnelling from the workload.",
                "severity": "HIGH",
            },
            {
                "rule_id": "sensitive_file_write",
                "description": "Alert on writes to /etc/passwd, SSH keys, or secret material.",
                "severity": "CRITICAL",
            },
            {
                "rule_id": "container_runtime_exec",
                "description": "Flag executable invocation from unapproved containers or shells.",
                "severity": "HIGH",
            },
        ]

        return {
            "platform": "Falco",
            "status": "PLAN_ONLY",
            "workload": workload_name,
            "namespace": namespace_name,
            "runtime_rules": rules,
            "recommended_controls": [
                "Deploy Falco with kernel-level event collection and allowlist-driven rules.",
                "Centralize alerts into the SIEM and downstream SOAR workflow for triage.",
                "Pair Falco detections with eBPF-based enforcement and identity-aware policies.",
            ],
            "response_actions": [
                "Create isolating quarantine and incident-response actions for container compromise.",
                "Capture full runtime context and process lineage for forensic review.",
                "Tune the ruleset to reduce false positives while preserving critical alerts.",
            ],
        }

    assess_runtime_detection = assess_runtime_security


class FalcoModule(FalcoSecurityModule):
    """Backward-compatible alias for the Falco planning module."""

    def assess_runtime_detection(
        self,
        workload: str = "sanctum-suite",
        namespace: str = "prod",
    ) -> dict[str, Any]:
        return super().assess_runtime_security(workload=workload, namespace=namespace)
