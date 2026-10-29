⍝ ==============================================================================
⍝ Sanctum Suite: High-Performance Vector Telemetry Anomaly Detector (APL)
⍝ Błyskawiczna analiza odchyłek behawioralnych w strumieniach danych
⍝ ==============================================================================

⍝ [1] Główna funkcja wykrywania anomalii w macierzy telemetrii
∇ anomalies ← detect_telemetry_anomalies (telemetry_matrix threshold); means; variance; std_dev; diffs
  ⍝ Wiersze: metryki systemowe, Kolumny: próbki czasowe
  means ← (+/ telemetry_matrix) ÷ (⍴ telemetry_matrix)[1]
  
  ⍝ Obliczenie wariancji wektorowej
  variance ← (+/ (telemetry_matrix - means ∘.× (1 ⍴ (⍴ telemetry_matrix)[2])) * 2) ÷ (⍴ telemetry_matrix)[1]
  std_dev ← variance * 0.5
  
  ⍝ Wyznaczenie odchyleń bezwzględnych od normy
  diffs ← | telemetry_matrix - means ∘.× (1 ⍴ (⍴ telemetry_matrix)[2])
  
  ⍝ Maska binarna anomalii przekraczających zadany próg krytyczny
  anomalies ← diffs > (threshold × std_dev ∘.× (1 ⍴ (⍴ telemetry_matrix)[2]))
∇

⍝ [2] Kalkulacja zagregowanego wskaźnika ryzyka (Risk Score Aggregator)
∇ risk_index ← calculate_aggregate_risk anomaly_mask; weights; total_cells
  total_cells ← ×/ ⍴ anomaly_mask
  weights ← (⍴ anomaly_mask)[1] ⍴ 1.5 2.0 3.0 5.0 ⍝ Wagi krytyczności warstw
  risk_index ← (+/ +, anomaly_mask) ÷ total_cells
∇

⍝ [3] Filtr czyszczący szumy w strumieniu telemetrii
∇ filtered_stream ← purge_telemetry_noise (raw_stream noise_floor); mask
  mask ← raw_stream > noise_floor
  filtered_stream ← mask × raw_stream
∇