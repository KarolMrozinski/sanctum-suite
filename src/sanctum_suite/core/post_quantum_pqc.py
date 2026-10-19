import re
from collections.abc import Mapping, Sequence
from typing import Any


_STANDARDIZED_PQC = {
    "ML-KEM": "NIST FIPS 203",
    "ML-DSA": "NIST FIPS 204",
    "SLH-DSA": "NIST FIPS 205",
}
_PQC_PATTERNS = (
    ("ML-KEM", re.compile(r"^ML-KEM(?:-(?:512|768|1024))?$")),
    ("ML-DSA", re.compile(r"^ML-DSA(?:-(?:44|65|87))?$")),
    (
        "SLH-DSA",
        re.compile(
            r"^SLH-DSA(?:-(?:SHA2|SHAKE)-(?:128S|128F|192S|192F|256S|256F))?$"
        ),
    ),
)
_PQC_KEY_ESTABLISHMENT_PROTOCOLS = {"PQXDH"}
_CLASSICAL_PUBLIC_KEY_PATTERN = re.compile(
    r"^(RSA|ECDH|ECDSA|ECDHE|DH|DHE|DSA|ED25519|ED448|X25519|X448)(?:[-_ ]|$)"
)
_SYMMETRIC_OR_HASH = {
    "AES",
    "AES-GCM",
    "AES-128",
    "AES-192",
    "AES-256",
    "CHACHA20",
    "CHACHA20-POLY1305",
    "SHA-256",
    "SHA-384",
    "SHA-512",
    "SHA3-256",
    "SHA3-384",
    "SHA3-512",
}
_USE_CASES = {"key_establishment", "digital_signature", "other", "unknown"}


class PostQuantumCryptographicAssuranceEngine:
    """Classifies an operator-supplied crypto inventory; it does not inspect runtime keys."""

    def audit_cryptographic_primitives(
        self,
        inventory: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if inventory is None:
            return {
                "status": "NOT_ASSESSED",
                "inventory_required": True,
                "limitations": "No cryptographic primitives were discovered or supplied.",
            }

        reviewed: list[dict[str, Any]] = []
        for item in inventory:
            if not isinstance(item, Mapping):
                raise ValueError("Each inventory entry must be an object")
            algorithm_value = item.get("algorithm", "")
            location_value = item.get("location", "")
            if not isinstance(algorithm_value, str) or not isinstance(location_value, str):
                raise ValueError("Each inventory algorithm and location must be strings")
            algorithm = algorithm_value.strip()
            location = location_value.strip()
            if not algorithm or not location:
                raise ValueError("Each inventory entry requires an algorithm and location")
            normalized = algorithm.upper()
            pqc_family = next(
                (
                    family
                    for family, pattern in _PQC_PATTERNS
                    if pattern.fullmatch(normalized)
                ),
                None,
            )
            if normalized in _PQC_KEY_ESTABLISHMENT_PROTOCOLS:
                classification = "POST_QUANTUM_KEY_ESTABLISHMENT_PROTOCOL_REPORTED"
                family = normalized
                standard = ""
                migration_review = "VERIFY_PROTOCOL_SPEC_IMPLEMENTATION_AND_INTEROPERABILITY"
            elif pqc_family is not None:
                classification = "STANDARDIZED_PQC_ALGORITHM_REPORTED"
                family = pqc_family
                standard = _STANDARDIZED_PQC[family]
                migration_review = "VERIFY_PARAMETERS_IMPLEMENTATION_AND_INTEROPERABILITY"
            elif _CLASSICAL_PUBLIC_KEY_PATTERN.match(normalized):
                classification = "CLASSICAL_PUBLIC_KEY_ALGORITHM_REPORTED"
                standard = ""
                family = normalized.split("-", maxsplit=1)[0]
                migration_review = "MIGRATION_PLANNING_REQUIRED"
            elif normalized in _SYMMETRIC_OR_HASH:
                classification = "SYMMETRIC_OR_HASH_ALGORITHM_REPORTED"
                standard = ""
                family = normalized
                migration_review = "REVIEW_KEY_SIZE_HASH_USE_AND_PROTOCOL_CONTEXT"
            else:
                classification = "ALGORITHM_REQUIRES_REVIEW"
                standard = ""
                family = ""
                migration_review = "MANUAL_ALGORITHM_REVIEW_REQUIRED"

            use_case = item.get("use_case", "unknown")
            if not isinstance(use_case, str) or use_case not in _USE_CASES:
                raise ValueError(
                    "use_case must be key_establishment, digital_signature, other, or unknown"
                )
            long_term_confidentiality = item.get(
                "requires_long_term_confidentiality"
            )
            if long_term_confidentiality is not None and not isinstance(
                long_term_confidentiality, bool
            ):
                raise ValueError("requires_long_term_confidentiality must be a boolean")
            if (
                classification == "CLASSICAL_PUBLIC_KEY_ALGORITHM_REPORTED"
                and use_case == "key_establishment"
                and long_term_confidentiality is True
            ):
                migration_review = "PRIORITIZE_HARVEST_NOW_DECRYPT_LATER_REVIEW"
            reviewed.append({
                "algorithm": algorithm,
                "algorithm_family": family,
                "location": location,
                "use_case": use_case,
                "classification": classification,
                "standard": standard,
                "requires_long_term_confidentiality": long_term_confidentiality,
                "migration_review": migration_review,
            })

        return {
            "status": "INVENTORY_REVIEW_REQUIRED" if reviewed else "NOT_ASSESSED",
            "inventory_scope": "OPERATOR_SUPPLIED",
            "algorithms": reviewed,
            "review_counts": {
                "total": len(reviewed),
                "classical_public_key": sum(
                    item["classification"] == "CLASSICAL_PUBLIC_KEY_ALGORITHM_REPORTED"
                    for item in reviewed
                ),
                "standardized_pqc_reported": sum(
                    item["classification"] == "STANDARDIZED_PQC_ALGORITHM_REPORTED"
                    for item in reviewed
                ),
                "manual_review": sum(
                    item["classification"] == "ALGORITHM_REQUIRES_REVIEW"
                    for item in reviewed
                ),
                "hndl_review_prioritized": sum(
                    item["migration_review"]
                    == "PRIORITIZE_HARVEST_NOW_DECRYPT_LATER_REVIEW"
                    for item in reviewed
                ),
            },
            "limitations": (
                "This report classifies operator-supplied names and declared use cases only. "
                "It does not discover deployed cryptography, validate parameter sets, "
                "implementation, key management, protocol negotiation, or migration readiness. "
                "Migration review priorities are triage hints, not a risk assessment or certification."
            ),
        }
