⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Vector DDoS Guard & Traffic Burst Mitigator
⍝ Błyskawiczna analiza uderzeń masowych pakietów i dynamiczne dławienie pasma
⍝ ==============================================================================

⍝ [1] Obliczanie dynamicznych wskaźników natężenia ruchu w oknie czasowym
∇ burst_indicators ← analyze_traffic_burst_matrix (packet_rate_matrix baseline_average multiplier); threshold
  threshold        ← baseline_average × multiplier
  burst_indicators ← packet_rate_matrix > threshold
∇

⍝ [2] Dynamiczna synteza reguł ograniczania prędkości (Rate Limiting Matrix)
∇ throttled_rates ← synthesize_rate_limiting_matrix (current_rates burst_mask safety_limit); reduction_factor
  reduction_factor ← burst_mask × (current_rates ÷ 4)
  throttled_rates  ← (current_rates - reduction_factor) ⌈ safety_limit
∇

⍝ [3] Globalny audyt stabilności interfejsu sieciowego pod presją ataku
∇ ddos_audit_summary ← audit_cluster_ddos_resistance (burst_vector drop_stats_vector); severity_index
  severity_index     ← (+/ burst_vector) ÷ (⍴ burst_vector)
  ddos_audit_summary ← (⊂'attack_detected' (severity_index > 0.25)) (⊂'severity_index' severity_index) (⊂'total_dropped' (+/ drop_stats_vector))
∇