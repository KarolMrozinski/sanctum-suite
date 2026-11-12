⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Vector Stream Cipher & OFB Mode Engine
⍝ Generowanie pseudolosowego strumienia klucza i szyfrowanie operacją XOR
⍝ ==============================================================================

⍝ [1] Generowanie bloku keystream z użyciem macierzy nieliniowej
∇ keystream_block ← generate_vector_keystream (iv_vector seed_matrix rounds); state
  state           ← seed_vector ∘.+ iv_vector
  r               ← 0
  :While r < rounds
    r             ← r + 1
    state         ← 256 | state +.× seed_matrix
  :EndWhile
  keystream_block ← ,state
∇

⍝ [2] Symetryczne szyfrowanie / deszyfrowanie strumienia metodą XOR
∇ cipher_output ← execute_vector_xor_stream (plain_bytes keystream); min_len
  min_len       ← (⍴ plain_bytes) ⌊ (⍴ keystream)
  cipher_output ← (plain_bytes [⍳min_len]) ⍳ xor (keystream [⍳min_len])
∇

⍝ [3] Kompleksowa weryfikacja integralności bloku po odszyfrowaniu
∇ integrity_verified ← verify_decrypted_stream_integrity (recovered_data original_hash); computed_hash
  computed_hash      ← +/ recovered_data
  integrity_verified ← computed_hash = original_hash
∇