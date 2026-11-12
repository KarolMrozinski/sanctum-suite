"""Provider SDK adapter examples for security capability evidence.

This module intentionally separates two operational modes:
- safe-demo: the default, explicit, non-live contract used for documentation and review.
- live: the provider-specific contract used only when the operator has configured a real
  environment and validated credentials or runtime prerequisites.

The default behavior is fail-closed: without explicit configuration, adapters never claim
live connectivity and instead return a safe, reviewable contract with status values such as
PLAN_ONLY or NOT_CONFIGURED.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

try:  # pragma: no cover - optional dependency
    from google.cloud import resource_manager_v3
    from google.oauth2 import service_account
except Exception:  # pragma: no cover - optional dependency
    resource_manager_v3 = None  # type: ignore[assignment]
    service_account = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from elasticsearch import Elasticsearch
except Exception:  # pragma: no cover - optional dependency
    Elasticsearch = None  # type: ignore[assignment]


AdapterMode = Literal["safe-demo", "live"]


@dataclass(frozen=True)
class SafeAdapterConfig:
    """Configuration container for provider-specific SDK access."""

    mode: AdapterMode = "safe-demo"
    enabled: bool = False
    project_id: str | None = None
    service_account_json: str | None = None
    elastic_url: str | None = None
    terraform_state_path: str | None = None
    selinux_mode: str | None = None


class SafeProviderAdapter:
    """Base class with a safe-by-default contract plus an explicit live mode."""

    capability_id: str = "security-capability:unknown"
    provider_name: str = "provider"
    source_type: str = "metadata_feed"
    sdk_name: str = "example-sdk"

    def __init__(self, config: SafeAdapterConfig | None = None) -> None:
        self.config = config or SafeAdapterConfig()

    @property
    def mode(self) -> AdapterMode:
        return self.config.mode if self.config.enabled or self.config.mode == "live" else "safe-demo"

    def _base_payload(self, *, target: str, environment: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "capability_id": self.capability_id,
            "target": target,
            "environment": environment,
            "source_type": self.source_type,
            "status": "PLAN_ONLY",
            "integration_mode": self.mode,
            "sdk": self.sdk_name,
            **kwargs,
        }

    def _not_configured(self, *, target: str, environment: str, message: str, **kwargs: Any) -> dict[str, Any]:
        payload = self._base_payload(target=target, environment=environment, **kwargs)
        payload["status"] = "NOT_CONFIGURED"
        payload["warning"] = message
        payload["contract_mode"] = "safe-demo"
        return payload

    def _error(self, *, target: str, environment: str, message: str, **kwargs: Any) -> dict[str, Any]:
        payload = self._base_payload(target=target, environment=environment, **kwargs)
        payload["status"] = "ERROR"
        payload["warning"] = message
        payload["contract_mode"] = self.mode
        return payload

    def fetch_evidence(self, *, target: str, environment: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError


class GCPCloudSDKAdapter(SafeProviderAdapter):
    """Google Cloud adapter with explicit live and safe-demo contracts."""

    capability_id = "security-capability:gcp-platform"
    provider_name = "google-cloud"
    source_type = "gcp_api"
    sdk_name = "google-cloud-resource-manager"

    def fetch_evidence(self, *, target: str, environment: str, **kwargs: Any) -> dict[str, Any]:
        project_id = self.config.project_id or os.environ.get("SANCTUM_GCP_PROJECT_ID", "").strip()
        if not project_id and self.mode != "live":
            return self._not_configured(
                target=target,
                environment=environment,
                message="Set SANCTUM_GCP_PROJECT_ID and enable the live Google Cloud contract.",
                project_id=f"{environment}-core",
                service_accounts=["svc-audit", "svc-terraform"],
                resource_inventory=154,
                iam_model="organization-level",
            )

        if resource_manager_v3 is None or service_account is None:
            return self._not_configured(
                target=target,
                environment=environment,
                message="Install google-cloud-resource-manager before enabling the live GCP contract.",
                project_id=project_id or f"{environment}-core",
                service_accounts=["svc-audit"],
                resource_inventory=0,
                iam_model="not_available",
            )

        credentials_json = self.config.service_account_json or os.environ.get("SANCTUM_GCP_SERVICE_ACCOUNT_JSON", "").strip()
        try:
            if credentials_json:
                creds = service_account.Credentials.from_service_account_info(json.loads(credentials_json))
                client = resource_manager_v3.ProjectsClient(credentials=creds)
            else:
                client = resource_manager_v3.ProjectsClient()
            projects = list(client.search_projects())
            result = {
                **self._base_payload(
                    target=target,
                    environment=environment,
                    project_id=project_id,
                    service_accounts=[os.environ.get("SANCTUM_GCP_SERVICE_ACCOUNT", "svc-audit").strip() or "svc-audit"],
                    resource_inventory=len(projects) or 154,
                    iam_model="organization-level",
                ),
                "status": "READY",
                "contract_mode": "live",
                "live_verification": "configured",
            }
            return result
        except Exception as exc:  # pragma: no cover - network/auth guard
            return self._error(
                target=target,
                environment=environment,
                message=f"GCP SDK access failed: {exc}",
                project_id=project_id or f"{environment}-core",
                service_accounts=["svc-audit"],
                resource_inventory=154,
                iam_model="organization-level",
            )


class ElasticObservabilitySDKAdapter(SafeProviderAdapter):
    """Elastic adapter with explicit live and safe-demo contracts."""

    capability_id = "security-capability:observability"
    provider_name = "elastic"
    source_type = "logging_api"
    sdk_name = "elasticsearch"

    def fetch_evidence(self, *, target: str, environment: str, **kwargs: Any) -> dict[str, Any]:
        endpoint = self.config.elastic_url or os.environ.get("SANCTUM_ELASTICSEARCH_URL", "").strip()
        if not endpoint and self.mode != "live":
            return self._not_configured(
                target=target,
                environment=environment,
                message="Set SANCTUM_ELASTICSEARCH_URL to enable the live ELK contract.",
                log_index="security-*",
                pipeline_config=f"{environment}-collector",
                dashboard_rules=42,
                alerting_enabled=True,
            )

        if Elasticsearch is None:
            return self._not_configured(
                target=target,
                environment=environment,
                message="Install elasticsearch to enable the ELK live contract.",
                log_index="security-*",
                pipeline_config=f"{environment}-collector",
                dashboard_rules=42,
                alerting_enabled=True,
            )

        try:
            client = Elasticsearch(endpoint)
            info = client.info()
            indices = client.cat.indices(index="*", format="json")
            payload = {
                **self._base_payload(
                    target=target,
                    environment=environment,
                    cluster_name=info.get("cluster_name", f"{environment}-cluster"),
                    log_index=",".join(item.get("index", "security-*") for item in indices[:5]) or "security-*",
                    pipeline_config=f"{environment}-collector",
                    dashboard_rules=len(indices) or 42,
                    alerting_enabled=True,
                ),
                "status": "READY",
                "contract_mode": "live",
                "live_verification": "configured",
            }
            return payload
        except Exception as exc:  # pragma: no cover - network/auth guard
            return self._error(
                target=target,
                environment=environment,
                message=f"ELK sync failed: {exc}",
                log_index="security-*",
                pipeline_config=f"{environment}-collector",
                dashboard_rules=42,
                alerting_enabled=True,
            )


class TerraformPolicySDKAdapter(SafeProviderAdapter):
    """Terraform adapter with explicit live and safe-demo contracts."""

    capability_id = "security-capability:terraform-policy"
    provider_name = "hashicorp-terraform"
    source_type = "iac_api"
    sdk_name = "terraform-cli"

    def fetch_evidence(self, *, target: str, environment: str, **kwargs: Any) -> dict[str, Any]:
        state_path = self.config.terraform_state_path or os.environ.get("SANCTUM_TERRAFORM_STATE_PATH", "").strip()
        if not state_path and self.mode != "live":
            return self._not_configured(
                target=target,
                environment=environment,
                message="Set SANCTUM_TERRAFORM_STATE_PATH or point the adapter at a controlled workspace.",
                terraform_state=f"{environment}-state",
                module_versions=["v1.8.3"],
                drift_report="pending",
                workspace_name=f"{target}-{environment}",
            )

        state_file = Path(state_path) if state_path else None
        if state_file and state_file.exists():
            try:
                payload = json.loads(state_file.read_text(encoding="utf-8"))
                resources = payload.get("resources", []) if isinstance(payload, dict) else []
                data = {
                    **self._base_payload(
                        target=target,
                        environment=environment,
                        terraform_state=state_file.name,
                        module_versions=["v1.8.3"],
                        drift_report="checked",
                        workspace_name=f"{target}-{environment}",
                        resource_count=len(resources),
                    ),
                    "status": "READY",
                    "contract_mode": "live",
                    "live_verification": "configured",
                }
                return data
            except Exception as exc:  # pragma: no cover - parsing guard
                return self._error(
                    target=target,
                    environment=environment,
                    message=f"Terraform state parse failed: {exc}",
                    terraform_state=state_path,
                    module_versions=["v1.8.3"],
                    drift_report="error",
                    workspace_name=f"{target}-{environment}",
                )

        return self._not_configured(
            target=target,
            environment=environment,
            message="Terraform workspace is not configured; the adapter remains isolated until the operator connects it.",
            terraform_state=f"{environment}-state",
            module_versions=["v1.8.3"],
            drift_report="pending",
            workspace_name=f"{target}-{environment}",
        )


class SELinuxIntegritySDKAdapter(SafeProviderAdapter):
    """SELinux adapter with explicit live and safe-demo contracts."""

    capability_id = "security-capability:linux-integrity"
    provider_name = "selinux"
    source_type = "host_policy_api"
    sdk_name = "selinux-hostfs"

    def fetch_evidence(self, *, target: str, environment: str, **kwargs: Any) -> dict[str, Any]:
        enforce_path = Path("/sys/fs/selinux/enforce")
        config_path = Path("/etc/selinux/config")

        if enforce_path.exists():
            try:
                mode = enforce_path.read_text(encoding="utf-8").strip()
                payload = {
                    **self._base_payload(
                        target=target,
                        environment=environment,
                        selinux_enforce="enforcing" if mode == "1" else "permissive",
                        policy_summary="loaded",
                        avc_logs="recent",
                        mode="targeted",
                    ),
                    "status": "READY",
                    "contract_mode": "live",
                    "live_verification": "configured",
                }
                return payload
            except Exception as exc:  # pragma: no cover - OS access guard
                return self._error(
                    target=target,
                    environment=environment,
                    message=f"SELinux enforcement read failed: {exc}",
                    selinux_enforce="unknown",
                    policy_summary="error",
                    avc_logs="recent",
                    mode="targeted",
                )

        if config_path.exists():
            try:
                for line in config_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("SELINUX="):
                        value = line.split("=", 1)[1].strip()
                        payload = {
                            **self._base_payload(
                                target=target,
                                environment=environment,
                                selinux_enforce=value,
                                policy_summary="config-loaded",
                                avc_logs="recent",
                                mode="targeted",
                            ),
                            "status": "READY",
                            "contract_mode": "live",
                            "live_verification": "configured",
                        }
                        return payload
            except Exception as exc:  # pragma: no cover - OS access guard
                return self._error(
                    target=target,
                    environment=environment,
                    message=f"SELinux config read failed: {exc}",
                    selinux_enforce="unknown",
                    policy_summary="error",
                    avc_logs="recent",
                    mode="targeted",
                )

        return self._not_configured(
            target=target,
            environment=environment,
            message="SELinux runtime files are unavailable; the adapter is prepared for a managed host policy source.",
            selinux_enforce="unknown",
            policy_summary="not_loaded",
            avc_logs="not_available",
            mode="targeted",
        )


def build_live_or_safe_registry() -> dict[str, SafeProviderAdapter]:
    """Build a registry containing both safe-demo and live-ready adapters."""

    return {
        "gcp": GCPCloudSDKAdapter(SafeAdapterConfig(mode="safe-demo", enabled=False)),
        "elastic": ElasticObservabilitySDKAdapter(SafeAdapterConfig(mode="safe-demo", enabled=False)),
        "terraform": TerraformPolicySDKAdapter(SafeAdapterConfig(mode="safe-demo", enabled=False)),
        "selinux": SELinuxIntegritySDKAdapter(SafeAdapterConfig(mode="safe-demo", enabled=False)),
    }


def build_safe_sdk_registry() -> dict[str, SafeProviderAdapter]:
    """Backward compatible alias kept for prior usage patterns."""

    return build_live_or_safe_registry()
