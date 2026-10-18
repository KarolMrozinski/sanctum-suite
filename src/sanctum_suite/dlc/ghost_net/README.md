<div align="center">

  <br />
  <h1>👻 SANCTUM-DLC-GHOST-NET</h1>
  <p><b>Decentralized P2P C2 Simulation, DGA & Covert Channel Exfiltration Module</b></p>

  <p>
    <i>Opcjonalny dodatek DLC do platformy SANCTUM-SUITE, symulujący zaawansowane, odporne na cenzurę sieci dowodzenia i kontroli (C2), routing cebulowy oraz ukryte kanały eksfiltracji danych (DNS/ICMP Tunneling).</i>
  </p>

  <p>
    <a href="#architektura-modułu"><img src="https://img.shields.io/badge/Architecture-P2P_Mesh_C2-38bdf8?style=for-the-badge&logo=python" alt="Architecture"></a>
    <a href="#komponenty-techniczne"><img src="https://img.shields.io/badge/Security-Covert_Channels_%7C_DGA-f43f5e?style=for-the-badge&logo=security" alt="Security"></a>
  </p>

  <br />

</div>

---

## 🏛️ O module

**SANCTUM-DLC-GHOST-NET** to enklawa symulacyjna stworzona do testowania zdolności wykrywania ukrytych kanałów komunikacyjnych, odporności infrastruktury sieciowej na protokoły tunelujące oraz analizy zachowań zaawansowanych sieci C2 (Command and Control) w środowiskach o wysokim ryzyku inwigilacji.

---

## ⚙️ Komponenty Techniczne

<table>
  <tr>
    <td width="50%">
      <h3>1. P2P Mesh & Onion Routing</h3>
      <p><b>Plik:</b> <code>p2p_mesh.py</code></p>
      <ul>
        <li>Zdecentralizowana sieć przekaźnikowa P2P.</li>
        <li>Wielowarstwowy routing cebulowy (Onion Layers).</li>
        <li>Szyfrowanie transportowe ChaCha20-Poly1305.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>2. DGA & Fast Flux</h3>
      <p><b>Plik:</b> <code>dga_fast_flux.py</code></p>
      <ul>
        <li>Dynamiczne generowanie algorytmicznych domen (Domain Generation Algorithms).</li>
        <li>Rotacja adresów i węzłów brzegowych.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>3. Covert Channels Exfiltration</h3>
      <p><b>Plik:</b> <code>covert_channels.py</code></p>
      <ul>
        <li>Tunelowanie danych przez zapytania DNS.</li>
        <li>Eksfiltracja pakietów w protokole ICMP z maskowaniem TTL.</li>
      </ul>
    </td>
    <td width="50%">
      <h3>4. Orkiestrator Główny</h3>
      <p><b>Plik:</b> <code>engine.py</code></p>
      <ul>
        <li>Koordynacja całej symulacji ruchu C2 i generowanie telemetrii.</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🚀 Szybki Start & Testy

Aby uruchomić testy jednostkowe wyłącznie dla tego dodatku, wykonaj w terminalu:

```bash
pytest tests/test_ghost_net_dlc.py