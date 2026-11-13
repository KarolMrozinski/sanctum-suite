⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise Deep Vector Telemetry & Anomaly Detector (APL)
⍝ Zaawansowany, produkcyjny system korelacji przestrzennej i analizy strumieni
⍝ ==============================================================================

⍝ [1] Wieloprzebiegowe wygładzanie wykładnicze (EMA) dla macierzy telemetrii
∇ ema_matrix ← compute_enterprise_exponential_moving_average (telemetry_stream smoothing_alpha); rows; cols; t
  rows ← (⍴ telemetry_stream)[1]
  cols ← (⍴ telemetry_stream)[2]
  ema_matrix ← telemetry_stream
  
  t ← 1
  :While t < cols
    t ← t + 1
    ema_matrix[;t] ← (smoothing_alpha × telemetry_stream[;t]) + ((1 - smoothing_alpha) × ema_matrix[;t-1])
  :EndWhile
∇

⍝ [2] Kompleksowy skaning odchyleń wielowymiarowych i ocena Z-Score
∇ anomaly_report ← scan_enterprise_telemetry_matrix (telemetry_matrix sensitivity_threshold); means; stds; z_scores; detections
  means      ← (+/ telemetry_matrix) ÷ (⍴ telemetry_matrix)[1]
  stds       ← ((+/ (telemetry_matrix - means ∘.× (1 ⍴ (⍴ telemetry_matrix)[2])) * 2) ÷ (⍴ telemetry_matrix)[1]) * 0.5
  
  z_scores   ← | (telemetry_matrix - means ∘.× (1 ⍴ (⍴ telemetry_matrix)[2])) ÷ (stds ∘.× (1 ⍴ (⍴ telemetry_matrix)[2]))
  detections ← z_scores > sensitivity_threshold
  
  anomaly_report ← (⊂'detections' detections) (⊂'z_scores' z_scores) (⊂'max_deviation' (⌈/ ,z_scores))
∇

⍝ [3] Automatyczna synteza poziomu zagrożenia systemowego
∇ threat_evaluation ← evaluate_enterprise_system_threat anomaly_detections; density_ratio
  density_ratio ← (+/ +, anomaly_detections) ÷ (×/ ⍴ anomaly_detections)
  
  :If density_ratio > 0.40
    threat_evaluation ← 5 ⍝ KRYTYCZNY: Natychmiastowa izolacja węzła
  :ElseIf density_ratio > 0.25
    threat_evaluation ← 4 ⍝ WYSOKI: Wzmożony nadzór i blokada portów
  :ElseIf density_ratio > 0.10
    threat_evaluation ← 3 ⍝ ŚREDNI: Ostrzeżenie behawioralne
  :Else
    threat_evaluation ← 1 ⍝ BEZPIECZNY: Nominalny stan operacyjny
  :EndIf
∇