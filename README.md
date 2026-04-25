# 🛡️ AuthBridge — AI-Native Employee Onboarding

> **Agentic AI layer that collapses offer-to-Day-1 from ~100 days to 10, with BGV embedded (not bolted on), DPDP Act 2023 compliance from Day 1, and production-grade RBAC throughout.**

Built for the AuthBridge AI Engineer assignment — Option 2: AI-Native Employee Onboarding Tool.

---

## 🏗️ Architecture

```
Streamlit UI (port 8501)
        │
        ▼
  FastAPI Backend (port 8000)   ◄─── REST + async aiosqlite
        │
        ▼
 LangGraph Supervisor Agent  (meta/llama-3.3-70b-instruct via NVIDIA NIM)
        │
   ┌────┴─────────────────────────┐
   ▼           ▼          ▼       ▼
Document    Policy     DPDP      BGV
 Agent      RAG        Compliance Agent
            Agent      Agent     (iBRIDGE mock)
              │           │
              ▼           ▼
         ChromaDB      HITL Queue
        (per-tenant    (HR approval
         namespace)     gate)
              │
   ┌──────────┴──────────┐
   ▼                     ▼
authbridge            globalbank
 tenant                tenant
```

**Persistence layer (SQLite)**
```
employees · tasks · audit_trail (immutable) · consents · hitl_queue · query_metrics
```

---

## 🎯 Key Differentiators

| Feature | What it solves |
|---------|----------------|
| **LangGraph Multi-Agent** | Supervisor + 4 specialist agents with typed state — not a chatbot |
| **Multi-Tenant ChromaDB** | Same query, different tenant-scoped answers — zero data bleed |
| **Production RBAC** | Dynamic tab gating + session isolation on privilege downgrade |
| **DPDP Act 2023** | Immutable audit trail: prompt · context · consent · model · purpose |
| **Human-in-the-Loop** | HR approval queue blocks high-risk actions (criminal checks, BGV) |
| **HyDE RAG + LRU Cache** | Hypothetical Document Embeddings for semantic expansion + 1-hour cache |
| **RAGAS Dashboard** | 10-question golden set: Faithfulness · Recall · Relevancy · Precision |
| **Mock iBRIDGE API** | BGV integration stub — swap one line for the live AuthBridge API key |
| **NVIDIA LLM / NIM-Ready** | meta/llama-3.3-70b-instruct — zero OpenAI dependency |

---

## 🔐 Role-Based Access Control

The UI implements production-grade RBAC — tabs are dynamically created per role, not just locked behind banners.

| Role | Tabs visible | Employee selector |
|------|-------------|-------------------|
| 👤 Employee | New Hire Portal only | Locked to own record (JWT `sub` in production) |
| 👔 Manager | Portal + Manager View | Full team dropdown |
| 🛡️ HR Admin | All 6 tabs | Full tenant dropdown |
| ⚙️ Super Admin | All 6 tabs | Full tenant dropdown |

**Session isolation:** Switching from a higher to a lower privilege role clears all `st.session_state` keys — chat history, cached results, trace data — preventing data leakage between role sessions.

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/ARajkumar45/AuthBridge_Onboarding.git
cd AuthBridge_Onboarding
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.template .env
# Add your NVIDIA_API_KEY from https://build.nvidia.com
```

### 3. Run (direct mode — no FastAPI needed for the demo)
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### 4. (Optional) Run FastAPI Backend
```bash
python api/main.py
# Swagger UI at http://localhost:8000/docs
```

### 5. (Optional) Run Tests
```bash
pytest tests/ -v
```

---

## 📁 Project Structure

```
AuthBridge_Onboarding/
├── app.py                     # Streamlit UI — 6-tab role-gated dashboard
├── requirements.txt
├── .env.template
├── Dockerfile
├── docker-compose.yml
├── logging_config.py          # Structured JSON logging
├── retention_job.py           # DPDP data-retention scheduler
├── agents/
│   └── supervisor.py          # LangGraph graph — Supervisor + 4 agents
├── api/
│   └── main.py                # FastAPI async backend (aiosqlite)
├── database/
│   └── db.py                  # SQLite schema, seed data, audit helpers
├── rag/
│   ├── loader.py              # ChromaDB multi-tenant loader + HyDE + LRU
│   └── policies/              # 5 HR policy documents
│       ├── leave_policy.txt
│       ├── bgv_policy.txt
│       ├── dpdp_policy.txt
│       ├── it_provisioning_policy.txt
│       └── code_of_conduct.txt
└── tests/
    └── test_api.py            # pytest API test suite
```

---

## 🔒 DPDP Act 2023 Compliance

| Requirement | Implementation |
|-------------|----------------|
| **Per-purpose consent** (§6) | Unbundled, revocable, purpose-specific consent table |
| **Legitimate use** (§7(1)(i)) | Employment processing without separate consent |
| **Data principal rights** (§8) | Access, correction, erasure flows in UI |
| **Immutable audit trail** | Every AI action: prompt · context chunks · model · purpose · consent status |
| **Breach notification hooks** | 72-hour timer stubs ready for production wiring |
| **Data retention schedules** | PF 10yr · BGV 7yr · Chat 2yr · Audit 7yr |
| **Aadhaar masking** | First 8 digits masked per UIDAI 2025 circular |

---

## 🤖 Agent Details

| Agent | Role | HITL Trigger |
|-------|------|-------------|
| **Supervisor** | Routes to specialist, aggregates response | — |
| **Document Agent** | OCR, extraction, classification | Confidence < 80% |
| **Policy RAG Agent** | Multi-tenant HyDE + ChromaDB Q&A | — |
| **Compliance Agent** | DPDP consent gate + audit write | Missing consent |
| **BGV Agent** | iBRIDGE mock API — criminal / identity checks | All BGV + criminal |

---

## 📊 UI Tabs

| Tab | Role Required | What it shows |
|-----|--------------|---------------|
| 🏠 New Hire Portal | All | AI chat · onboarding stepper · document checklist · policy acknowledgement |
| 👔 Manager View | Manager+ | Team KPIs · per-employee progress tracker · HITL escalation queue |
| 🛡️ HR Admin Dashboard | HR Admin+ | Tenant KPIs · consent management · HITL approval · department breakdown |
| 🔍 Agent Trace Viewer | HR Admin+ | Animated LangGraph SVG · live execution trace · DPDP audit log |
| 📊 RAGAS Evaluation | HR Admin+ | Faithfulness · Context Recall · Answer Relevancy · Context Precision gauges |
| ⚡ Performance | HR Admin+ | Query latency · confidence trends · cache hit rate · agent breakdown |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | NVIDIA API — `meta/llama-3.3-70b-instruct` |
| Embeddings | `nvidia/nv-embedqa-e5-v2` |
| RAG | ChromaDB + HyDE + LRU cache |
| Agent Orchestration | LangGraph (typed state machine) |
| Backend | FastAPI + aiosqlite (fully async) |
| Frontend | Streamlit (dark mode, Plotly, animated SVG) |
| Database | SQLite with WAL mode |
| Evaluation | RAGAS-inspired metric suite |
| Containerisation | Docker + docker-compose |

---

## 👤 Author

**Arivukkarasan Rajkumar**
- GitHub: [github.com/ARajkumar45](https://github.com/ARajkumar45)
- Email: armugamvrajkumar121@gmail.com
- LangChain Academy Certified · 2 years Python @ HCL Technologies

---

*Built for AuthBridge Research Services — India's largest background verification company.*
