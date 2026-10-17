# 🏛️ SANCTUM-SUITE: Enterprise Cyber Resilience & AI Safety Platform

[![Architecture](https://img.shields.io/badge/architecture-Modular%20%7C%20Enterprise%20Grade-darkblue)](#)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![Containers](https://img.shields.io/badge/container-CVE%20Scanner-blue)](#)
[![Queue](https://img.shields.io/badge/queue-Async%20Task%20Manager-purple)](#)
[![SDK](https://img.shields.io/badge/SDK-Python%20Client-teal)](#)
[![Compliance](https://img.shields.io/badge/compliance-EU%20AI%20Act%20%7C%20NIS2%20%7C%20ISO%2027001-gold)](#)
[![Attack Graph](https://img.shields.io/badge/graph-NetworkX%203D%20UI-orange)](#)
[![Frontend](https://img.shields.io/badge/frontend-Next.js%2014%20%7C%20React-black)](#)
[![AI Security](https://img.shields.io/badge/AI%20Red--Teaming-Multi--Turn%20%26%20Multimodal-purple)](#)
[![GitHub API](https://img.shields.io/badge/GitHub-Automated%20PRs-black)](#)
[![Detection](https://img.shields.io/badge/rules-Sigma%20%7C%20YARA-red)](#)
[![Self-Healing](https://img.shields.io/badge/remediation-Automated%20Patching-emerald)](#)
[![Framework](https://img.shields.io/badge/framework-MITRE%20ATT%26CK%20%7C%20ATLAS-orange)](#)
[![Docker](https://img.shields.io/badge/docker-Ready-blue)](#)
[![API](https://img.shields.io/badge/API-FastAPI%20%7C%20Secured-teal)](#)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-green)](#)
[![License](https://img.shields.io/badge/license-View--Only-orange)](#)

> **SANCTUM-SUITE** to zintegrowana, wielomodułowa platforma bezpieczeństwa klasy Enterprise. Łączy rozpoznanie powierzchni ataku (**SPECTRE-OSINT**), wielostopniowy oraz multimodalny Red-Teaming modeli LLM/Vision (**Multimodal & Multi-Turn Adaptive Fuzzer** / **SHADOW-AGENT**), skaner kontenerów Docker pod kątem podatności CVE (**Docker Container CVE Analyzer**), asynchroniczną kolejkę zadań audytowych (**Async Task Queue Manager**), silnik audytu zgodności (**EU AI Act, NIS2 & ISO 27001 Compliance Engine**), modelowanie i wizualizację grafów ataków (**Attack Graph Engine & UI**), dedykowane **Python Client SDK (`sanctum-client`)**, samoleczącą się sieć P2P Zero-Trust (**GHOST-COMM**), automatyczne otwieranie Pull Requestów na GitHubie (**GitHub Auto-PR Publisher**), zarządcze uprawnienia **RBAC & Multi-Tenancy**, rozproszoną szynę zdarzeń (**Distributed Event Bus**), automatyczne generowanie poprawek kodu (**Self-Healing Code PRs**), asynchroniczny skaner portów/usług, silnik korelacji zagrożeń z mapowaniem **MITRE ATT&CK/ATLAS**, automatyczne scenariusze naprawcze (Playbooks), generator reguł detekcyjnych **Sigma & YARA**, silnik detekcji anomalii oparty o heurystykę i entropię tekstu (**ML Anomaly Detection**), ochronne middleware **LLM Guardrail Proxy**, integrację **SIEM/CEF**, pasywny **Honeypot Sensor**, dedykowany pulpit webowy w **Next.js / React**, kryptograficzne podpisywanie raportów RSA oraz serwer **REST API / WebSockets** (`FastAPI` + `X-API-Key`).

---

## ⚡ Kluczowe Moduły i Funkcjonalności Systemu

- **Docker Container CVE Analyzer:** Skaner natywny analizujący pliki rejestru i paczki w kontenerach pod kątem wykrytych podatności CVE.
- **Async Task Queue Manager:** Kolejkowanie i asynchroniczne wykonywanie wielogodzinnych audytów w tle bez blokowania wątków API.
- **Attack Graph Visualizer (Next.js Component):** Dedykowana wizualizacja grafowa w panelu React przedstawiająca zależności między podatnościami, otwartymi usługami i celek ataku.
- **Regulatory Compliance Engine (EU AI Act, NIS2, ISO 27001):** Automatyczna ewaluacja wymogów bezpieczeństwa sztucznej inteligencji, zarządzania ryzykiem i kontroli technicznych.
- **Python Client SDK (`sanctum-client`):** Lekki pakiet kliencki pozwalający na łatwą integrację dowolnej aplikacji zewnętrznej z serwerem API SANCTUM-SUITE dwoma linijkami kodu.
- **SPECTRE-OSINT & Async Probing:** Pasywna agregacja aktywów cyfrowych, asynchroniczne sondowanie nagłówków i certyfikatów (`httpx` + `asyncio`).
- **Async Port & Service Scanner:** Błyskawiczny, wielowiątkowy skaner otwartych portów TCP (SSH, HTTP, HTTPS, DB, Ollama API).
- **Multimodal & Multi-Turn AI Red-Teaming:** Fuzzer symulujący ukryte wstrzyknięcia w obrazach (*Visual Prompt Injection*) oraz wielostopniowe ataki konwersacyjne.
- **GitHub Automated Pull Request Publisher:** Automatyczne zakładanie gałęzi i zgłaszanie Pull Requestów naprawczych na GitHubie po wykryciu podatności.
- **RBAC & Multi-Tenancy Layer:** Zarządzanie kontrolą dostępów (`ADMIN`, `AUDITOR`, `VIEWER`) i izolacją danych wielu organizacji.
- **Automated Self-Healing Code Patcher:** Silnik generujący gotowe łatki kodu (Unified Diffs) oraz propozycje Pull Requestów naprawiających zidentyfikowane podatności.
- **Distributed Telemetry Event Bus:** Rozproszona magistrala zdarzeń (kompatybilna z wzorcem Kafka/RabbitMQ) umożliwiająca asynchroniczną komunikację klastrów skanujących.
- **Enterprise Web Dashboard (Next.js / React):** Nowoczesny pulpit nawigacyjny SOC Workbench wizualizujący metryki ryzyka oraz żywy strumień telemetrii przez WebSockets.
- **LLM Guardrail Proxy & ML Anomaly Detection:** Inspection proxy filtrujące złośliwe prompty z analizą entropii tekstu i oceną anomalii w czasie rzeczywistym.
- **Detection Rules Generator (Sigma & YARA):** Automatyczna synteza natywnych reguł **Sigma** (dla SIEM) i **YARA** (dla skanowania logów/pamięci) na podstawie wykrytych podatności.
- **SIEM / SOAR Exporter:** Formatowanie telemetryczne w standardzie **CEF (Common Event Format)** oraz powiadomienia HTTP Webhook.
- **Decoy Honeypot Sensor:** Pasywna pułapka sieciowa emulująca wrażliwe usługi do przechwytywania nieautoryzowanych prób skanowania.
- **GHOST-COMM Mesh & Remediation:** Bezpieczne pakowanie alertów w szyfrowane koperty P2P (AES-256-GCM) oraz zapasowy routing Zero-Trust.
- **Threat Correlation & MITRE ATT&CK/ATLAS:** Wykrywanie złożonych łańcuchów ataku (*Attack Chains*) oraz taksonomia zagrożeń wg standardu **MITRE ATT&CK** i **MITRE ATLAS**.
- **Remediation Playbook Engine:** Automatyczne generowanie skryptów hardeningowych (reguły `iptables`, polityki WAF i rekomendacje dla guardraili LLM).
- **Cryptographic Report Signing:** Kryptograficzny stempel integralności raportów PDF/HTML przy użyciu kluczy **RSA-2048** (pliki `.sig`).
- **Secured REST & WebSockets API:** Asynchroniczny serwer API z obsługą nagłówków `X-API-Key`, interaktywną dokumentacją Swagger UI oraz strumieniowaniem alertów w czasie rzeczywistym.
- **OLAP Analytics & Persistence:** Trwała analityka wariancji ryzyka w **DuckDB** oraz archiwizacja audytów w **SQLite**.
- **Executive Reporting & Live TUI:** Podpisane cyfrowo raporty zgodności dla zarządu (**PDF** / **HTML**) oraz pełnoekranowy pulpit **Rich Live TUI Dashboard**.
- **Enterprise Containerization & CI/CD:** Gotowy plik `Dockerfile` + `docker-compose.yml` oraz automatyczny potok testowy w **GitHub Actions**.

---

## 🏗️ Pełna Architektura Przepływu Audytowego

```mermaid
graph TD
    classDef core fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef module fill:#1e293b,stroke:#cbd5e1,stroke-width:1px,color:#fff;
    classDef output fill:#276749,stroke:#9ae6b4,stroke-width:1px,color:#fff;

    Orchestrator["SANCTUM Unified Orchestrator"]
    API["FastAPI Secured API (X-API-Key)"]
    Queue["Async Task Queue Manager"]
    SDK["Sanctum Python Client SDK"]
    RBAC["RBAC & Multi-Tenancy Manager"]
    WebDash["Next.js Web Dashboard & Attack Graph UI"]
    Guardrail["LLM Guardrail Proxy & ML Anomaly"]
    OSINT["SPECTRE-OSINT / Async Probe"]
    PortScan["Async Port Scanner"]
    ContainerCVE["Docker Container CVE Analyzer"]
    Honeypot["Decoy Honeypot Sensor"]
    RedTeam["Multimodal & Multi-Turn Fuzzer / SHADOW-AGENT"]
    Correlator["Threat Correlation Engine"]
    Mitre["MITRE ATT&CK / ATLAS Mapper"]
    Compliance["EU AI Act / NIS2 / ISO 27001 Engine"]
    AttackGraph["Attack Graph Engine (NetworkX)"]
    Playbook["Remediation Playbook Engine"]
    AutoPatch["Automated Code Patcher (Self-Healing)"]
    GitHubPR["GitHub Automated PR Publisher"]
    SigmaYara["Sigma & YARA Rule Generator"]
    SIEM["SIEM Exporter (CEF / Webhook)"]
    EventBus["Distributed Event Bus"]
    GhostMesh["GHOST-COMM Zero-Trust Mesh"]
    Signer["RSA-2048 Report Signer"]
    DuckDB["DuckDB OLAP Analytics"]
    Reports["Signed Reports (PDF / HTML / .sig)"]

    SDK -->|API Calls| API
    API -->|Enqueue Task| Queue --> RBAC --> Orchestrator
    WebDash -->|Connect via WebSockets & REST| API
    Guardrail -->|Filter & Inspect Prompts| Orchestrator
    Orchestrator -->|1. Network & Footprint Discovery| OSINT
    Orchestrator -->|2. Active TCP Port Scan| PortScan
    Orchestrator -->|3. Container CVE Scan| ContainerCVE
    Orchestrator -->|4. Monitor Decoy Traps| Honeypot
    OSINT & PortScan -->|5. Feed Targets| RedTeam
    RedTeam & PortScan -->|6. Attack Chain, Graph & Compliance Mapping| Correlator & Mitre & Compliance & AttackGraph
    Correlator & RedTeam -->|7. Generate Hardening Playbooks, Patches & Rules| Playbook & AutoPatch & SigmaYara
    AutoPatch -->|8. Publish PR to GitHub| GitHubPR
    Correlator -->|9. Export Telemetry & Dispatch Events| SIEM & EventBus & GhostMesh
    Orchestrator -->|10. Persist Security Events| DuckDB
    Orchestrator -->|11. Generate & Sign Artifacts| Reports & Signer

    class Orchestrator,API,Queue,SDK,RBAC,WebDash core;
    class Guardrail,OSINT,PortScan,ContainerCVE,Honeypot,RedTeam,Correlator,Mitre,Compliance,AttackGraph,Playbook,AutoPatch,GitHubPR,SigmaYara,SIEM,EventBus,GhostMesh module;
    class DuckDB,Reports,Signer output;