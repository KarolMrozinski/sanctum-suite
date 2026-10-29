⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Network Packet Inspector & Firewall Engine
⍝ Analiza nagłówków ramek sieciowych, ocena portów i detekcja prób skanowania
⍝ ==============================================================================

⍝ [1] Walidacja przestrzeni adresów IP pod kątem restrykcyjnych reguł Air-Gap
∇ compliance_mask ← validate_air_gap_ip_matrix (ip_octets_matrix strict_mode); is_local
  ⍝ Kolumny: [Octet1, Octet2, Octet3, Octet4]
  ⍝ Sprawdzenie podsieci prywatnych (10.x.x.x, 192.168.x.x, 172.16-31.x.x, 127.x.x.x)
  is_local ← (ip_octets_matrix[;0] = 10) ∨ \
             ((ip_octets_matrix[;0] = 192) ∧ (ip_octets_matrix[;1] = 168)) ∨ \
             ((ip_octets_matrix[;0] = 172) ∧ (ip_octets_matrix[;1] ≥ 16) ∧ (ip_octets_matrix[;1] ≤ 31)) ∨ \
             (ip_octets_matrix[;0] = 127)
  
  :If strict_mode
    compliance_mask ← is_local ⍝ W trybie ścisłym dopuszczalny tylko ruch lokalny
  :Else
    compliance_mask ← (1 ⍴ ⍴ip_octets_matrix)[1] ⍴ 1 ⍝ Tryb otwarty
  :EndIf
∇

⍝ [2] Wykrywanie anomalii portów i prób skanowania typu SYN/Xmas Scan
∇ threat_indicators ← inspect_port_behavior_matrix (source_ports destination_ports flags_vector); invalid_ports
  invalid_ports     ← (source_ports > 65535) ∨ (destination_ports > 65535) ∨ (source_ports = 0)
  ⍝ Detekcja flag SYN+FIN (Xmas/Null scan indicators)
  threat_indicators ← invalid_ports ∨ (flags_vector = 3) ∨ (flags_vector = 0)
∇

⍝ [3] Główna funkcja decyzyjna firewalla wektorowego
∇ firewall_actions ← process_vectorized_firewall_decisions (ip_matrix src_ports dst_ports flags strict_flag); ip_check; port_check
  ip_check   ← validate_air_gap_ip_matrix ip_matrix strict_flag
  port_check ← inspect_port_behavior_matrix src_ports dst_ports flags
  
  ⍝ Decyzja: 1 = ALLOW, 0 = DROP / QUARANTINE
  firewall_actions ← ip_check ∧ (~port_check)
∇