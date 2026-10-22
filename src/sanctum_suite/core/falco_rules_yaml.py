from __future__ import annotations

from typing import Any


class FalcoRuleTemplateGenerator:
    """Generates example Falco YAML rules for Kubernetes workload profiles in plan-only mode."""

    @staticmethod
    def generate_yaml(workload: str = "sanctum-suite", namespace: str = "prod") -> dict[str, Any]:
        workload_name = (workload or "sanctum-suite").strip() or "sanctum-suite"
        namespace_name = (namespace or "prod").strip() or "prod"
        workload_lower = workload_name.lower()

        rules: list[dict[str, Any]] = [
            {
                "rule": "Unexpected outbound connection detected",
                "condition": "evt.type=connect and evt.dir=< and fd.type=ipv4 and not proc.exe in (\"/usr/local/bin/nginx\", \"/usr/local/bin/python\")",
                "output": "Outbound connection from pod in namespace %container.namespace% to %fd.ip% by %proc.name% (user=%user.name%)",
                "priority": "WARNING",
                "tags": ["network", "egress", "potential-exfiltration"],
                "description": "Detect unexpected outbound network access from the workload.",
            },
            {
                "rule": "Sensitive file write detected",
                "condition": "openat(2) and evt.is_open_write=true and filename in (/etc/passwd, /etc/shadow, /etc/ssh/*, /var/run/secrets/*, /run/secrets/*, /root/.ssh/*)",
                "output": "Sensitive file write attempt from %proc.name% in %container.namespace%/%container.name%",
                "priority": "CRITICAL",
                "tags": ["filesystem", "credential-access", "secret-exposure"],
                "description": "Alert on writes to sensitive paths or secret material.",
            },
            {
                "rule": "Unexpected shell execution",
                "condition": "spawned_process and proc.name in (bash, sh, dash, zsh, python, python3, curl, wget, nc, ncat, powershell, pwsh)",
                "output": "Unexpected command execution: %proc.name% from %container.image.repository% in %container.namespace%",
                "priority": "HIGH",
                "tags": ["process", "execution", "post-exploit"],
                "description": "Signal suspicious execution of shell or package-management tools in runtime context.",
            },
        ]

        if "llm" in workload_lower or "model" in workload_lower or "inference" in workload_lower:
            rules.extend([
                {
                    "rule": "LLM model artifact exfiltration",
                    "condition": "openat(2) and (fd.name contains \".bin\" or fd.name contains \".gguf\" or fd.name contains \".onnx\" or fd.name contains \"model\") and evt.is_open_read=true and not fd.name contains \"/tmp/\"",
                    "output": "Possible model artifact access or exfiltration in %container.namespace%/%container.name% using %proc.name%",
                    "priority": "CRITICAL",
                    "tags": ["llm", "model", "exfiltration"],
                    "description": "Alert when model artifacts are read or transferred from non-approved paths.",
                },
                {
                    "rule": "Unexpected package manager execution in inference runtime",
                    "condition": "spawned_process and proc.name in (pip, pip3, apt, apt-get, yum, dnf, npm, yarn) and container.namespace=\"prod\"",
                    "output": "Package manager was executed from inference workload %container.name% in %container.namespace%",
                    "priority": "HIGH",
                    "tags": ["llm", "package-manager", "tampering"],
                    "description": "Detect package manager use in inference workloads to identify tampering or malicious changes.",
                },
            ])

        if "db" in workload_lower or "postgres" in workload_lower or "mysql" in workload_lower:
            rules.extend([
                {
                    "rule": "Database credential access attempt",
                    "condition": "openat(2) and (fd.name contains \".env\" or fd.name contains \"/var/lib/postgresql/\" or fd.name contains \"/etc/mysql/\") and evt.is_open_read=true",
                    "output": "Possible credential or DB config access in %container.namespace%/%container.name% by %proc.name%",
                    "priority": "CRITICAL",
                    "tags": ["database", "credentials", "credential-access"],
                    "description": "Alert on access to DB credentials or config stores.",
                },
            ])

        return {
            "status": "PLAN_ONLY",
            "namespace": namespace_name,
            "workload": workload_name,
            "rules": rules,
            "notes": [
                "These rules are examples for a controlled release workflow and should be reviewed by a security owner before deployment.",
                "This module intentionally does not execute or enforce Falco rules in runtime; it only documents the expected rule set and verification gate.",
            ],
        }
