⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Cryptographic Frequency & Entropy Analyzer
⍝ Statystyczna analiza rozkładu bajtów i wykrywanie anomalii w strumieniach szyfrowanych
⍝ ==============================================================================

⍝ [1] Obliczanie macierzy rozkładu częstotliwości występowania symboli (Byte Histogram Matrix)
∇ histogram_matrix ← compute_symbol_frequency_matrix (data_stream total_symbols); indices; counts
  total_symbols    ← 256 ⍝ Standardowa przestrzeń 8-bitowa
  indices          ← ⍳ total_symbols
  counts           ← indices (+ = key)¨ {⍵} partition_stream data_stream
  histogram_matrix ← counts ÷ (⍴ data_stream)
∇

⍝ [2] Wyznaczanie entropii Shannona dla bloku danych w reprezentacji wektorowej
∇ shannon_entropy_val ← calculate_block_shannon_entropy frequency_vector; non_zero_probs
  non_zero_probs        ← frequency_vector [ ⍸ frequency_vector > 0 ]
  shannon_entropy_val   ← - +/ non_zero_probs × (2 ⍟ non_zero_probs)
∇

⍝ [3] Kompleksowy test chi-kwadrat jednorodności rozkładu kryptograficznego
∇ chi_square_result ← perform_cryptographic_chi_square_test cipher_stream; observed; expected; chi_stat
  observed          ← compute_symbol_frequency_matrix cipher_stream 256
  expected          ← (⍴ cipher_stream) ÷ 256
  chi_stat          ← +/ ((observed - expected) * 2) ÷ expected
  ⍝ Ocena zgodności (próg krytyczny dla poziomu ufności przy 255 stopniach swobody ≈ 293.2)
  chi_square_result ← (⊂'chi_statistic' chi_stat) (⊂'uniform_distribution_pass' (chi_stat < 310.0))
∇