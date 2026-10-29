⍝ ==============================================================================
⍝ Sanctum Suite: Enterprise APL Vector Neural Network Classifier & Threat Matrix
⍝ Macierzowa implementacja warstw perceptronowych do klasyfikacji anomalii w tle
⍝ ==============================================================================

⍝ [1] Funkcja aktywacji nieliniowej (Sigmoid Vector Activation)
∇ activated ← vector_sigmoid_activation weights_matrix; exp_vals
  exp_vals  ← * (- weights_matrix)
  activated ← 1 ÷ (1 + exp_vals)
∇

⍝ [2] Przetwarzanie warstwy ukrytej sieci neuronowej (Forward Propagation)
∇ layer_output ← forward_propagate_neural_layer (input_vector weights bias_vector); linear_mix
  linear_mix   ← (weights +.× input_vector) + bias_vector
  layer_output ← vector_sigmoid_activation linear_mix
∇

⍝ [3] Główny klasyfikator zagrożeń oparty na strukturze perceptronu wielowarstwowego
∇ threat_classification ← classify_telemetry_vector_mlp (telemetry_vector w1 w2 b1 b2); hidden_layer
  hidden_layer          ← forward_propagate_neural_layer telemetry_vector w1 b1
  threat_classification ← forward_propagate_neural_layer hidden_layer w2 b2
∇