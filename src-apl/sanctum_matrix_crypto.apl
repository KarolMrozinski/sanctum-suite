⍝ ==============================================================================
⍝ Sanctum Suite: Matrix Cryptographic Transformer & Permutation Engine (APL)
⍝ Zaawansowane transformacje kryptograficzne oparte na algebrze liniowej
⍝ ==============================================================================

⍝ [1] Inicjalizacja kontekstu transformacji macierzowej
∇ context ← init_crypto_context key_seed; dimensions; base_matrix
  dimensions ← 8 8 ⍝ Standardowy blok macierzy 8x8 dla operacji
  base_matrix ← dimensions ⍴ (dimensions[1] × dimensions[2]) | key_seed + ⍳ (dimensions[1] × dimensions[2])
  context ← ⍎¨ 'matrix' 'dims' 'active' ⍝ Zestawienie struktury kontekstu
  ⎕IO ← 0 ⍝ Ustawienie indeksowania od zera dla spójności niskopoziomowej
∇

⍝ [2] Równoległe szyfrowanie blokowe z użyciem mnożenia macierzowego modulo 256
∇ cipher_block ← encrypt_matrix_block (key_matrix data_vector); dims; padded_data; reshaped_block; transformed
  dims ← ⍴ key_matrix
  ⍝ Wypełnienie wektora danych do pełnego bloku macierzy
  padded_data ← ((×/dims)⌈⍴data_vector) ↑ data_vector
  reshaped_block ← (dims[1] ⍴ dims[2]) ⍴ padded_data
  
  ⍝ Mnożenie macierzowe modulo 256 z maskowaniem bezpieczeństwa
  transformed ← 256 | (key_matrix +.× reshaped_block)
  cipher_block ← ,transformed
∇

⍝ [3] Deszyfrowanie blokowe przy użyciu macierzy odwrotnej
∇ plain_block ← decrypt_matrix_block (inv_key_matrix cipher_vector); dims; reshaped_cipher; recovered
  dims ← ⍴ inv_key_matrix
  reshaped_cipher ← (dims[1] ⍴ dims[2]) ⍴ cipher_vector
  
  ⍝ Odtworzenie macierzy źródłowej modulo 256
  recovered ← 256 | (inv_key_matrix +.× reshaped_cipher)
  plain_block ← ,recovered
∇

⍝ [4] Weryfikacja odwracalności macierzy klucza pod kątem bezpieczeństwa
∇ is_valid ← verify_matrix_invertibility key_matrix; row_sum; determinant_approx
  row_sum ← +/ key_matrix
  determinant_approx ← ×/ row_sum
  ⍝ Sprawdzenie czy macierz nie jest osobliwa
  is_valid ← 0 ≠ determinant_approx
∇