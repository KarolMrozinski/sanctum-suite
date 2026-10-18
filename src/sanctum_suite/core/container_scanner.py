from typing import Any


class DockerContainerCVEAnalyzer:
    """Reports container-image analysis as unperformed until a scanner is configured."""

    def inspect_container_image(self, image_name: str = "sanctum-suite:latest") -> dict[str, Any]:
        return {
            "image": image_name,
            "status": "NOT_SCANNED",
            "scanner_configured": False,
            "vulnerabilities_found": None,
            "cves": None,
            "compliance_status": "NOT_ASSESSED",
        }
