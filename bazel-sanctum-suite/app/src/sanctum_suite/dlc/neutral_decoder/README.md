<div align="center">

  <br />
  <h1>🧠 SANCTUM-DLC-NEURAL-DECODER</h1>
  <p><b>Unavailable biometric and session-guardian placeholder</b></p>

  <p>
    <i>Dodatek nie zbiera biometrii, nie wykrywa przymusu, nie autoryzuje sesji i nie uruchamia dead-man switch.</i>
  </p>

  <p>
    <a href="#architektura-modułu"><img src="https://img.shields.io/badge/Architecture-Neural_Guardian-38bdf8?style=for-the-badge&logo=python" alt="Architecture"></a>
    <a href="#komponenty-techniczne"><img src="https://img.shields.io/badge/Security-Biometrics_%7C_Kill_Switch-f43f5e?style=for-the-badge&logo=security" alt="Security"></a>
  </p>

  <br />

</div>

---

## 🏛️ O module

**SANCTUM-DLC-NEURAL-DECODER** nie jest podsystemem ochrony tożsamości. Wyniki są oznaczane NOT_ASSESSED; brak walidowanego modelu biometrycznego i integracji sprzętowej.

---

## ⚙️ Komponenty Techniczne

<table>
  <tr>
    <td width="50%">
      <h3>1. Behavioral Biometrics</h3>
      <p><b>Plik:</b> <code>behavioral_biometrics.py</code></p>
      <ul>
        <li>NOT_ASSESSED; dane rytmu pisania nie są analizowane.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>2. Rubber-Hose Detector</h3>
      <p><b>Plik:</b> <code>rubber_hose_detector.py</code></p>
      <ul>
        <li>NOT_ASSESSED; klucze nie są zerowane ani modyfikowane.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>3. Neural Core</h3>
      <p><b>Plik:</b> <code>neural_core.py</code></p>
      <ul>
        <li>Brak działającego modelu i atestacji sesji.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>4. Orkiestrator Główny</h3>
      <p><b>Plik:</b> <code>engine.py</code></p>
      <ul>
        <li>Zwraca NOT_ASSESSED; nie zmienia stanu sesji.</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🚀 Szybki Start & Testy

Aby uruchomić testy jednostkowe wyłącznie dla tego dodatku, wykonaj w terminalu:

```bash
pytest tests/test_neural_dlc.py