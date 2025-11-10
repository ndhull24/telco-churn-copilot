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
