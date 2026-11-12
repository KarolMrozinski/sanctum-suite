#!/usr/bin/env python3
# ==============================================================================
# Sanctum Suite: Ghidra Headless Bridge & Automated Binary Analyzer
# Umożliwia zautomatyzowaną analizę wsteczną binariów w środowiskach Air-Gapped
# ==============================================================================

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (GhidraBridge): %(message)s")
logger = logging.getLogger("GhidraBridge")


class GhidraBridgeError(Exception):
    """Wyjątek dla błędów wykonania silnika Ghidra Headless."""
    pass


class GhidraHeadlessBridge:
    """
    Klasa zarządzająca integracją z frameworkiem Ghidra w trybie headless
    do automatycznego skanowania i dekompilacji kodu maszynowego.
    """

    def __init__(self, ghidra_home: str, workspace_dir: str = "/var/lib/sanctum/ghidra_projects"):
        self.ghidra_home = Path(ghidra_home)
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Ścieżka do skryptu headless Ghidry (zależna od systemu)
        script_name = "analyzeHeadless.bat" if os.name == "nt" else "analyzeHeadless"
        self.headless_script = self.ghidra_home / "support" / script_name
        
        if not self.headless_script.exists():
            logger.warning(f"Ghidra headless script not found at expected path: {self.headless_script}")
        else:
            logger.info(f"Initialized GhidraHeadlessBridge. Ghidra Home: {self.ghidra_home}")

    def analyze_binary(self, binary_path: str, project_name: str = "AirGapAnalysis") -> Dict[str, Any]:
        """
        Uruchamia automatyczną analizę binarnego pliku wykonywalnego w trybie headless.
        """
        bin_path = Path(binary_path)
        if not bin_path.exists():
            raise GhidraBridgeError(f"Target binary not found: {bin_path}")

        if not self.headless_script.exists():
            raise GhidraBridgeError(f"Ghidra executable script missing: {self.headless_script}")

        project_path = self.workspace_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        # Komenda uruchamiająca Ghidra Headless
        cmd = [
            str(self.headless_script),
            str(project_path),
            f"TempProject_{bin_path.name}",
            "-import", str(bin_path),
            "-overwrite",
            "-noanalysis" # Można usunąć, aby wykonać pełny autodecompiler pass
        ]

        logger.info(f"Executing Ghidra analysis on target binary: {bin_path.name}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error(f"Ghidra analysis failed: {result.stderr}")
                raise GhidraBridgeError(f"Ghidra process exited with code {result.returncode}")

            logger.info(f"Binary {bin_path.name} successfully analyzed by Ghidra framework.")
            return {
                "binary_name": bin_path.name,
                "project_path": str(project_path),
                "status": "SUCCESS",
                "stdout": result.stdout[:1000] # Zwrócenie wycinka logów analizy
            }

        except subprocess.TimeoutExpired:
            logger.error("Ghidra analysis timed out after 300 seconds.")
            raise GhidraBridgeError("Analysis timeout")
        except Exception as e:
            logger.error(f"Unexpected error during Ghidra execution: {str(e)}")
            raise GhidraBridgeError(str(e))