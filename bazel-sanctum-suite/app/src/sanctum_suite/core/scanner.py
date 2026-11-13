import asyncio
from urllib.parse import urlsplit
from typing import Any

import httpx

from sanctum_suite.core.target_authorization import require_authorized_target


class AsyncEndpointScanner:
    """Performs bounded HTTPS checks only for explicitly allowlisted targets."""

    MAX_TARGETS = 50

    def __init__(self, timeout: float = 3.0) -> None:
        if timeout <= 0 or timeout > 30:
            raise ValueError("timeout must be greater than zero and at most 30 seconds")
        self.timeout = timeout

    @staticmethod
    def _target_url(target: str, authorization_reference: str) -> str:
        candidate = target.strip()
        if "://" in candidate:
            parsed = urlsplit(candidate)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.port is not None
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Endpoint target must be a bare hostname or HTTPS origin")
            host = parsed.hostname
        else:
            host = candidate
        approved_host = require_authorized_target(host, authorization_reference)
        host_literal = f"[{approved_host}]" if ":" in approved_host else approved_host
        return f"https://{host_literal}"

    async def _probe_single_target(
        self,
        client: httpx.AsyncClient,
        target_url: str,
    ) -> dict[str, Any]:
        response = await client.get(target_url, timeout=self.timeout, follow_redirects=False)
        expected_headers = (
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
        )
        return {
            "url": target_url,
            "status_code": response.status_code,
            "is_alive": True,
            "missing_security_headers": [
                header for header in expected_headers if header not in response.headers
            ],
            "server": response.headers.get("Server", "UNKNOWN"),
            "tls_verified": True,
        }

    async def scan_endpoints_batch(
        self,
        targets: list[str],
        authorization_reference: str,
    ) -> list[dict[str, Any]]:
        if len(targets) > self.MAX_TARGETS:
            raise ValueError(f"An endpoint scan is limited to {self.MAX_TARGETS} targets")
        approved_urls = [
            self._target_url(target, authorization_reference)
            for target in targets
        ]
        async with httpx.AsyncClient(verify=True, follow_redirects=False) as client:
            return list(
                await asyncio.gather(
                    *(
                        self._probe_single_target(client, target_url)
                        for target_url in approved_urls
                    )
                )
            )

    def run_sync_batch_scan(
        self,
        targets: list[str],
        authorization_reference: str,
    ) -> list[dict[str, Any]]:
        return asyncio.run(self.scan_endpoints_batch(targets, authorization_reference))
