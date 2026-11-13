from typing import Dict, Any, List


class CiliumSecurityProfileEngine:
    """Silnik profilowania eBPF i automatycznej generacji polityk CiliumNetworkPolicy L3/L4/L7."""

    def generate_least_privilege_policy(self, pod_label: str, namespace: str = "default") -> Dict[str, Any]:
        """Tworzy deklaratywną politykę Cilium ograniczającą ruch do zweryfikowanych punktów końcowych."""
        cilium_policy = {
            "apiVersion": "cilium.io/v2",
            "kind": "CiliumNetworkPolicy",
            "metadata": {
                "name": f"strict-least-privilege-{pod_label}",
                "namespace": namespace,
            },
            "spec": {
                "endpointSelector": {
                    "matchLabels": {"app": pod_label},
                },
                "ingress": [
                    {
                        "fromEndpoints": [{"matchLabels": {"role": "api-gateway"}}],
                        "toPorts": [{"ports": [{"port": "8080", "protocol": "TCP"}]}],
                    }
                ],
                "egress": [
                    {
                        "toFQDNs": [{"matchName": "api.openai.com"}],
                        "toPorts": [{"ports": [{"port": "443", "protocol": "TCP"}]}],
                    }
                ],
            },
        }

        return {
            "pod_label": pod_label,
            "namespace": namespace,
            "status": "POLICY_GENERATED",
            "ebpf_profile_verified": None,
            "cluster_connected": False,
            "policy_applied": False,
            "policy": cilium_policy,
        }