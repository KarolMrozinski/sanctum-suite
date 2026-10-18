import hashlib
from typing import List


class GhostNetDgaEngine:
    """Generator algorytmów DGA (Domain Generation Algorithms) oraz mechanizmów Fast Flux IP."""

    def generate_dga_domains(self, seed_phrase: str, count: int = 5) -> List[str]:
        domains = []
        for i in range(count):
            raw = f"{seed_phrase}:{i}:ghostnet"
            h = hashlib.sha256(raw.encode()).hexdigest()[:12]
            domains.append(f"{h}.ghost-enclave.net")
        return domains