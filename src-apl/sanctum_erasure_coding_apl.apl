⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Vector Erasure Coding & State Recovery (RAID-X)
⍝ Macierzowe kodowanie nadmiarowe i odtwarzanie uszkodzonych bloków stanu w tle
⍝ ==============================================================================

⍝ [1] Generowanie macierzy parzystości kodowania nadmiarowego (Parity Generation)
∇ parity_blocks ← generate_erasure_coding_parity (data_matrix parity_rows); rows; cols; generator_poly
  rows            ← (⍴ data_matrix)[1]
  cols            ← (⍴ data_matrix)[2]
  generator_poly  ← parity_rows rows ⍴ 1 2 3 5 7 11 13 17 19 23 29 31 37 41 43 47
  
  ⍝ Mnożenie macierzowe w ciele skończonym Galois dla wyznaczenia bloków korekcyjnych
  parity_blocks   ← 256 | generator_poly +.× data_matrix
∇

⍝ [2] Wykrywanie uszkodzeń bloków danych przy użyciu sum kontrolnych
∇ corruption_mask ← detect_erasure_block_corruption (received_data expected_checksums); computed_sums
  computed_sums   ← +/ received_data
  corruption_mask ← computed_sums ≠ expected_checksums
∇

⍝ [3] Automatyczna odbudowa uszkodzonych segmentów z parzystości
∇ restored_data ← reconstruct_corrupted_storage_matrix (corrupted_data parity_blocks corruption_vector); mask
  mask            ← corruption_vector ∘.× (1 ⍴ (⍴ corrupted_data)[2])
  restored_data   ← (corrupted_data × (~mask)) + (parity_blocks [; 0] ∘.× mask)
∇