from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.langgraph_flow import run_stub_flow
from app.dataio import load_signals, latest_week   # 👈 add this import

app = FastAPI(title="T3C", version="0.2.0")

# ----- existing endpoints (keep) -----
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

class Ticket(BaseModel):
    ticket_id: str
    customer_id: str
    text: str

@app.post("/run_ticket")
def run_ticket(t: Ticket):
    return run_stub_flow(t.model_dump())

# Optional: friendly root so / isn’t 404
@app.get("/")
def home():
    return {"ok": True, "try": ["/healthz", "/docs", "POST /run_ticket", "/cpi/top", "/cpi/summary"]}

# ----- new CPI endpoints (add these) -----
@app.get("/cpi/top")
def cpi_top(limit: int = 20, region: Optional[str] = None):
    """Top-N customers by CPI for the latest week (optionally filter by region)."""
    import pandas as pd
    df = load_signals()
    wk = latest_week()
    sub = df[df["date"] == wk]
    if region:
        sub = sub[sub["region"].astype(str) == region]
    out = (sub.sort_values("CPI", ascending=False)
              .head(limit)
              [["customer_id","region","CPI","contract_days_remaining",
                "price_sensitivity_flag","peer_port_count_30d","weekly_ad_intensity_index"]])
    return out.to_dict(orient="records")

@app.get("/cpi/summary")
def cpi_summary(region: Optional[str] = None,
                start: Optional[str] = None,
                end: Optional[str] = None):
    """Summary stats and a short trend over a date window."""
    import pandas as pd
    df = load_signals()
    sub = df
    if region:
        sub = sub[sub["region"].astype(str) == region]
    if start:
        sub = sub[sub["date"] >= pd.to_datetime(start)]
    if end:
        sub = sub[sub["date"] <= pd.to_datetime(end)]

    agg = {
        "records": int(len(sub)),
        "avg_cpi": float(sub["CPI"].mean()) if len(sub) else None,
        "p90_cpi": int(sub["CPI"].quantile(0.90)) if len(sub) else None,
        "latest_week": str(sub["date"].max().date()) if len(sub) else None
    }
    by_week = (sub.groupby("date")["CPI"].mean().reset_index().tail(12))
    agg["trend"] = [{"date": str(r.date()), "avg_cpi": float(v)} for r, v in zip(by_week["date"], by_week["CPI"])]
    return agg

@app.get("/cpi/customer/{customer_id}")
def cpi_for_customer(customer_id: str):
    """Latest CPI row for a specific customer."""
    df = load_signals()
    wk = latest_week()
    sub = df[(df["customer_id"] == customer_id) & (df["date"] == wk)]
    if sub.empty:
        return {"found": False}
    row = sub.iloc[0].to_dict()
    row["found"] = True
    row["date"] = str(row["date"].date())
    return row

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from app.langgraph_flow import run_stub_flow
from app.dataio import load_signals, latest_week
from app.analytics import severity_0_100, crs_0_1, final_risk, route_action

app = FastAPI(title="T3C", version="0.3.0")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

class Ticket(BaseModel):
    ticket_id: str
    customer_id: str
    text: str

@app.post("/run_ticket")
def run_ticket(t: Ticket):
    return run_stub_flow(t.model_dump())

@app.get("/")
def home():
    return {"ok": True, "try": ["/healthz", "/docs", "/cpi/top", "/cpi/summary", "/insights/top_risk"]}

# ---------- NEW: decision-ready list (no n8n) ----------
@app.get("/insights/top_risk")
def top_risk(limit: int = 20, region: Optional[str] = None):
    """
    Returns top-N customers by blended risk:
      final = 0.5*CPI + 0.3*Severity + 0.2*(CRS*100)
    Includes a recommended, policy-safe action + message.
    """
    df = load_signals()
    wk = latest_week()
    sub = df[df["date"] == wk]
    if region:
        sub = sub[sub["region"].astype(str) == region]

    rows = []
    for _, r in sub.iterrows():
        cid = str(r["customer_id"])
        reg = str(r["region"])
        cpi = int(r["CPI"])
        sev = severity_0_100(cid, reg)
        crs = crs_0_1(cid)
        score = final_risk(cpi, sev, crs)
        plan = route_action(cpi, sev, crs)
        rows.append({
            "customer_id": cid,
            "region": reg,
            "CPI": cpi,
            "Severity": sev,
            "CRS": crs,
            "final_score": score,
            **plan
        })

    rows.sort(key=lambda x: x["final_score"], reverse=True)
    return rows[:limit]
