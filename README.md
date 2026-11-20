# 🛡️ BugBusters // AIOps Alert Shield

<div align="center">

![AIOps Alert Shield Banner](https://img.shields.io/badge/AIOPS-ALERT--SHIELD-09090B?style=for-the-badge&logoColor=CCFF00)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![GraphQL](https://img.shields.io/badge/Strawberry-GraphQL-E10098?style=for-the-badge&logo=graphql&logoColor=white)](https://strawberry.rocks/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-Neo--Brutalist-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/Tests-25%2F25%20Passing-CCFF00?style=for-the-badge&logo=pytest&logoColor=black)](tests/)

**Orchestrated, Self-Evolving Hybrid AIOps Alert Verification Platform**  
*Built by **Team BugBusters** for the SJCE Hackathon*

[Features](#-key-features) • [Architecture](#-system-architecture) • [Scorecard](#-benchmark-scorecard) • [Quickstart](#-quickstart--verification) • [UI Console](#-neo-brutalist-console)

</div>

---

## 📌 Executive Summary

Modern cloud microservice architectures generate torrential alert storms during incidents. A single upstream failure can trigger **hundreds of cascade alerts**, blinding Site Reliability Engineers (SREs) and burying the true root cause under false positives.

**AIOps Alert Shield** by **Team BugBusters** resolves alert fatigue using a foundational design principle:  
> **"Compute first, reason second, verify against evidence and history, and only then publish an incident."**

### Highlights at a Glance
- ⚡ **90.6% Noise Reduction:** Compresses storms of 470+ raw alerts down into 44 deterministic event clusters.
- 🎯 **100% Incident Recall & Precision:** Zero missed P0 outages, zero hallucinated root-cause incidents.
- 🛡️ **Guaranteed Fail-Open Path:** If the AI gateway experiences an outage, critical deterministic threshold breaches automatically publish as `FAIL_OPEN_CRITICAL` incidents.
- 🧠 **Self-Evolving Agent (SEA) with Context Divergence Protection:** Differentiates between identical symptoms in benign scenarios (e.g. scheduled 2 AM database backups) vs critical outages (e.g. midday lock contention).
- 🎨 **Neo-Brutalist Dark Operational Console:** Built with Next.js 14 and Tailwind, featuring live streaming alert compression, causal lag graphs ($\tau$), and 3-agent reasoning dossiers.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph DataIngestion ["1. Telemetry Ingestion Layer"]
        A[Raw Alert Flood<br/>470+ events] --> B[scripts/validate_normalize.py]
        M[Timeseries Metrics<br/>10s interval] --> B
        L[Application Logs] --> P[scripts/privacy_mask.py<br/>PII / Secret Masking]
    end

    subgraph PurePythonCompute ["2. Deterministic Compute First (100% Pure Python)"]
        B --> D[scripts/deduplicate.py<br/>Fingerprint & Flapping Detection]
        B --> S[scripts/window_stats.py<br/>Median & MAD, EWMA, Hysteresis]
        S --> F[scripts/anomaly_features.py<br/>Anomaly Scoring & Symptom Hash]
        M --> C[scripts/correlate_services.py<br/>Cross-Service Lag Correlation r(tau)]
        F --> G[scripts/dependency_graph.py<br/>Blast Radius & DAG Traversal]
        G --> R[scripts/risk_features.py<br/>Deterministic Risk Scoring]
        D --> PKT[scripts/build_evidence_packet.py<br/>Typed ComputeResult Evidence Packet]
        P --> PKT
        S --> PKT
        C --> PKT
        G --> PKT
        R --> PKT
    end

    subgraph PipelineOrchestrator ["3. Pipeline Orchestrator (Fail-Open Controller)"]
        PKT --> SEAR[agents/self_evolving_agent.py (Read Path)<br/>Incident Casebook & Context Divergence Check]
        SEAR --> AIO[agents/orchestrator_agent.py<br/>AI State Machine Coordinator]
        SEAR -.->|Fail-Open Triggered| FO[Direct Incident Publication<br/>Status: FAIL_OPEN_CRITICAL]
    end

    subgraph AIOrchestrator ["4. Multi-Agent Reasoning (Maker-Checker Gate)"]
        AIO --> A1[Triage Agent<br/>Scope & User Journey Impact]
        A1 --> A2[Root-Cause Agent<br/>Causal Chain & Failure Mechanism]
        A2 --> A3[Risk Validator Agent<br/>Adversarial Verification Gate]
    end

    subgraph StorageAndAPI ["5. Storage & GraphQL Presentation Layer"]
        A3 --> DB[(SQLite WAL Database<br/>Incidents & Versioned Casebook)]
        FO --> DB
        DB --> SEAW[agents/self_evolving_agent.py (Write Path)<br/>Append Verified Resolution]
        DB --> GQL[FastAPI + Strawberry GraphQL<br/>Queries, Mutations & Subscriptions]
    end

    subgraph UI ["6. Dark Neo-Brutalist Operational Console"]
        GQL --> FRONT[Next.js 14 + React + Tailwind<br/>Real-Time Stream Replay & Topology Graph]
    end
```

---

## 🎯 Benchmark Scorecard

Evaluated against labeled production scenarios using the automated ground-truth evaluation engine (`scripts/evaluate_system.py`):

| Evaluation Metric | Benchmark Target | BugBusters Result | Status |
| :--- | :---: | :---: | :---: |
| **Incident Recall** | $\ge 95\%$ | **100.0%** (3 / 3 incidents detected) | ✅ **PASS** |
| **Alert Noise Reduction** | $\ge 85\%$ | **90.6%** (470 alerts &rarr; 44 clusters) | ✅ **PASS** |
| **Verifier Precision** | $\ge 90\%$ | **100.0%** (Zero false incidents published) | ✅ **PASS** |
| **Evidence Traceability** | $100\%$ | **100.0%** (All findings link to raw trace IDs) | ✅ **PASS** |
| **SEA Case A (Benign Noise Suppression)** | Required | **PASSED** (Suppressed with audit trail) | ✅ **PASS** |
| **SEA Case B (Context Divergence)** | Required | **PASSED** (Detected & Escalated to P0) | ✅ **PASS** |
| **Fail-Open Circuit Breaker** | Required | **PASSED** (Guaranteed P0 publication during AI failure) | ✅ **PASS** |
| **End-to-End Latency (p50 / p95)** | $< 1.0\text{s}$ | **140.3ms / 447.6ms** | ⚡ **OPTIMAL** |

---

## 🌟 Key Features

### 1. Deterministic Computation First
- **Zero Hallucinated Metrics:** 100% of arithmetic, alert deduplication, statistical anomaly detection (Rolling Median & MAD, EWMA, Rate of Change, Persistence/Hysteresis), PII redaction, dependency-graph blast radius traversal, and cross-service lag correlation are executed in pure Python modules before any LLM is called.
- Random Forest or opaque black-box ML models are strictly avoided in favor of transparent, explainable mathematics.

### 2. Dual Orchestrators & The Maker-Checker Gate
- **Pipeline Orchestrator:** Manages execution flow, timeouts, and fail-open publication.
- **AI Orchestrator:** Coordinates a 3-agent sequence:
  1. `Triage Agent`: Assesses service degradation and user checkout impact.
  2. `Root-Cause Agent`: Formulates the causal chain using lag correlation and graph topology.
  3. `Risk Validator Agent`: An adversarial checker that verifies the hypothesis against raw telemetry.

### 3. Context Divergence Protection (Self-Evolving Agent)
- **Case A (Benign Recurrence):** Identifies scheduled operations (e.g. nightly DB backups) where CPU spikes occur without latency impact, suppressing noise while retaining an audit trail.
- **Case B (Context Divergence):** If a similar CPU spike occurs during business hours with downstream error spikes, the agent flags `CONTEXT_DIVERGENCE_DETECTED` and immediately publishes a P0 incident.

---

## 🖥️ Neo-Brutalist Console

Designed with a high-contrast dark aesthetic for SRE war rooms:
- **Palette:** Deep Obsidian (`#09090B`), Charcoal (`#141418`), Electric Crimson (`#FF2E4C`), Safety Amber (`#FFB800`), Acid Lime (`#CCFF00`), and Cyber Cyan (`#00E5FF`).
- **Tab 1: Verified Incidents:** Incident dossiers, blast radius topology graphs, and one-click runbook execution.
- **Tab 2: Suppressed & Audit Log:** "No Silent Suppression" guarantee—inspect why alerts were suppressed with full manual override capability.
- **Tab 3: SEA Casebook Memory:** Historical incident casebook with vector cosine similarity search.

---

## 📁 Repository Structure

```text
bugbusters/
├── aiops-alert-shield/
│   ├── backend/                     # FastAPI & Strawberry GraphQL Service
│   │   ├── main.py                  # API endpoints (/graphql & /health)
│   │   ├── Dockerfile               # Backend container definition
│   │   ├── orchestration/           # Pipeline Orchestrator & Fail-Open logic
│   │   ├── graphql/                 # Schema, queries, mutations, subscriptions
│   │   ├── storage/                 # SQLite WAL store & case repository
│   │   └── models/                  # Pydantic schemas and contracts
│   ├── agents/                      # LLM Agents & Orchestration
│   │   ├── orchestrator_agent.py    # 3-Agent state machine
│   │   ├── triage_agent.py          # Scope & journey impact
│   │   ├── root_cause_agent.py      # Causal chain & mechanisms
│   │   ├── risk_validator_agent.py  # Maker-checker validation gate
│   │   ├── self_evolving_agent.py   # Context divergence & casebook agent
│   │   └── llm_gateway.py           # LiteLLM gateway with deterministic mock
│   ├── frontend/                    # Next.js 14 Neo-Brutalist UI
│   │   ├── src/app/                 # App Router (pages & layouts)
│   │   ├── src/components/          # Interactive console components
│   │   └── src/lib/api.ts           # GraphQL client
│   ├── scripts/                     # Pure Python Compute & Evaluation
│   │   ├── evaluate_system.py       # Automated benchmark scorecard
│   │   ├── replay_stream.py         # Micro-batched stream replay engine
│   │   ├── deduplicate.py           # Alert fingerprinting & flapping
│   │   ├── window_stats.py          # Rolling Median, MAD, EWMA
│   │   ├── correlate_services.py    # Cross-service lag correlation
│   │   ├── dependency_graph.py      # Blast radius DAG traversal
│   │   └── privacy_mask.py          # PII & token redaction
│   ├── tests/                       # Complete Pytest test suite (25/25)
│   ├── data/                        # Benchmark datasets & ground truth
│   ├── start.ps1                    # One-command Windows launcher
│   ├── start.sh                     # One-command Linux/macOS launcher
│   └── docker-compose.yml           # Full containerized stack
├── .gitignore                       # Clean repository exclusions
└── README.md                        # Master project documentation
```

---

## 🚀 Quickstart & Verification

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**

### 1. Launch the Full Stack
Navigate to `aiops-alert-shield` and run the launcher:
- **Windows (PowerShell):**
  ```powershell
  cd aiops-alert-shield
  .\start.ps1
  ```
- **Linux / macOS:**
  ```bash
  cd aiops-alert-shield
  chmod +x start.sh && ./start.sh
  ```

Access the services:
- **Operational Console:** `http://localhost:3000`
- **GraphQL Interactive Playground:** `http://localhost:8000/graphql`
- **Health Check:** `http://localhost:8000/health`

### 2. Run Ground-Truth Benchmark
Validate performance against labeled scenarios:
```bash
cd aiops-alert-shield
python scripts/evaluate_system.py
```

### 3. Replay 400-Alert Live Storm
Simulate a live production cascading outage:
```bash
cd aiops-alert-shield
python scripts/replay_stream.py --speed 5.0
```

### 4. Run Pytest Suite
```bash
cd aiops-alert-shield
python -m pytest tests -v
```

---

## 👥 Team BugBusters

Developed for the **SJCE Hackathon**:
- **GitHub:** [@chinmayeevs](https://github.com/chinmayeevs)
- **Repository:** [`bugbusters`](https://github.com/chinmayeevs/bugbusters)

---

<div align="center">
<sub>Built with ⚡ by Team BugBusters • Deterministic Compute First AIOps</sub>
</div>
