from __future__ import annotations

from typing import Any


class SigstoreCosignSecurityManager:
    """Plans Sigstore/Cosign signing and attestation controls without invoking external services."""

    def assess_sigstore_cosign(
        self,
        artifact_name: str = "sanctum-suite-release",
        repository: str = "KarolMrozinski/sanctum-suite",
    ) -> dict[str, Any]:
        artifact = (artifact_name or "unnamed-artifact").strip() or "unnamed-artifact"
        repo = (repository or "unknown/repository").strip() or "unknown/repository"

        return {
            "platform": "Sigstore / Cosign",
            "status": "PLAN_ONLY",
            "artifact": artifact,
            "repository": repo,
            "key_requirements": [
                "OIDC-backed identity for signing workflows",
                "Fulcio certificate issuance for ephemeral signing identities",
                "Rekor transparency log for provenance publication",
            ],
            "recommended_controls": [
                "Sign every release artifact with Cosign and enforce provenance generation in CI.",
                "Require identity, issuer, and subject checks before accepting an attestation as trusted.",
                "Publish supply-chain metadata to Rekor and validate transparency log evidence during release approval.",
            ],
            "attestation_types": [
                "in-toto statement",
                "SLSA provenance",
                "binary signature verification",
            ],
            "verification_steps": [
                "Verify the signature against the expected certificate identity.",
                "Confirm the subject digest matches the artifact being released.",
                "Review the attestation predicate and allow only approved provenance metadata.",
            ],
            "recommendations": [
                "Use signed and attestable release pipelines for all artifacts and container images.",
                "Keep Sigstore verification as a gate in promotion and production deployment workflows.",
                "Record verification results in the audit archive, but do not treat the plan as a live trust decision.",
            ],
        }

    assess_supply_chain_signing = assess_sigstore_cosign


class SigstoreCosignManager(SigstoreCosignSecurityManager):
    """Backward-compatible alias for the Sigstore/Cosign planning module."""

    def assess_supply_chain_signing(
        self,
        artifact_name: str = "sanctum-suite-release",
        repository: str = "KarolMrozinski/sanctum-suite",
    ) -> dict[str, Any]:
        return super().assess_sigstore_cosign(artifact_name=artifact_name, repository=repository)
