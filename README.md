# Telco Churn & Complaint Copilot (T3C)

Minimal, fast FastAPI service with a stubbed agent flow and mock variable severity.

## Quickstart
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.api:app --reload --port 8000

## Quickstart
```bash
python -m pip install -r requirements.txt
uvicorn app.api:app --reload --port 8000
# open http://127.0.0.1:8000/  (app)
# open http://127.0.0.1:8000/dashboard  (exec dashboard)


# 📊 T3C – Telecom Churn Copilot

### Overview
Telecom providers lose customers due to service pain (slow speeds, billing shocks) and competitive pull (intro offers, bundles).  
**T3C** uses AI-driven analytics and compliance guardrails to:
- Detect churn early (service + competitive)
- Recommend ROI-positive, policy-safe actions
- Log and audit every action automatically

---

### ⚙️ Stack
`FastAPI` · `Pandas` · `Jinja2` · `Chart.js` · `HTML/CSS/JS`

---

### 🚀 Quickstart
```bash
pip install -r requirements.txt
uvicorn app.api:app --reload --port 8000


flowchart LR
  subgraph Frontend["🌐 Website (Jinja + JS)"]
    A[User] --> B[Load Insights → Approve]
    B --> C[POST /insights/log]
    C --> D[(action_log.csv)]
  end

  subgraph Backend["⚙️ FastAPI + Analytics"]
    B --> E[Guardrails check_message]
    E -->|compliance| F[(variable_scores)]
    D --> G[Dashboard / Downloads]
  end

  subgraph Data["📊 Data Layer"]
    H[(Synthetic Telecom Signals)] --> B
  end
