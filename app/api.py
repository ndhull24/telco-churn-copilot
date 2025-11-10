# app/api.py
from typing import Optional, List

from fastapi import FastAPI, Request, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from fastapi.responses import FileResponse

# project imports
from app.langgraph_flow import run_stub_flow
from app.dataio import load_signals, latest_week
from app.guardrails import check_message, add_disclaimers
from app.analytics import severity_0_100, crs_0_1, final_risk, route_action
from app.logger import append_action

from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
import os

# -----------------------------------------------------------------------------
# FastAPI app + WEBSITE (static & Jinja templates)
# -----------------------------------------------------------------------------
app = FastAPI(title="T3C", version="0.4.0")

# serve static assets and templates from /web
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# website home (HTML). Data is fetched by /static/app.js from JSON APIs below.
@app.get("/")
def home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# -----------------------------------------------------------------------------
# Health + simple ticket endpoint (kept)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# CPI endpoints
# -----------------------------------------------------------------------------
@app.get("/cpi/top")
def cpi_top(limit: int = 20, region: Optional[str] = None):
    """Top-N customers by CPI for the latest week (optionally filter by region)."""
    import pandas as pd  # local import to keep module import light
    df = load_signals()
    wk = latest_week()
    sub = df[df["date"] == wk]
    if region:
        sub = sub[sub["region"].astype(str) == region]
    out = (
        sub.sort_values("CPI", ascending=False)
           .head(limit)[
            [
                "customer_id",
                "region",
                "CPI",
                "contract_days_remaining",
                "price_sensitivity_flag",
                "peer_port_count_30d",
                "weekly_ad_intensity_index",
            ]
        ]
    )
    return out.to_dict(orient="records")

@app.get("/cpi/summary")
def cpi_summary(
    region: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
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

    if len(sub) == 0:
        return {
            "records": 0,
            "avg_cpi": None,
            "p90_cpi": None,
            "latest_week": None,
            "trend": [],
        }

    agg = {
        "records": int(len(sub)),
        "avg_cpi": float(sub["CPI"].mean()),
        "p90_cpi": int(sub["CPI"].quantile(0.90)),
        "latest_week": str(sub["date"].max().date()),
    }
    by_week = sub.groupby("date")["CPI"].mean().reset_index().tail(12)
    agg["trend"] = [
        {"date": str(d.date()), "avg_cpi": float(v)}
        for d, v in zip(by_week["date"], by_week["CPI"])
    ]
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

# -----------------------------------------------------------------------------
# Insights (risk + compliance)
# -----------------------------------------------------------------------------
@app.get("/insights/top_risk")
def top_risk(limit: int = 20, region: Optional[str] = None, auto_fix: bool = True):
    """
    Returns top-N customers by blended risk with a policy-safe action.
    If auto_fix=True, missing disclaimers are appended automatically.
    """
    df = load_signals()
    wk = latest_week()
    sub = df[df["date"] == wk]
    if region:
        sub = sub[sub["region"].astype(str) == region]

    rows = []
    for _, r in sub.iterrows():
        cid, reg = str(r["customer_id"]), str(r["region"])
        cpi = int(r["CPI"])
        sev = severity_0_100(cid, reg)
        crs = crs_0_1(cid)
        score = final_risk(cpi, sev, crs)
        plan = route_action(cpi, sev, crs)

        msg = plan["proposed_text"]
        if auto_fix:
            msg = add_disclaimers(msg)

        comp = check_message(msg)
        rows.append(
            {
                "customer_id": cid,
                "region": reg,
                "CPI": cpi,
                "Severity": sev,
                "CRS": crs,
                "final_score": score,
                "action": plan["action"],
                "reason": plan["reason"],
                "proposed_text": msg,
                "compliance": comp,
                "estimated_action_cost_usd": plan["estimated_action_cost_usd"],
            }
        )

    rows.sort(key=lambda x: x["final_score"], reverse=True)
    return rows[:limit]

@app.post("/utils/check_text")
def check_text(payload: dict = Body(...)):
    txt = payload.get("text", "")
    return check_message(add_disclaimers(txt))

# -----------------------------------------------------------------------------
# Logging approvals to CSV
# -----------------------------------------------------------------------------
@app.post("/insights/log")
def log_actions(payload: List[dict] = Body(...)):
    for item in payload:
        append_action(item)
    return {"ok": True, "logged": len(payload)}

@app.get("/admin/download/action_log.csv")
def download_action_log():
    return FileResponse("data/action_log.csv", media_type="text/csv", filename="action_log.csv")

@app.get("/admin/download/top_risk")
def download_top_risk(
    region: Optional[str] = None,
    format: str = "csv",        # csv | xlsx | json
    limit: Optional[int] = None # None = no limit (all rows)
):
    # --- build the dataset (same logic as /insights/top_risk but file-friendly) ---
    df = load_signals()
    wk = latest_week()
    sub = df[df["date"] == wk]
    if region:
        sub = sub[sub["region"].astype(str) == region]

    rows = []
    for _, r in sub.iterrows():
        cid, reg = str(r["customer_id"]), str(r["region"])
        cpi = int(r["CPI"])
        sev = severity_0_100(cid, reg)
        crs = crs_0_1(cid)
        score = final_risk(cpi, sev, crs)
        plan = route_action(cpi, sev, crs)
        rows.append({
            "customer_id": cid, "region": reg,
            "CPI": cpi, "Severity": sev, "CRS": crs,
            "final_score": score, "action": plan["action"],
            "reason": plan["reason"], "proposed_text": plan["proposed_text"],
            "estimated_action_cost_usd": plan["estimated_action_cost_usd"]
        })

    out = pd.DataFrame(rows).sort_values("final_score", ascending=False)
    if limit is not None and limit > 0:
        out = out.head(limit)

    os.makedirs("data", exist_ok=True)

    # --- return in requested format ---
    fmt = format.lower()
    if fmt == "json":
        # return JSON array directly
        return JSONResponse(out.to_dict(orient="records"))

    if fmt == "xlsx" or fmt == "excel":
        path = "data/top_risk_download.xlsx"
        # index=False for a clean sheet
        out.to_excel(path, index=False)
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="top_risk.xlsx"
        )

    # default = CSV
    path = "data/top_risk_download.csv"
    out.to_csv(path, index=False)
    return FileResponse(path, media_type="text/csv", filename="top_risk.csv")

from fastapi.responses import HTMLResponse
import pandas as pd, os

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    log_path = "data/action_log.csv"
    stats = {"logged": 0, "pass_rate": 0.0, "violations": 0}
    trend = []
    by_action = []

    if os.path.exists(log_path):
        df = pd.read_csv(log_path)
        if not df.empty:
            # coerce
            df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
            if "pass" in df.columns:
                # in CSV it might be string "True"/"False" → normalize to bool
                df["pass"] = df["pass"].astype(str).str.lower().isin(["true","1","yes"])
            df["date"] = df["ts"].dt.date

            stats["logged"] = int(len(df))
            stats["pass_rate"] = round(float(df["pass"].mean()*100) if len(df) else 0.0, 2)
            stats["violations"] = int((~df["pass"]).sum())

            trend = (
                df.groupby("date")["pass"].mean().reset_index()
                  .rename(columns={"pass":"pass_rate"})
                  .assign(pass_rate=lambda x: (x["pass_rate"]*100).round(2))
                  .tail(30)
                  .to_dict(orient="records")
            )
            if "action" in df.columns:
                by_action = (
                    df.groupby("action").size().reset_index(name="count")
                      .sort_values("count", ascending=False)
                      .to_dict(orient="records")
                )

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "stats": stats, "trend": trend, "by_action": by_action}
    )