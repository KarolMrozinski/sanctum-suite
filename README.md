# 🏛️ SANCTUM-SUITE: Enterprise Cyber Resilience & AI Safety Platform

[![Architecture](https://img.shields.io/badge/architecture-Modular%20%7C%20Enterprise%20Grade-darkblue)](#)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![Docker](https://img.shields.io/badge/docker-Ready-blue)](#)
[![API](https://img.shields.io/badge/API-FastAPI%20%7C%20Secured-teal)](#)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-green)](#)
[![License](https://img.shields.io/badge/license-Non--Commercial-orange)](#)

> **SANCTUM-SUITE** to zintegrowana, wielomodułowa platforma bezpieczeństwa klasy Enterprise. Łączy rozpoznanie powierzchni ataku (**SPECTRE-OSINT**), automatyczny Red-Teaming modeli LLM (**SHADOW-AGENT**), samoleczącą się sieć P2P Zero-Trust (**GHOST-COMM**), asynchroniczny skaner portów/usług, silnik korelacji zagrożeń, zabezpieczony serwer **REST API / WebSockets** (`FastAPI` + `X-API-Key`) oraz gotową infrastrukturę konteneryzacji i CI/CD.

---

## ⚡ Kluczowe Moduły i Funkcjonalności Systemu

- **SPECTRE-OSINT & Async Probing:** Pasywna agregacja aktywów cyfrowych, asynchroniczne sondowanie nagłówków i certyfikatów (`httpx` + `asyncio`).
- **Async Port & Service Scanner:** Błyskawiczny, wielowątkowy skaner otwartych portów TCP (SSH, HTTP, HTTPS, DB, Ollama API).
- **SHADOW-AGENT AI Red-Teaming:** Automatyczny fuzzing modeli LLM pod kątem *Prompt Injection*, wycieków instrukcji i złamań guardraili.
- **GHOST-COMM Mesh & Remediation:** Bezpieczne pakowanie alertów w szyfrowane koperty P2P (AES-256-GCM) oraz zapasowy routing Zero-Trust.
- **Threat Correlation Engine:** Wykrywanie złożonych łańcuchów ataku (*Attack Chains*) i korelacja otwartych portów z podatnościami AI.
- **Secured REST & WebSockets API:** Asynchroniczny serwer API z obsługą nagłówków `X-API-Key`, interaktywną dokumentacją Swagger UI oraz strumieniowaniem alertów w czasie rzeczywistym.
- **OLAP Analytics & Persistence:** Trwała analityka wariancji ryzyka w **DuckDB** oraz archiwizacja audytów w **SQLite**.
- **Executive Reporting & Live TUI:** Automatyczny generator raportów zgodności dla zarządu (**PDF** / **HTML**) oraz pełnoekranowy pulpit **Rich Live TUI Dashboard**.
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
    OSINT["SPECTRE-OSINT / Async Probe"]
    PortScan["Async Port Scanner"]
    RedTeam["SHADOW-AGENT (LLM Fuzzer)"]
    Correlator["Threat Correlation Engine"]
    GhostMesh["GHOST-COMM Zero-Trust Mesh"]
    DuckDB["DuckDB OLAP Analytics"]
    Reports["Compliance Reports (PDF / HTML)"]

    API -->|Secured REST Trigger / WS Stream| Orchestrator
    Orchestrator -->|1. Network & Footprint Discovery| OSINT
    Orchestrator -->|2. Active TCP Port Scan| PortScan
    OSINT & PortScan -->|3. Feed Targets| RedTeam
    RedTeam & PortScan -->|4. Attack Chain Analysis| Correlator
    Correlator -->|5. Encrypted Alert Dispatch| GhostMesh
    Orchestrator -->|6. Persist Security Events| DuckDB
    Orchestrator -->|7. Generate Executive Artifacts| Reports

    class Orchestrator,API core;
    class OSINT,PortScan,RedTeam,Correlator,GhostMesh module;
    class DuckDB,Reports output;