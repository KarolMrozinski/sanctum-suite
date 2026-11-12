from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping


class KubernetesWebhookHandler:
    """Validates and interprets admission review webhooks from Kubernetes controllers."""

    def __init__(self, *, secret: str | None = None, allowed_gateways: tuple[str, ...] = ()) -> None:
        self.secret = secret or ""
        self.allowed_gateways = allowed_gateways

    @staticmethod
    def _normalize_payload(payload: Mapping[str, Any] | Any) -> dict[str, Any]:
        if isinstance(payload, Mapping):
            return dict(payload)
        if hasattr(payload, "model_dump"):
            return dict(payload.model_dump())
        if hasattr(payload, "dict"):
            return dict(payload.dict())
        raise TypeError("Webhook payload must be a mapping-like object")

    def validate_signature(self, payload: Mapping[str, Any] | Any, *, signature: str | None = None, secret: str | None = None) -> bool:
        signing_secret = (secret or self.secret or "").encode("utf-8")
        if not signing_secret:
            return True
        if not signature:
            raise ValueError("A webhook signature is required when a signing secret is configured")
        candidate = hmac.new(signing_secret, json.dumps(self._normalize_payload(payload), separators=(",", ":"), sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(candidate, signature)

    def handle_admission_review(self, payload: Mapping[str, Any] | Any) -> dict[str, Any]:
        data = self._normalize_payload(payload)
        kind = data.get("kind") or data.get("request", {}).get("kind") or "AdmissionReview"
        uid = data.get("uid") or data.get("request", {}).get("uid") or "unknown-uid"
        response = {
            "allowed": True,
            "uid": uid,
            "status": {"message": "sanctum-suite admission review accepted"},
        }
        if kind not in {"AdmissionReview", "admission.k8s.io/v1", "admission.k8s.io/v1beta1"}:
            response["allowed"] = False
            response["status"]["message"] = "unsupported admission review kind"
        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": response,
        }

    def handle_event(self, payload: Mapping[str, Any] | Any) -> dict[str, Any]:
        return self.handle_admission_review(payload)


KubernetesAdmissionWebhook = KubernetesWebhookHandler
