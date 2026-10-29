⍝ ==============================================================================
⍝ Sanctum Suite: Network Topology & Air-Gap Isolation Matrix Analyzer (APL)
⍝ Macierzowa analiza grafu połączeń w poszukiwaniu ukrytych wycieków danych
⍝ ==============================================================================

⍝ [1] Obliczanie macierzy osiągalności w grafie sieci (Reachability Matrix Closure)
∇ closure_matrix ← compute_network_reachability adjacency_matrix; n; current_power; next_power
  n              ← (⍴ adjacency_matrix)[1]
  closure_matrix ← adjacency_matrix > 0
  current_power  ← adjacency_matrix
  
  ⍝ Potęgowanie macierzy w algebrze Boole'a dla wyznaczenia ścieżek
  k ← 1
  :While k < n
    k             ← k + 1
    current_power ← current_power +.× adjacency_matrix
    closure_matrix ← closure_matrix ∨ (current_power > 0)
  :EndWhile
∇

⍝ [2] Wykrywanie niedozwolonych mostków izolacyjnych (Bridge Leak Detection)
∇ leak_report ← audit_air_gap_topology_bridges (adjacency_matrix internal_nodes external_nodes); reach_matrix; violations
  reach_matrix  ← compute_network_reachability adjacency_matrix
  
  ⍝ Sprawdzenie czy węzły wewnętrzne mają ścieżkę do węzłów zewnętrznych
  violations    ← reach_matrix [internal_nodes; external_nodes]
  
  leak_report   ← (⊂'secure_isolation' (0 = +/ ,violations)) (⊂'violated_links' violations)
∇