import pytest
from sanctum_suite.core.classified_info_vault import ClassifiedInformationVault


def test_classified_vault_access_denied():
    vault = ClassifiedInformationVault()
    # Próba dostępu z za niską klauzulą (Secret do Top Secret)
    res = vault.store_compartmented_payload(
        payload_id="DOC-99",
        data="CRITICAL_DEFENSE_TELEMETRY",
        classification_level="TOP_SECRET",
        clearance_level="SECRET"
    )
    assert res["access_granted"] is False
    assert res["status"] == "SECURITY_BREACH_ATTEMPT_LOGGED"


def test_classified_vault_access_granted():
    vault = ClassifiedInformationVault()
    # Prawidłowy dostęp (Secret do Secret)
    res = vault.store_compartmented_payload(
        payload_id="DOC-100",
        data="TACTICAL_CYBER_INTELLIGENCE",
        classification_level="SECRET",
        clearance_level="SECRET"
    )
    assert res["access_granted"] is True
    assert res["status"] == "PAYLOAD_SECURED_COMPARTMENTED_NOMINAL"