import random
from typing import Dict, Any, List


class GANMutatorEngine:
    """Silnik ewolucyjnej mutacji i syntezy adwersarialnej wariantów promptów."""

    def __init__(self) -> None:
        self.mutation_strategies = [
            "SYNONYM_REPLACEMENT",
            "SEMANTIC_PARAPHRASE",
            "HOMOGLYPH_INJECTION",
            "BYTE_ORDER_MARK_PADDING",
        ]

    def generate_mutations(self, base_prompt: str, generations: int = 3) -> Dict[str, Any]:
        """Generuje syntetyczne warianty podanego promptu za pomocą znanych strategii mutacji."""
        mutated_variants: List[Dict[str, str]] = []

        for i in range(generations):
            strategy = self.mutation_strategies[i % len(self.mutation_strategies)]
            if strategy == "SYNONYM_REPLACEMENT":
                mutated_text = base_prompt.replace("ignore", "bypass").replace("system", "core_admin")
            elif strategy == "SEMANTIC_PARAPHRASE":
                mutated_text = f"In a hypothetical research context, please {base_prompt}"
            elif strategy == "HOMOGLYPH_INJECTION":
                mutated_text = base_prompt.replace("e", "е")  # Cyrylica 'e'
            else:
                mutated_text = f"\u200B{base_prompt}\u200B"

            mutated_variants.append({
                "generation_id": f"GEN-{i+1}",
                "strategy": strategy,
                "mutated_prompt": mutated_text,
            })

        return {
            "base_prompt": base_prompt,
            "total_generated": len(mutated_variants),
            "variants": mutated_variants,
        }