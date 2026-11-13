from typing import List, Dict


class BookCipherEngine:
    """Kryptograficzny system szyfrowania książkowego (Book Cipher) względem lokalnego manifestu tekstu."""

    def __init__(self, manifest_text: str) -> None:
        self.lines = [line.strip().split() for line in manifest_text.splitlines() if line.strip()]

    def encrypt_to_indices(self, secret_word: str) -> List[Dict[str, int]]:
        indices = []
        target = secret_word.lower()
        for line_idx, line in enumerate(self.lines):
            for word_idx, word in enumerate(line):
                cleaned_word = "".join(c for c in word.lower() if c.isalnum())
                if cleaned_word == target:
                    indices.append({"line": line_idx, "word": word_idx})
        return indices

    def decrypt_from_indices(self, indices: List[Dict[str, int]]) -> str:
        resolved_words = []
        for idx in indices:
            l_idx = idx["line"]
            w_idx = idx["word"]
            if 0 <= l_idx < len(self.lines) and 0 <= w_idx < len(self.lines[l_idx]):
                resolved_words.append(self.lines[l_idx][w_idx])
        return " ".join(resolved_words)