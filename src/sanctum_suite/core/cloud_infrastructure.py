from __future__ import annotations

from typing import Any


class AWSInfrastructureManager:
    """Plans AWS security controls without making live API calls."""

    def review_security_baseline(
        self,
        account_id: str,
        region: str,
        workload: str,
    ) -> dict[str, Any]:
        account = (account_id or "unknown-account").strip()
        region_name = (region or "unknown-region").strip()
        workload_name = (workload or "unidentified-workload").strip()

        controls = [
            "IAM least-privilege roles and MFA on privileged access",
            "AWS WAF / ALB / CloudFront protections for public exposure",
            "KMS encryption at rest and in transit for data plane workloads",
            "GuardDuty, Security Hub, and VPC Flow Logs enabled for monitoring",
            "Immutable AMIs, patch baselines, and EBS encryption",
        ]

        return {
            "platform": "AWS",
            "status": "PLAN_ONLY",
            "account_id": account,
            "region": region_name,
            "workload": workload_name,
            "recommended_controls": controls,
            "networking": {
                "vpc_segmentation": "required",
                "private_subnets": "preferred",
                "nat_gateway": "review",
                "flow_logs": "enabled",
            },
            "defense_in_depth": [
                "identity protection",
                "network segmentation",
                "workload hardening",
                "data encryption",
                "continuous monitoring",
            ],
            "recommendations": [
                "Apply least-privilege IAM, MFA, and AWS Organizations guardrails.",
                "Place internet exposure behind WAF, ALB, and private-only backend routing.",
                "Enable centralized logging, vulnerability management, and asset inventory.",
            ],
        }


class AzureInfrastructureManager:
    """Plans Microsoft Azure security controls without making live API calls."""

    def review_security_baseline(
        self,
        subscription_id: str,
        region: str,
        workload: str,
    ) -> dict[str, Any]:
        subscription = (subscription_id or "unknown-subscription").strip()
        region_name = (region or "unknown-region").strip()
        workload_name = (workload or "unidentified-workload").strip()

        controls = [
            "Azure AD / Entra ID MFA and conditional access",
            "Azure Firewall / WAF / Front Door edge protections",
            "Managed disk encryption and Key Vault-backed secrets",
            "Microsoft Defender for Cloud and activity logging",
            "NSG / ASG / private endpoints for service isolation",
        ]

        return {
            "platform": "Azure",
            "status": "PLAN_ONLY",
            "subscription_id": subscription,
            "region": region_name,
            "workload": workload_name,
            "recommended_controls": controls,
            "networking": {
                "subnet_isolation": "required",
                "private_endpoints": "preferred",
                "diagnostic_logs": "enabled",
                "firewall_policy": "review",
            },
            "defense_in_depth": [
                "identity and access control",
                "network and perimeter hardening",
                "application isolation",
                "platform monitoring",
                "incident readiness",
            ],
            "recommendations": [
                "Configure RBAC, conditional access, and just-in-time admin access.",
                "Use Azure Firewall, WAF, private endpoints, and region-level segmentation.",
                "Centralize log retention, Defender for Cloud posture management, and policy enforcement.",
            ],
        }


class CloudInfrastructureManager:
    """High-level cloud review used by the orchestrator for AWS/Azure planning."""

    def __init__(self) -> None:
        self.aws = AWSInfrastructureManager()
        self.azure = AzureInfrastructureManager()

    def assess_cloud_infrastructure(
        self,
        platform: str,
        *,
        account_id: str | None = None,
        subscription_id: str | None = None,
        region: str = "eu-central-1",
        workload: str = "sanctum-suite",
    ) -> dict[str, Any]:
        platform_name = (platform or "").strip().lower()

        if platform_name == "aws":
            return self.aws.review_security_baseline(
                account_id or "unknown-account",
                region,
                workload,
            )
        if platform_name == "azure":
            return self.azure.review_security_baseline(
                subscription_id or "unknown-subscription",
                region,
                workload,
            )
        raise ValueError("Unsupported cloud platform; choose 'aws' or 'azure'.")
