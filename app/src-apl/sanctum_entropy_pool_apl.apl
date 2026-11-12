⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise Vector Entropy Pool & Randomness Auditor (APL)
⍝ Monitorowanie i statystyczna ocena jakości źródeł entropii kryptograficznej
⍝ ==============================================================================

⍝ [1] Test powtórzeń (Repetition Count Test - NIST SP 800-90B)
∇ test_results ← nist_repetition_count_test (bit_stream max_allowable_repeats); runs; max_streak
  ⍝ Obliczanie długości ciągów powtarzających się bitów w strumieniu wektorowym
  runs         ← (+ / ≠ bit_stream) ⌸ bit_stream
  max_streak   ← ⌈/ ,runs
  test_results ← max_streak ≤ max_allowable_repeats
∇

⍝ [2] Test częstotliwości jedynek w bloku wektorowym
∇ frequency_health ← vector_frequency_health_check (raw_bits expected_ratio tolerance); ones_ratio
  ones_ratio       ← (+/ raw_bits) ÷ (⍴ raw_bits)
  frequency_health ← (| ones_ratio - expected_ratio) ≤ tolerance
∇

⍝ [3] Agregacja puli entropii i wyznaczenie wskaźnika gotowości systemu
∇ pool_status ← evaluate_system_entropy_pool (entropy_matrix threshold_val); stream_health; overall_score
  stream_health ← vector_frequency_health_check¨ {⍵} collect_bits entropy_matrix 0.5 0.1
  overall_score ← (+/ stream_health) ÷ (⍴ stream_health)
  
  pool_status   ← (⊂'ready' (overall_score ≥ threshold_val)) (⊂'score' overall_score)
∇