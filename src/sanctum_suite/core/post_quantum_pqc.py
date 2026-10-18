from collections.abc import Mapping, Sequence
from typing import Any


_STANDARDIZED_PQC = {
    "ML-KEM": "NIST FIPS 203",
    "ML-DSA": "NIST FIPS 204",
    "SLH-DSA": "NIST FIPS 205",
}
_CLASSICAL_PUBLIC_KEY = {"RSA", "ECDH", "ECDSA", "DH", "DSA"}


class PostQuantumCryptographicAssuranceEngine:
    """Classifies an operator-supplied crypto inventory; it does not inspect runtime keys."""

    def audit_cryptographic_primitives(
        self,
        inventory: Sequence[Mapping[str, str]] | None = None,
    ) -> dict[str, Any]:
        if inventory is None:
            return {
                "status": "NOT_ASSESSED",
                "inventory_required": True,
                "limitations": "No cryptographic primitives were discovered or supplied.",
            }

        reviewed: list[dict[str, str]] = []
        for item in inventory:
            algorithm = item.get("algorithm", "").strip()
            location = item.get("location", "").strip()
            if not algorithm or not location:
                raise ValueError("Each inventory entry requires an algorithm and location")
            normalized = algorithm.upper()
            if normalized in _STANDARDIZED_PQC:
                classification = "STANDARDIZED_PQC_ALGORITHM_REPORTED"
                standard = _STANDARDIZED_PQC[normalized]
            elif normalized in _CLASSICAL_PUBLIC_KEY:
                classification = "CLASSICAL_PUBLIC_KEY_ALGORITHM_REPORTED"
                standard = ""
            else:
                classification = "ALGORITHM_REQUIRES_REVIEW"
                standard = ""
            reviewed.append({
                "algorithm": algorithm,
                "location": location,
                "classification": classification,
                "standard": standard,
            })

        return {
            "status": "INVENTORY_REVIEW_REQUIRED" if reviewed else "NOT_ASSESSED",
            "inventory_scope": "OPERATOR_SUPPLIED",
            "algorithms": reviewed,
            "limitations": (
                "Names are classified only; this does not validate implementation, "
                "parameter sets, key management, protocol negotiation, or deployment."
            ),
        }
