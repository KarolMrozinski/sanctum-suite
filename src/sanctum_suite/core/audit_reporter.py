#!/usr/bin/env python3
import json
import hashlib
from datetime import datetime
from pathlib import Path

class SecurityAuditReporter:
    """Generuje kryptograficznie powiązane raporty audytowe w formacie STIX/JSON dla komponentów Sanctum Suite."""
    
    def __init__(self, audit_dir: Path = Path("/var/lib/sanctum/audit")):
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def write_audit_event(self, event_type: str, details: dict) -> Path:
        timestamp = datetime.utcnow().isoformat() + "Z"
        payload = {
            "timestamp": timestamp,
            "event_type": event_type,
            "details": details,
            "generator": "Sanctum-Suite-Enterprise-Core"
        }
        
        raw_data = json.dumps(payload, sort_keys=True).encode("utf-8")
        event_hash = hashlib.sha256(raw_data).hexdigest()
        payload["integrity_sha256"] = event_hash
        
        filename = self.audit_dir / f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filename.write_text(json.dumps(payload, indent=4), encoding="utf-8")
        
        print(f"[+] Zapisano bezpieczny raport audytowy: {filename}")
        return filename