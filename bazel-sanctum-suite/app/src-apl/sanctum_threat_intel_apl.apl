⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Threat Intelligence & Indicator Matrix Aggregator
⍝ Masowa korelacja IoC (Indicators of Compromise) w strukturach wektorowych
⍝ ==============================================================================

⍝ [1] Wektorowe dopasowanie adresów IP i domen do baz IOC (IP Watchlist Matching)
∇ match_results ← vectorized_ioc_watchlist_lookup (observed_ips watchlist_matrix); comparison_tensor
  comparison_tensor ← observed_ips ∘.= watchlist_matrix
  match_results     ← ∨/ comparison_tensor
∇

⍝ [2] Kalkulacja zagregowanego wskaźnika reputacji węzła sieciowego
∇ node_reputation ← calculate_vectorized_node_reputation (incident_counts severity_weights decay_factors); raw_score
  raw_score       ← +/ incident_counts × severity_weights × decay_factors
  node_reputation ← 100 - (raw_score ⌊ 100) ⍝ Wynik w skali 0-100 (100 = pełne zaufanie)
∇

⍝ [3] Automatyczna prioritaryzacja alertów bezpieczeństwa w macierzy zdarzeń
∇ prioritized_matrix ← prioritize_security_event_matrix (event_vectors urgency_factors); sorted_indices
  sorted_indices     ← ⍋ event_vectors × urgency_factors
  prioritized_matrix ← event_vectors [ sorted_indices ; ]
∇