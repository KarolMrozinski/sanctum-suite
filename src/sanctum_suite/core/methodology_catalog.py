"""Version-labeled framework references, not executable compliance packs."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MethodologyReference:
    reference_id: str
    name: str
    category: str
    version: str
    implementation_status: str
    source_url: str


_REFERENCES = (
    MethodologyReference(
        "owasp-asvs",
        "OWASP Application Security Verification Standard",
        "standard",
        "5.0.0",
        "REFERENCE_ONLY",
        "https://owasp.org/www-project-application-security-verification-standard/",
    ),
    MethodologyReference(
        "cwe-top-25",
        "CWE Top 25",
        "weakness-prioritization",
        "2025",
        "REFERENCE_ONLY",
        "https://cwe.mitre.org/top25/",
    ),
    MethodologyReference(
        "nist-csf",
        "NIST Cybersecurity Framework",
        "framework",
        "2.0",
        "REFERENCE_ONLY",
        "https://www.nist.gov/cyberframework",
    ),
    MethodologyReference(
        "cis-controls",
        "CIS Critical Security Controls",
        "controls",
        "8.1",
        "REFERENCE_ONLY",
        "https://www.cisecurity.org/controls",
    ),
    MethodologyReference(
        "nist-ai-rmf",
        "NIST AI Risk Management Framework",
        "framework",
        "1.0",
        "REFERENCE_ONLY",
        "https://www.nist.gov/itl/ai-risk-management-framework",
    ),
    MethodologyReference(
        "nist-sp-800-53",
        "NIST Security and Privacy Controls",
        "controls",
        "Rev. 5",
        "REFERENCE_ONLY",
        "https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
    ),
    MethodologyReference(
        "iso-iec-42001",
        "AI management systems",
        "standard",
        "2023",
        "REFERENCE_ONLY",
        "https://www.iso.org/standard/81230.html",
    ),
    MethodologyReference(
        "nis2",
        "Directive (EU) 2022/2555",
        "legislation",
        "2022",
        "REFERENCE_ONLY",
        "https://eur-lex.europa.eu/eli/dir/2022/2555/oj",
    ),
    MethodologyReference(
        "dora",
        "Regulation (EU) 2022/2554",
        "legislation",
        "2022",
        "REFERENCE_ONLY",
        "https://eur-lex.europa.eu/eli/reg/2022/2554/oj",
    ),
    MethodologyReference(
        "ptes",
        "Penetration Testing Execution Standard",
        "methodology",
        "OPERATOR_VERSION_REQUIRED",
        "NOT_IMPLEMENTED",
        "http://www.pentest-standard.org/",
    ),
    MethodologyReference(
        "osstmm",
        "Open Source Security Testing Methodology Manual",
        "methodology",
        "OPERATOR_VERSION_REQUIRED",
        "NOT_IMPLEMENTED",
        "https://www.isecom.org/OSSTMM.3.pdf",
    ),
    MethodologyReference(
        "tiber-eu",
        "TIBER-EU Framework",
        "methodology",
        "OPERATOR_VERSION_REQUIRED",
        "NOT_IMPLEMENTED",
        "https://www.ecb.europa.eu/paym/cyber-resilience/tiber-eu/html/index.en.html",
    ),
    MethodologyReference(
        "mitre-attack",
        "MITRE ATT&CK",
        "threat-model",
        "OPERATOR_VERSION_REQUIRED",
        "REFERENCE_ONLY",
        "https://attack.mitre.org/",
    ),
    MethodologyReference(
        "diamond-model",
        "Diamond Model of Intrusion Analysis",
        "threat-model",
        "2006",
        "REFERENCE_ONLY",
        "https://www.threatintel.academy/wp-content/uploads/2020/07/diamond.pdf",
    ),
    MethodologyReference(
        "nist-pqc",
        "NIST post-quantum cryptography standards",
        "cryptography",
        "FIPS 203, 204, 205",
        "INVENTORY_CLASSIFICATION_ONLY",
        "https://csrc.nist.gov/projects/post-quantum-cryptography",
    ),
    MethodologyReference(
        "parrot-os",
        "Parrot Security OS",
        "platform",
        "OPERATOR_IMAGE_DIGEST_REQUIRED",
        "ENVIRONMENT_DETECTION_ONLY",
        "https://parrotsec.org/download/",
    ),
    MethodologyReference(
        "google-project-zero",
        "Google Project Zero research",
        "research-source",
        "OPERATOR_SELECTED_PUBLICATIONS",
        "REFERENCE_ONLY",
        "https://googleprojectzero.blogspot.com/",
    ),
    MethodologyReference(
        "pwn2own",
        "Pwn2Own public research program",
        "research-source",
        "OPERATOR_SELECTED_PUBLICATIONS",
        "REFERENCE_ONLY",
        "https://www.zerodayinitiative.com/pwn2own/",
    ),
    MethodologyReference(
        "microsoft-msrc",
        "Microsoft Security Response Center",
        "research-source",
        "OPERATOR_SELECTED_PUBLICATIONS",
        "REFERENCE_ONLY",
        "https://www.microsoft.com/en-us/msrc",
    ),
    MethodologyReference(
        "mandiant-research",
        "Mandiant threat research",
        "research-source",
        "OPERATOR_SELECTED_PUBLICATIONS",
        "REFERENCE_ONLY",
        "https://www.mandiant.com/resources/blog",
    ),
    MethodologyReference(
        "nsa-cybersecurity-advisories",
        "NSA Cybersecurity Advisories and Guidance",
        "research-source",
        "OPERATOR_SELECTED_PUBLICATIONS",
        "REFERENCE_ONLY",
        "https://www.nsa.gov/Press-Room/Cybersecurity-Advisories-Guidance/",
    ),
    MethodologyReference(
        "uk-ncsc-guidance",
        "UK NCSC public guidance",
        "research-source",
        "OPERATOR_SELECTED_PUBLICATIONS",
        "REFERENCE_ONLY",
        "https://www.ncsc.gov.uk/section/keep-up-to-date/all-blogs",
    ),
    MethodologyReference(
        "vx-underground",
        "VX-Underground research archive",
        "research-source",
        "OPERATOR_SELECTED_PUBLICATIONS",
        "REFERENCE_ONLY",
        "https://vx-underground.org/",
    ),
)


def list_methodology_references(category: str | None = None) -> list[dict[str, Any]]:
    references = _REFERENCES
    if category:
        requested = category.casefold()
        references = tuple(item for item in references if item.category.casefold() == requested)
    return [asdict(item) for item in references]
