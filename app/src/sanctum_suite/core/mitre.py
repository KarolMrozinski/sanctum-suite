from typing import List, Dict, Any


class MitreMapperEngine:
    """Silnik taksonomii zagrożeń wg matryc MITRE ATT&CK oraz MITRE ATLAS."""

    TECHNIQUE_MAP = {
        "PROMPT_INJECTION_RISK": {
            "technique_id": "AML.T0051",
            "technique_name": "LLM Prompt Injection",
            "tactic": "Initial Access / Execution",
            "framework": "MITRE ATLAS",
        },
        "EXPOSED_LLM_API": {
            "technique_id": "T1190",
            "technique_name": "Exploit Public-Facing Application",
            "tactic": "Initial Access",
            "framework": "MITRE ATT&CK",
        },
        "OPEN_SSH": {
            "technique_id": "T1021.004",
            "technique_name": "Remote Services: SSH",
            "tactic": "Lateral Movement",
            "framework": "MITRE ATT&CK",
        },
    }

    def map_findings(self, shadow_vulns: List[Dict[str, Any]], open_ports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapped_tactics = []

        for v in shadow_vulns:
            issue = v.get("issue")
            if issue in self.TECHNIQUE_MAP:
                mapped_tactics.append(self.TECHNIQUE_MAP[issue])

        for p in open_ports:
            if p.get("port") == 11434:
                mapped_tactics.append(self.TECHNIQUE_MAP["EXPOSED_LLM_API"])
            elif p.get("port") == 22:
                mapped_tactics.append(self.TECHNIQUE_MAP["OPEN_SSH"])

        return mapped_tactics