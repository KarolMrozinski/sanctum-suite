import hmac
import base64
from typing import List, Generator


class CryptoPipelineEngine:
    """Zaawansowany pipeline kryptograficzny: ROT, dynamiczny XOR oparty na ciągach matematycznych, Base64."""

    @staticmethod
    def _generate_fibonacci(n: int) -> List[int]:
        fib = [1, 1]
        while len(fib) < n:
            fib.append(fib[-1] + fib[-2])
        return [x % 256 for x in fib]

    @staticmethod
    def _generate_primes(n: int) -> List[int]:
        primes = []
        num = 2
        while len(primes) < n:
            if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):
                primes.append(num)
            num += 1
        return [p % 256 for p in primes]

    def dynamic_xor_transform(self, data: bytes, sequence_type: str = "fibonacci") -> bytes:
        seq = self._generate_fibonacci(len(data)) if sequence_type == "fibonacci" else self._generate_primes(len(data))
        return bytes(b ^ s for b, s in zip(data, seq))

    def multi_pass_rot(self, text: str, shift: int = 13, passes: int = 2) -> str:
        current = text
        for _ in range(passes):
            res = []
            for char in current:
                if 'a' <= char <= 'z':
                    res.append(chr((ord(char) - ord('a') + shift) % 26 + ord('a')))
                elif 'A' <= char <= 'Z':
                    res.append(chr((ord(char) - ord('A') + shift) % 26 + ord('A')))
                else:
                    res.append(char)
            current = "".join(res)
        return current

    @staticmethod
    def secure_compare(val_a: str, val_b: str) -> bool:
        """Zapobiega atakom czasowym (Timing Attacks) podczas weryfikacji klucza."""
        return hmac.compare_digest(val_a.encode('utf-8'), val_b.encode('utf-8'))