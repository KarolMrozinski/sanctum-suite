from typing import List, Dict, Any


class ThreatCorrelationEngine:
    """Silnik korelacji incydentów wykrywający złożone łańcuchy ataku (Attack Chains)."""

    def correlate_findings(self, open_ports: List[Dict[str, Any]], shadow_vulns: List[Dict[str, Any]]) -> Dict[str, Any]:
        attack_chains = []
        risk_multiplier = 1.0

        # Wykrycie otwartego portu Ollama API (11434) w połączeniu z podatnością Prompt Injection
        has_ollama_port = any(p.get("port") == 11434 for p in open_ports)
        has_prompt_injection = any(v.get("issue") == "PROMPT_INJECTION_RISK" for v in shadow_vulns)

        if has_ollama_port and has_prompt_injection:
            attack_chains.append({
                "chain_id": "CHAIN-AI-01",
                "severity": "CRITICAL",
                "description": "Exposed Ollama LLM API port combined with validated Prompt Injection vulnerability.",
            })
            risk_multiplier = 1.5

        return {
            "risk_multiplier": risk_multiplier,
            "detected_attack_chains": attack_chains,
            "chain_count": len(attack_chains),
        }