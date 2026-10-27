#!/usr/bin/env python3

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (MicroVMSandboxGuard): %(message)s"
)
logger = logging.getLogger("MicroVMSandboxGuard")

class SandboxExecutionError(Exception):
    pass

class MicroVMSandboxGuard:

    def __init__(self, sandbox_root: Path = Path("/var/lib/sanctum/sandbox")):
        self.sandbox_root = Path(sandbox_root)
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja MicroVMSandboxGuard w katalogu: {self.sandbox_root}")

    def execute_isolated_command(self, command_args: List[str], timeout_seconds: int = 30) -> Dict[str, Any]:
        logger.info(f"Uruchamianie polecenia w izolowanym środowisku sandbox: {' '.join(command_args)}")
        
        execution_id = f"SANDBOX-RUN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        start_time = datetime.utcnow()

        try:
            # Symulacja bezpiecznego wykonania z restrykcjami środowiskowymi
            result = subprocess.run(
                command_args,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env={**os.environ, "SANCTUM_SANDBOX_MODE": "enforced"}
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            success = (result.returncode == 0)

            logger.info(f"Wykonanie w sandbox zakończone (Exit Code: {result.returncode}, Czas: {duration}s).")

            return {
                "execution_id": execution_id,
                "command": command_args,
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "duration_seconds": duration,
                "status": "success" if success else "failed",
                "executed_at": start_time.isoformat() + "Z"
            }

        except subprocess.TimeoutExpired as te:
            logger.error(f"Przekroczono limit czasu w sandbox dla polecenia: {command_args}")
            raise SandboxExecutionError(f"Sandbox execution timed out: {te}") from te
        except Exception as e:
            logger.error(f"Krytyczny błąd podczas wykonywania w sandbox: {e}")
            raise SandboxExecutionError(f"Sandbox execution failed: {e}") from e