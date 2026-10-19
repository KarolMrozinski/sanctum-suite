import asyncio
import os
import sys

from fastapi import HTTPException

from sanctum_suite.core.audit_pseudonymizer import AuditPseudonymizer
from sanctum_suite.core.billing import CommercialLicenseManager
from sanctum_suite.core.immutable_audit import (
    ImmutableAuditError,
    MinioImmutableAuditStore,
)
from sanctum_suite.core.kms_vault import VaultTransitError, ZeroTrustKMSVault
from sanctum_suite.core.opa_policy import (
    OPAPolicyClient,
    OPAPolicyConfigurationError,
    OPAPolicyUnavailable,
)
from sanctum_suite.core.signer import SecurityReportSigner
from sanctum_suite.core.target_authorization import require_authorized_target
from sanctum_suite.core.tpm_attestation import (
    KeylimeVerifierClient,
    TPMAttestationConfigurationError,
    TPMAttestationUnavailable,
)
from sanctum_suite.core.tee_attestation import (
    TEEAttestationConfigurationError,
    TEEAttestationUnavailable,
    TrusteeClaimsClient,
)


def run_production_check() -> int:
    print("[SANCTUM-SUITE] Checking required audit configuration; no target will be scanned.")
    try:
        authorized_targets = os.environ.get("SANCTUM_AUTHORIZED_TARGETS", "")
        targets = [target.strip() for target in authorized_targets.split(",") if target.strip()]
        if not targets:
            raise ValueError("SANCTUM_AUTHORIZED_TARGETS is empty")
        require_authorized_target(targets[0], "production-preflight")
        entitlement = CommercialLicenseManager().validate_license_key(
            os.environ.get("SANCTUM_LICENSE_KEY")
        )
        print(f"[SANCTUM-SUITE] Signed entitlement validated for tenant {entitlement['tenant_id']}.")
        kms = ZeroTrustKMSVault(require_production=True)
        kms.verify_production_access()
        print("[SANCTUM-SUITE] Vault Transit encrypt/decrypt access verified.")
        AuditPseudonymizer()
        print("[SANCTUM-SUITE] Audit pseudonymization key verified.")
        SecurityReportSigner()
        print("[SANCTUM-SUITE] RSA report-signing key pair verified.")
        opa = OPAPolicyClient.from_environment(required=True)
        if opa is None:
            raise OPAPolicyConfigurationError("SANCTUM_OPA_URL is required")
        asyncio.run(opa.verify_readiness())
        print("[SANCTUM-SUITE] OPA authorization policy and version verified.")
        tpm_attestation = KeylimeVerifierClient.from_environment(required=True)
        if tpm_attestation is None:
            raise TPMAttestationConfigurationError(
                "SANCTUM TPM measured-boot verifier is required"
            )
        asyncio.run(tpm_attestation.verify_readiness())
        print("[SANCTUM-SUITE] Keylime TPM measured-boot attestation verified.")
        tee_attestation = TrusteeClaimsClient.from_environment(required=True)
        if tee_attestation is None:
            raise TEEAttestationConfigurationError(
                "SANCTUM confidential-computing verifier is required"
            )
        asyncio.run(tee_attestation.verify_readiness())
        print("[SANCTUM-SUITE] Trustee SNP/TDX workload claims verified.")
        MinioImmutableAuditStore().verify_access()
        print("[SANCTUM-SUITE] MinIO Compliance Object Lock write/retention verified.")
        print("[SANCTUM-SUITE] Configuration preflight passed. This is not a production-readiness sign-off.")
        return 0
    except (
        HTTPException,
        ValueError,
        ImmutableAuditError,
        VaultTransitError,
        OPAPolicyUnavailable,
        TPMAttestationConfigurationError,
        TPMAttestationUnavailable,
        TEEAttestationConfigurationError,
        TEEAttestationUnavailable,
    ) as error:
        print(f"[SANCTUM-SUITE] Configuration preflight failed: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(run_production_check())
