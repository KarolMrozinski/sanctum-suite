from __future__ import annotations

from typing import Any


class DefenseInDepthPolicy:
    """Represents a layered protection model for public-facing web assets."""

    @staticmethod
    def build_policy(service_name: str, host: str) -> dict[str, Any]:
        service = (service_name or "web-service").strip() or "web-service"
        host_name = (host or "example.internal").strip() or "example.internal"

        return {
            "service": service,
            "host": host_name,
            "model": "defense_in_depth",
            "layers": [
                {
                    "name": "identity",
                    "controls": [
                        "MFA and conditional access",
                        "least-privilege IAM / RBAC",
                        "service-to-service authentication",
                    ],
                },
                {
                    "name": "network",
                    "controls": [
                        "WAF / reverse proxy fronting",
                        "deny-by-default network policy",
                        "private-only backend routing",
                    ],
                },
                {
                    "name": "application",
                    "controls": [
                        "input validation and output encoding",
                        "rate limiting and bot protections",
                        "secure session management",
                    ],
                },
                {
                    "name": "data",
                    "controls": [
                        "encryption at rest and in transit",
                        "secret vaulting and rotation",
                        "data minimization and retention",
                    ],
                },
                {
                    "name": "monitoring",
                    "controls": [
                        "detector coverage and alerting",
                        "audit trail retention",
                        "security validation and incident drills",
                    ],
                },
            ],
            "summary": (
                f"Defense-in-depth for {service} should enforce identity, network, application, "
                f"data, and monitoring controls before exposing {host_name} to untrusted traffic."
            ),
        }


class WASModule:
    """Web application security module, including WAF policy planning and defense-in-depth evaluation."""

    def assess_web_application(self, host: str, service_name: str = "web-service") -> dict[str, Any]:
        host_name = (host or "example.internal").strip()
        if not host_name:
            raise ValueError("Host must not be empty")

        waf_rules = [
            "Block malformed HTTP requests and oversized payloads",
            "Apply OWASP CRS rules and rate limits at the edge",
            "Restrict administrative endpoints to approved networks",
            "Normalize and inspect headers for SSRF and header injection patterns",
        ]

        defense = DefenseInDepthPolicy.build_policy(service_name, host_name)

        return {
            "status": "PLAN_ONLY",
            "host": host_name,
            "service": service_name,
            "waf_policy": {
                "mode": "PLAN_ONLY",
                "required": True,
                "rules": waf_rules,
                "policy_name": f"sanctum-waf-{service_name}",
            },
            "defense_in_depth": defense,
            "recommendations": [
                "Front the application with a WAF or equivalent reverse-proxy control.",
                "Enforce HTTPS, HSTS, and least-privilege access at every layer.",
                "Capture telemetry for anomaly detection, incidents, and policy tuning.",
            ],
        }
