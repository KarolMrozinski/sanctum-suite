<div align="center">

# SANCTUM-SUITE

### Modułowy zestaw narzędzi do inżynierii bezpieczeństwa

Narzędzia CLI, API i dashboard wspierające wybrane procesy audytowe, analizę danych oraz eksperymenty z AI safety.

<p>
  <img src="https://img.shields.io/badge/wersja-6.0.0-2563eb?style=flat-square" alt="Wersja 6.0.0">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/dashboard-Next.js-111827?style=flat-square&logo=nextdotjs&logoColor=white" alt="Dashboard Next.js">
  <img src="https://img.shields.io/badge/status-beta-f59e0b?style=flat-square" alt="Status beta">
  <img src="https://img.shields.io/badge/licencja-source--available-64748b?style=flat-square" alt="Licencja source-available">
</p>

[Instalacja](./docs/INSTALLATION.md) ·
[Katalog kontroli](./docs/CONTROL_CATALOG.md) ·
[Bezpieczeństwo](./SECURITY.md) ·
[Licencja](./LICENSE)

</div>

---

## O projekcie

SANCTUM-SUITE to rozwijany zestaw modułów programistycznych przeznaczonych do pracy w kontrolowanych, zatwierdzonych środowiskach. Repozytorium łączy narzędzia wiersza poleceń, API, funkcje analityczne i opcjonalny dashboard.

Projekt ma status **beta**. Zakres, dojrzałość i wymagania zależą od konkretnego modułu. Obecność funkcji w repozytorium nie oznacza, że została niezależnie zweryfikowana, jest gotowa do wdrożenia produkcyjnego ani zapewnia zgodność z określonym standardem.

## Możliwości

- **Audyt i testy** — wybrane, jawnie autoryzowane testy HTTPS/TCP z kontrolą dozwolonych celów.
- **Analiza i korelacja** — przetwarzanie zdarzeń, analityka oraz pomocnicze narzędzia do raportowania.
- **AI safety** — moduły do analizy promptów i eksperymentów z zabezpieczeniami modeli.
- **Interfejsy** — CLI w Pythonie, REST API i WebSocket oraz osobny dashboard oparty na Next.js.
- **Kontrole i entitlementy** — mapowanie kontroli oraz weryfikacja podpisanych uprawnień do użycia.

### Ważne ograniczenia

Część modułów jest eksperymentalna, zależna od platformy lub stanowi jedynie punkt integracji. Repozytorium nie dostarcza działających integracji dla skanowania kontenerów/SBOM, analizy firmware i pamięci, telemetrii EDR/XDR, inspekcji GPU, sprzętowych enklaw ani magazynowania danych niejawnych. Funkcje kampanii red-team, C2/covert-channel, spoofingu satelitarnego, biometrii, hot-patchingu i dead-man switch nie wykonują opisanych działań. Brak integracji jest raportowany jako brak oceny, a nie jako pozytywny wynik.

Dashboard nie otrzymuje obecnie rzeczywistej telemetrii z endpointu workbench. Pomocnicze szyfrowanie kopertowe `ZeroTrustKMSVault` wykorzystuje klucz efemeryczny przechowywany w pamięci procesu i **nie zastępuje produkcyjnego KMS**.

## Szybki start

> **Uwaga licencyjna:** przed instalacją, uruchomieniem, modyfikacją lub wdrożeniem uzyskaj wymaganą pisemną zgodę właściciela praw. Licencja repozytorium pozwala na wgląd w kod w celach oceny, edukacyjnych lub code review; nie przyznaje ogólnego prawa do jego wykonywania ani użycia komercyjnego.

### Wymagania

- Python 3.11 lub nowszy
- Node.js i npm — tylko jeśli instalujesz dashboard
- Pisemna zgoda na użycie programu oraz osobna autoryzacja każdego testowanego celu

### Instalacja pakietu Python

Po uzyskaniu wymaganej zgody, w katalogu głównym repozytorium:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Sprawdzenie dostępnych poleceń i testy:

```powershell
sanctum --help
python -m pytest -q
```

### Dashboard (opcjonalnie)

```powershell
Set-Location .\sanctum-dashboard
npm ci
Copy-Item .env.example .env.local
npm run build
npm run start
```

Szczegóły konfiguracji API, TLS, sekretów i dashboardu opisuje [przewodnik instalacji](./docs/INSTALLATION.md).

## Użycie aktywnych testów

Aktywne audyty i skanowanie portów są blokowane, dopóki operator nie skonfiguruje wszystkich wymaganych elementów:

1. dokładnej listy dozwolonych celów w `SANCTUM_AUTHORIZED_TARGETS` — bez wildcardów;
2. identyfikatora pisemnej zgody przekazywanego przy uruchomieniu;
3. ważnego, podpisanego entitlementu oraz klucza publicznego do jego weryfikacji.

Przykładowe polecenie dla celu znajdującego się na skonfigurowanej liście i objętego ważną zgodą:

```powershell
sanctum run-audit --target zatwierdzony.example --authorization-reference "identyfikator-zgody"
```

Wartość `--authorization-reference` służy operatorowi do prowadzenia śladu audytowego — sama w sobie nie potwierdza zgody. Nie uruchamiaj testów wobec systemów spoza zatwierdzonego zakresu. Więcej informacji o uprawnieniach znajduje się w [dokumentacji entitlementów](./docs/COMMERCIAL_ENTITLEMENTS.md).

## Architektura

Diagram przedstawia orientacyjny podział obszarów repozytorium, a nie gwarantowany przepływ danych ani wdrożony układ infrastruktury.

```mermaid
flowchart LR
    T["Zatwierdzone środowisko testowe"] --> A["Moduły audytowe"]
    A --> C["Korelacja i analityka"]
    AI["Analiza AI safety"] --> C
    C --> R["Raporty"]
    P["Moduły zależne od platformy"] -. opcjonalnie .-> C
    API["REST API / WebSocket"] --> D["Dashboard Next.js"]
```

## Dokumentacja

| Dokument | Opis |
|---|---|
| [Instalacja i wdrożenie](./docs/INSTALLATION.md) | Konfiguracja środowiska, API, dashboardu i wymagania wdrożeniowe |
| [Katalog kontroli](./docs/CONTROL_CATALOG.md) | Opis mapowanych kontroli |
| [Entitlementy komercyjne](./docs/COMMERCIAL_ENTITLEMENTS.md) | Podpisane uprawnienia, zakres i limity |
| [Polityka bezpieczeństwa](./SECURITY.md) | Zgłaszanie problemów bezpieczeństwa |
| [Lista kontrolna wydania](./docs/RELEASE_CHECKLIST.md) | Czynności przed wydaniem |
| [Informacje o wydaniu 6.0.0](./docs/RELEASE_NOTES_v6.0.0.md) | Zmiany w bieżącej wersji |
| [Changelog](./CHANGELOG.md) | Historia zmian |
| [Licencja](./LICENSE) | Warunki dostępu i użycia |

## Status wdrożeniowy

Repozytorium zawiera materiały do instalacji i wydania, ale **nie jest to potwierdzenie gotowości produkcyjnej**. Przed wdrożeniem należy zweryfikować zachowanie, uprawnienia i zależności każdego używanego modułu oraz przygotować właściwe zabezpieczenia środowiska.

Licencja nie zezwala na komercyjne użycie bez odrębnej pisemnej zgody. W repozytorium nie ma gotowej integracji płatności, unieważniania entitlementów online, izolacji danych klientów ani wdrożonego SLA. Formularz kontaktowy wymaga skonfigurowania zatwierdzonego webhooka. Build, testy i dokumentacja nie stanowią certyfikacji bezpieczeństwa, zgodności ani gwarancji skuteczności.

## Licencja

SANCTUM-SUITE jest udostępniany na warunkach ograniczonej licencji source-available. Przed jakimkolwiek użyciem zapoznaj się z pełnym tekstem pliku [LICENSE](./LICENSE) i uzyskaj pisemną zgodę, jeśli jest wymagana.
