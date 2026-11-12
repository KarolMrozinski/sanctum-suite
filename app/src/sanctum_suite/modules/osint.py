class SpectreOsintModule:
    """Records a supplied authorized scope without fabricating discovered assets."""

    def scan_target(self, target: str) -> dict:
        scope = target.strip()
        if not scope:
            raise ValueError("An authorized target scope is required")
        return {
            "target": scope,
            "subdomains": [],
            "exposed_assets_count": 0,
            "discovery_performed": False,
        }