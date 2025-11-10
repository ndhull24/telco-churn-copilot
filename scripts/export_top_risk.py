import pandas as pd
from app.dataio import load_signals, latest_week
from app.analytics import severity_0_100, crs_0_1, final_risk, route_action

LIMIT = 200
REGION = None  # e.g., "metro_north"

df = load_signals()
wk = latest_week()
sub = df[df["date"] == wk]
if REGION:
    sub = sub[sub["region"].astype(str) == REGION]

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
        "customer_id": cid, "region": reg, "CPI": cpi,
        "Severity": sev, "CRS": crs, "final_score": score,
        "action": plan["action"], "reason": plan["reason"],
        "proposed_text": plan["proposed_text"], "estimated_action_cost_usd": plan["estimated_action_cost_usd"]
    })

out = pd.DataFrame(rows).sort_values("final_score", ascending=False).head(LIMIT)
out.to_csv("data/top_risk_export.csv", index=False)
print("✅ Wrote data/top_risk_export.csv with", len(out), "rows")
