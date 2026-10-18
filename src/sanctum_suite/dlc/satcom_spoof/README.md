<div align="center">

  <br />
  <h1>🛰️ SANCTUM-DLC-SATCOM-SPOOF</h1>
  <p><b>Orbital Security Audit, CCSDS Telemetry Analyzer & Uplink Spoofing Simulation Module</b></p>

  <p>
    <i>Opcjonalny dodatek DLC do platformy SANCTUM-SUITE, symulujący zaawansowaną analizę dynamiki orbitalnej (efekt Dopplera), inspekcję ramek telekomunikacyjnych CCSDS oraz audyt odporności stacji naziemnych i satelitów na wstrzykiwanie komend.</i>
  </p>

  <p>
    <a href="#architektura-modułu"><img src="https://img.shields.io/badge/Architecture-Orbital_Defender-38bdf8?style=for-the-badge&logo=python" alt="Architecture"></a>
    <a href="#komponenty-techniczne"><img src="https://img.shields.io/badge/Security-CCSDS_%7C_Uplink_Spoof-f43f5e?style=for-the-badge&logo=security" alt="Security"></a>
  </p>

  <br />

</div>

---

## 🏛️ O module

**SANCTUM-DLC-SATCOM-SPOOF** to enklawa symulacyjna stworzona z myślą o audycie bezpieczeństwa infrastruktury kosmicznej (Space-Sec). Moduł modeluje warunki fizyczne łączy LEO/MEO, weryfikuje podatności na braki uwierzytelniania w standardach telemetrii CCSDS oraz symuluje ataki typu *Command Injection* i *Replay*.

---

## ⚙️ Komponenty Techniczne

<table>
  <tr>
    <td width="50%">
      <h3>1. Orbital Doppler Engine</h3>
      <p><b>Plik:</b> <code>orbital_doppler.py</code></p>
      <ul>
        <li>Obliczanie przesunięcia częstotliwości Dopplera dla satelitów LEO.</li>
        <li>Modelowanie strat ścieżki w wolnej przestrzeni (Free Space Path Loss).</li>
      </ul>
    </td>
    <td width="50%">
      <h3>2. CCSDS Telemetry Analyzer</h3>
      <p><b>Plik:</b> <code>ccsds_telemetry.py</code></p>
      <ul>
        <li>Parsowanie nagłówków ramek telekomunikacyjnych CCSDS (APID, wersja).</li>
        <li>Weryfikacja obecności kryptograficznego uwierzytelniania.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>3. Uplink Spoofing Simulation</h3>
      <p><b>Plik:</b> <code>uplink_spoofing.py</code></p>
      <ul>
        <li>Symulacja wstrzykiwania fałszywych komend sterujących (Command Injection).</li>
        <li>Ocena ryzyka dla podsystemów kontroli orientacji (ADCS).</li>
      </ul>
    </td>
    <td width="50%">
      <h3>4. Orkiestrator Główny</h3>
      <p><b>Plik:</b> <code>engine.py</code></p>
      <ul>
        <li>Koordynacja pełnego audytu bezpieczeństwa łącza satelitarnego.</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🚀 Szybki Start & Testy

Aby uruchomić testy jednostkowe wyłącznie dla tego dodatku, wykonaj w terminalu:

```bash
pytest tests/test_satcom_dlc.py