"""SANCTUM-SUITE package exports."""

from src_ada import list_modules as list_ada_modules
from src_apl import list_modules as list_apl_modules
from src_hals import list_modules as list_hals_modules
from src_rust import list_modules as list_rust_modules

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
]
