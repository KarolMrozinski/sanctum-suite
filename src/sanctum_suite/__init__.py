"""SANCTUM-SUITE package exports."""

from src_ada import list_modules as list_ada_modules
from src_apl import list_modules as list_apl_modules
from src_hals import list_modules as list_hals_modules
from src_rust import list_modules as list_rust_modules

from sanctum_suite.capability.registry import discover_language_module_capabilities
from sanctum_suite.core.chaos_resilience import ChaosResilienceEngine
from sanctum_suite.core.technology_stack_catalog import PlatformTechnologyCatalog
from sanctum_suite.modules import (
    AuditEvidenceBundle,
    CEFEventExporter,
    CorporateTelemetryExporter,
    DebeziumKafkaConnector,
    ExternalKMSAdapter,
    ExternalKMSFacade,
    HashiCorpVaultPKI,
    KafkaDebeziumConnector,
    KeycloakIdentityProvider,
    KeycloakOIDCProvider,
    KubernetesAdmissionWebhook,
    KubernetesWebhookHandler,
    VaultPKISecretsEngine,
)

ADA_MODULES = list_ada_modules()
APL_MODULES = list_apl_modules()
HALS_MODULES = list_hals_modules()
RUST_MODULES = list_rust_modules()


def list_integrated_language_modules() -> dict[str, list[str]]:
    """Expose the companion language modules that live next to the Python package."""
    return {
        "ada": ADA_MODULES,
        "apl": APL_MODULES,
        "hals": HALS_MODULES,
        "rust": RUST_MODULES,
    }


def describe_integrated_language_modules() -> dict[str, list[dict[str, str]]]:
    """Return the full module catalog, including capability ids and source paths."""
    records = discover_language_module_capabilities()
    by_language: dict[str, list[dict[str, str]]] = {}
    for record in records:
        by_language.setdefault(record.language, []).append(
            {
                "module_name": record.module_name,
                "language": record.language,
                "capability_id": record.capability_id,
                "source_dir": record.source_dir,
                "source_path": record.source_path,
                "status": record.status,
            }
        )
    return {language: sorted(modules, key=lambda item: item["module_name"].lower()) for language, modules in sorted(by_language.items())}


__all__ = [
    "ChaosResilienceEngine",
    "PlatformTechnologyCatalog",
    "CorporateTelemetryExporter",
    "CEFEventExporter",
    "AuditEvidenceBundle",
    "ExternalKMSAdapter",
    "ExternalKMSFacade",
    "KubernetesWebhookHandler",
    "KubernetesAdmissionWebhook",
    "VaultPKISecretsEngine",
    "HashiCorpVaultPKI",
    "KeycloakOIDCProvider",
    "KeycloakIdentityProvider",
    "KafkaDebeziumConnector",
    "DebeziumKafkaConnector",
    "ADA_MODULES",
    "APL_MODULES",
    "HALS_MODULES",
    "RUST_MODULES",
    "list_integrated_language_modules",
    "describe_integrated_language_modules",
]
