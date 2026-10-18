<div align="center">

  <br />
  <h1>🧠 SANCTUM-DLC-NEURAL-DECODER</h1>
  <p><b>Behavioral Biometrics, Rubber-Hose Cryptanalysis Defense & Neural Session Guardian</b></p>

  <p>
    <i>Opcjonalny dodatek DLC do platformy SANCTUM-SUITE, monitorujący dynamikę klawiatury operatora, wykrywający przymus fizyczny (Rubber-Hose Cryptanalysis) i automatycznie wyzwalający Dead-Man's Switch w przypadku zagrożenia.</i>
  </p>

  <p>
    <a href="#architektura-modułu"><img src="https://img.shields.io/badge/Architecture-Neural_Guardian-38bdf8?style=for-the-badge&logo=python" alt="Architecture"></a>
    <a href="#komponenty-techniczne"><img src="https://img.shields.io/badge/Security-Biometrics_%7C_Kill_Switch-f43f5e?style=for-the-badge&logo=security" alt="Security"></a>
  </p>

  <br />

</div>

---

## 🏛️ O module

**SANCTUM-DLC-NEURAL-DECODER** to zaawansowany podsystem ochrony tożsamości i sesji uprzywilejowanych. Analizując biometrię behawioralną oraz wykrywając anomalie wywołane stresem lub przymusem, chroni enklawę przed przejęciem konta.

---

## ⚙️ Komponenty Techniczne

<table>
  <tr>
    <td width="50%">
      <h3>1. Behavioral Biometrics</h3>
      <p><b>Plik:</b> <code>behavioral_biometrics.py</code></p>
      <ul>
        <li>Analiza opóźnień między naciśnięciami klawiszy (Keystroke Dynamics).</li>
      </ul>
    </td>
    <td width="50%">
      <h3>2. Rubber-Hose Detector</h3>
      <p><b>Plik:</b> <code>rubber_hose_detector.py</code></p>
      <ul>
        <li>Wykrywanie przymusu i automatyczne zerowanie kluczy (Kill-Switch).</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>3. Neural Core</h3>
      <p><b>Plik:</b> <code>neural_core.py</code></p>
      <ul>
        <li>Lekki model decyzyjny oceniający entropię sesji.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>4. Orkiestrator Główny</h3>
      <p><b>Plik:</b> <code>engine.py</code></p>
      <ul>
        <li>Koordynacja analizy behawioralnej i zarządzanie stanem zagrożenia.</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🚀 Szybki Start & Testy

Aby uruchomić testy jednostkowe wyłącznie dla tego dodatku, wykonaj w terminalu:

```bash
pytest tests/test_neural_dlc.py