⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Automated Mitigation & Policy Synthesizer
⍝ Macierzowa synteza reguł blokady dla zapór sieciowych i mechanizmów jądra
⍝ ==============================================================================

⍝ [1] Generowanie wektora reguł blokowania dla złośliwych interfejsów
∇ mitigation_rules ← synthesize_iptables_drop_vectors offending_ips subnet_masks; base_template
  base_template    ← 'iptables -A INPUT -s '
  mitigation_rules ← base_template ,¨ offending_ips ,¨ ' -j DROP'
∇

⍝ [2] Ocena skuteczności wdrożonych kontrmrodków w czasie rzeczywistym
∇ effectiveness_report ← audit_mitigation_action_impact (pre_incident_rates post_incident_rates); reduction
  reduction            ← pre_incident_rates - post_incident_rates
  effectiveness_report ← (⊂'mitigation_successful' (all (reduction > 0))) (⊂'average_drop' ((+/ reduction) ÷ (⍴ reduction)))
∇

⍝ [3] Masowa sanitizacja i zamknięcie portów nasłuchowych w klastrze Air-Gap
∇ closed_ports_matrix ← enforce_air_gap_port_lockdown active_ports_matrix critical_whitelist_mask; lockdown_filter
  lockdown_filter     ← ~ critical_whitelist_mask
  closed_ports_matrix ← active_ports_matrix × lockdown_filter
∇