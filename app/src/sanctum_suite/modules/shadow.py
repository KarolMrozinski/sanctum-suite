class ShadowAgentModule:
    """Reports LLM endpoint assessment as unperformed without a model test harness."""

    def evaluate_llm_endpoints(self, endpoints: list[str]) -> dict:
        return {
            "status": "NOT_ASSESSED",
            "assessment_performed": False,
            "endpoints_received": len(endpoints),
            "endpoints_scanned": 0,
            "vulnerabilities": None,
        }