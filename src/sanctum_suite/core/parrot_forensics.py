from typing import Any


class ParrotForensicsEngine:
    """Reports memory-dump analysis as unperformed until a forensic tool is configured."""

    def analyze_memory_dump(self, dump_file_path: str) -> dict[str, Any]:
        return {
            "dump_path": dump_file_path,
            "forensic_status": "NOT_ANALYZED",
            "analysis_performed": False,
            "artifacts_found": None,
            "artifacts": None,
            "integrity_verified": None,
        }
