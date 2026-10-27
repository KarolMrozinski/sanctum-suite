#!/usr/bin/env python3

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

from sanctum_suite.core.agent_orchestrator import AutonomousAgentOrchestrator
from sanctum_suite.core.telemetry_buffer import TelemetryBuffer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (SanctumCLI): %(message)s"
)
logger = logging.getLogger("SanctumCLI")

class SanctumCLI:

    def __init__(self, workspace_dir: Path = Path("/var/lib/sanctum")):
        self.workspace_dir = Path(workspace_dir)
        self.orchestrator = AutonomousAgentOrchestrator(workspace_dir=self.workspace_dir)
        self.telemetry = TelemetryBuffer(buffer_dir=self.workspace_dir / "telemetry")
        logger.info("Inicjalizacja SanctumCLI - Centralny Panel Operatora Air-Gapped.")

    def handle_status_command(self) -> None:
        print("=== SANCTUM SUITE: STATUS SYSTEMU I AGENTÓW ===")
        state_file = self.workspace_dir / "orchestrator_state.json"
        
        if state_file.exists():
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
                print(json.dumps(state_data, indent=2, sort_keys=True))
            except Exception as e:
                print(f"Błąd odczytu stanu orkiestratora: {e}")
        else:
            print("Brak zapisanych stanów orkiestratora. Uruchom cykl autonomiczny.")

        override_active = self.orchestrator.is_operator_override_active()
        print(f"\n[Operator Oversight] Blokada nadzoru (Override): {'AKTYWNA' / 'WYŁĄCZONA' if not override_active else 'AKTYWNA'}")
        print(f"[Telemetry Buffer] Oczekujące wpisy w pamięci: {self.telemetry.get_buffered_count()}")

    def handle_run_cycle_command(self) -> None:
        print("=== WYZWOLENIE AUTONOMICZNEGO CYKLU AGENTÓW ===")
        mock_telemetry_summary = {
            "high_severity_incidents_found": 0,
            "flagged_anomalies_count": 0
        }
        report = self.orchestrator.run_autonomous_cycle(mock_telemetry_summary)
        print("Wynik cyklu autonomicznego:")
        print(json.dumps(report, indent=2, sort_keys=True))

    def main(self) -> None:
        if len(sys.argv) < 2:
            print("Użycie: sanctum-cli [status | run-cycle | override-on | override-off]")
            sys.exit(1)

        command = sys.argv[1].lower()

        if command == "status":
            self.handle_status_command()
        elif command == "run-cycle":
            self.handle_run_cycle_command()
        elif command == "override-on":
            self.orchestrator.operator_override_flag.touch()
            print("Włączono blokadę nadzoru operatora (Operator Override ACTIVE).")
        elif command == "override-off":
            if self.orchestrator.operator_override_flag.exists():
                self.orchestrator.operator_override_flag.unlink()
            print("Wyłączono blokadę nadzoru operatora (Autonomous Mode ACTIVE).")
        else:
            print(f"Nieznana komenda: {command}")
            sys.exit(1)

if __name__ == "__main__":
    cli = SanctumCLI()
    cli.main()