<div align="center">

  <br />
  <h1>🧩 SANCTUM-DLC-CICADA-3301</h1>
  <p><b>Advanced Cypherpunk Security Challenge, Steganography & Gamification Module</b></p>

  <p>
    <i>Izolowany, opcjonalny podsystem rozszerzający platformę SANCTUM-SUITE o mechanizmy kryptograficzne inspirowane Cicada 3301, Notpron, The Primroses, szyframi książkowymi oraz systemami śledzenia APT.</i>
  </p>

  <p>
    <a href="#architektura-modułu"><img src="https://img.shields.io/badge/Architecture-Modular_DLC-38bdf8?style=for-the-badge&logo=python" alt="Architecture"></a>
    <a href="#komponenty-kryptograficzne"><img src="https://img.shields.io/badge/Crypto-Pipeline_%7C_LSB-f43f5e?style=for-the-badge&logo=security" alt="Crypto"></a>
  </p>

  <br />

</div>

---

## 🏛️ O module

**SANCTUM-DLC-CICADA-3301** to zaawansowana warstwa gamifikacji i operacyjnego testowania kognitywnego. Moduł działa w całkowitej izolacji od głównego orkiestratora, służąc jako:
* Poligon treningowy i test rekrutacyjny dla inżynierów Red Team.
* System testowania odporności psychologicznej i zdolności analitycznych operatorów.
* Niski poziom eksperymentalnych algorytmów kryptograficznych i stenograficznych.

---

## ⚙️ Komponenty Modułu

<table>
  <tr>
    <td width="50%">
      <h3>1. Crypto Pipeline Engine</h3>
      <p><b>Plik:</b> <code>crypto_pipeline.py</code></p>
      <ul>
        <li>Wielopasmowe transformacje ROT.</li>
        <li>Dynamiczny byte-level XOR z kluczami generowanymi z ciągów Fibonacciego i liczb pierwszych.</li>
        <li>Bezpieczne porównania stałoczasowe (<i>constant-time</i>) chroniące przed atakami czasowymi (Timing Attacks).</li>
      </ul>
    </td>
    <td width="50%">
      <h3>2. LSB Steganography Engine</h3>
      <p><b>Plik:</b> <code>steganography.py</code></p>
      <ul>
        <li>Ukrywanie ładunków binarnych w najmniej znaczących bitach (LSB) buforów nośnych.</li>
        <li>Wbudowane nagłówki z magicznymi bajtami i sumą kontrolną CRC32 gwarantujące integralność danych.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>3. Book Cipher Utility</h3>
      <p><b>Plik:</b> <code>book_cipher.py</code></p>
      <ul>
        <li>Mapowanie sekretnych wiadomości na indeksy (linia, słowo) względem osadzonego manifestu literackiego.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>4. State Machine & Telemetry</h3>
      <p><b>Plik:</b> <code>state_machine.py</code></p>
      <ul>
        <li>Bezpieczny menedżer stanu oparty na izolowanej bazie SQLite wewnątrz katalogu DLC.</li>
        <li>Logowanie telemetrii sesji bez zapisywania wrażliwych kluczy w jawnym tekście.</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🚀 Szybki Start & Testy

Aby uruchomić testy jednostkowe wyłącznie dla tego dodatku, wykonaj w terminalu:

```bash
pytest src/sanctum_suite/tests/test_cicada_dlc.py