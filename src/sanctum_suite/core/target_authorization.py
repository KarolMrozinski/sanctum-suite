import ipaddress
import os
import re


class TargetAuthorizationError(ValueError):
    """Raised when an active test is outside the operator-approved exact target list."""


_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_target_host(target: str) -> str:
    candidate = target.strip()
    if not candidate or "://" in candidate or any(char in candidate for char in "/?#@"):
        raise ValueError("Target must be a hostname or IP address, not a URL")
    candidate = candidate.rstrip(".").lower()
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        try:
            hostname = candidate.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise ValueError("Target is not a valid IDNA hostname") from error
        if len(hostname) > 253 or any(not _DNS_LABEL.fullmatch(label) for label in hostname.split(".")):
            raise ValueError("Target is not a valid hostname")
        return hostname


def require_authorized_target(
    target: str,
    authorization_reference: str | None,
    authorized_targets: str | None = None,
) -> str:
    normalized_target = normalize_target_host(target)
    reference = (authorization_reference or "").strip()
    if not reference or len(reference) > 500:
        raise TargetAuthorizationError("A written authorization reference is required")

    configured_targets = (
        authorized_targets
        if authorized_targets is not None
        else os.environ.get("SANCTUM_AUTHORIZED_TARGETS", "")
    )
    allowed = {
        normalize_target_host(value)
        for value in configured_targets.split(",")
        if value.strip()
    }
    if normalized_target not in allowed:
        raise TargetAuthorizationError(
            "Target is not an exact match for SANCTUM_AUTHORIZED_TARGETS"
        )
    return normalized_target
