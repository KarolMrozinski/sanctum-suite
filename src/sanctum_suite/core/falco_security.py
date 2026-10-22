from __future__ import annotations

from typing import Any


class FalcoSecurityModule:
    """Represents Falco rules and runtime detection controls as a planning model only."""

    @staticmethod
    def _profile_rules(workload_name: str, namespace_name: str) -> list[dict[str, Any]]:
        workload = (workload_name or "sanctum-suite").strip().lower()
        if "api" in workload or "gateway" in workload or "web" in workload:
            return [
                {
                    "rule_id": "unexpected_outbound_connection",
                    "description": "Detect unexpected egress or tunnelling from the web/API pod.",
                    "severity": "HIGH",
                    "scope": f"{namespace_name}/web-tier",
                    "trigger": "Outbound TCP or DNS from non-approved destinations",
                    "response": "Isolate pod, block egress, and start incident triage.",
                },
                {
                    "rule_id": "sensitive_file_write",
                    "description": "Alert on writes to /etc/passwd, SSH keys, secrets, or certificate material.",
                    "severity": "CRITICAL",
                    "scope": f"{namespace_name}/web-tier",
                    "trigger": "Write to sensitive file paths or secret stores",
                    "response": "Pause workload, preserve forensic image, and rotate impacted secrets.",
                },
                {
                    "rule_id": "container_runtime_exec",
                    "description": "Flag shell execution, package manager use, or binary invocation from unapproved paths.",
                    "severity": "HIGH",
                    "scope": f"{namespace_name}/web-tier",
                    "trigger": "Execution of bash, sh, curl, apt, wget, python in runtime context",
                    "response": "Quarantine workload and review the process lineage.",
                },
            ]

        if "db" in workload or "database" in workload or "postgres" in workload:
            return [
                {
                    "rule_id": "unexpected_db_port_bind",
                    "description": "Detect database processes binding to unapproved interfaces or ports.",
                    "severity": "CRITICAL",
                    "scope": f"{namespace_name}/database-tier",
                    "trigger": "MySQL/Postgres process binds to wildcard or unexpected interface",
                    "response": "Disable access path, enforce firewall rules, and review privilege scope.",
                },
                {
                    "rule_id": "db_credential_access",
                    "description": "Alert on reads of credential stores, config files, or TLS key paths.",
                    "severity": "CRITICAL",
                    "scope": f"{namespace_name}/database-tier",
                    "trigger": "Read access to .env, secrets, private keys, or backup archives",
                    "response": "Rotate secrets and block database access immediately.",
                },
                {
                    "rule_id": "crypto_miner_process",
                    "description": "Identify suspicious CPU-heavy child processes or malicious shell payloads.",
                    "severity": "HIGH",
                    "scope": f"{namespace_name}/database-tier",
                    "trigger": "Unexpected mining or cryptographic workload execution",
                    "response": "Fence the pod and inspect the full runtime ancestry.",
                },
            ]

        if "llm" in workload or "model" in workload or "inference" in workload:
            return [
                {
                    "rule_id": "model_artifact_exfiltration",
                    "description": "Detect copying or exfiltration of model artifacts, tokens, or API keys.",
                    "severity": "CRITICAL",
                    "scope": f"{namespace_name}/llm-tier",
                    "trigger": "Read, archiving, or network transfer of model files or credentials",
                    "response": "Quarantine pod, revoke tokens, and review model-serving access logs.",
                },
                {
                    "rule_id": "unexpected_package_manager_use",
                    "description": "Alert on pip, apt, npm, or pip install inside the inference runtime.",
                    "severity": "HIGH",
                    "scope": f"{namespace_name}/llm-tier",
                    "trigger": "Package manager invocation from a running inference workload",
                    "response": "Stop the pod and validate the image provenance and dependency graph.",
                },
                {
                    "rule_id": "suspicious_network_proxying",
                    "description": "Flag outbound proxying or tunnelling used to stage external exfiltration.",
                    "severity": "HIGH",
                    "scope": f"{namespace_name}/llm-tier",
                    "trigger": "Direct connections to proxies, Tor, or suspicious external hosts",
                    "response": "Block egress, suspend the workload, and review for data loss.",
                },
            ]

        return [
            {
                "rule_id": "unexpected_outbound_connection",
                "description": "Detect unexpected egress or tunnelling from the workload.",
                "severity": "HIGH",
                "scope": f"{namespace_name}/generic-tier",
                "trigger": "Outbound TCP or DNS to unapproved destinations",
                "response": "Isolate pod and start incident triage.",
            },
            {
                "rule_id": "sensitive_file_write",
                "description": "Alert on writes to /etc/passwd, SSH keys, or secret material.",
                "severity": "CRITICAL",
                "scope": f"{namespace_name}/generic-tier",
                "trigger": "Write to sensitive file paths or secret stores",
                "response": "Pause workload and rotate impacted credentials.",
            },
            {
                "rule_id": "container_runtime_exec",
                "description": "Flag shell execution, package manager use, or binary invocation from unapproved paths.",
                "severity": "HIGH",
                "scope": f"{namespace_name}/generic-tier",
                "trigger": "Execution of bash, sh, curl, apt, python in runtime context",
                "response": "Quarantine the workload and review process lineage.",
            },
        ]

    def assess_runtime_security(
        self,
        workload: str = "sanctum-suite",
        namespace: str = "prod",
    ) -> dict[str, Any]:
        workload_name = (workload or "unnamed-workload").strip() or "unnamed-workload"
        namespace_name = (namespace or "default").strip() or "default"

        rules = self._profile_rules(workload_name, namespace_name)

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
                "Enforce namespace and workload-specific deny rules for non-approved processes and network paths.",
            ],
            "response_actions": [
                "Create isolating quarantine and incident-response actions for container compromise.",
                "Capture full runtime context and process lineage for forensic review.",
                "Tune the ruleset to reduce false positives while preserving critical alerts.",
                "Rotate secrets, trigger playbooks, and verify image provenance after high-severity detection.",
            ],
            "verification_gate": {
                "mode": "PLAN_ONLY",
                "required": True,
                "checks": [
                    "Validate the Falco ruleset against the workload profile and namespace policy.",
                    "Confirm that critical alerts are mapped to SIEM or SOAR actions.",
                    "Document any exceptions with an expiry and owner before deployment.",
                ],
            },
            "yaml_example": {
                "generator": "FalcoRuleTemplateGenerator",
                "output_format": "yaml",
                "source_file": "sanctum_suite.core.falco_rules_yaml",
            },
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
