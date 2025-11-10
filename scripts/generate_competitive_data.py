# scripts/generate_competitive_data.py
# Generates a 12-month synthetic dataset for competitive-offer churn signals.
# Output: data/customers.csv, data/competitive_signals_2025.csv

import os, math, random
import numpy as np
import pandas as pd
from datetime import date, timedelta

random.seed(42)
np.random.seed(42)

OUT_DIR = "data"
os.makedirs(OUT_DIR, exist_ok=True)

# --------------------------
# Config (tweak freely)
# --------------------------
N_CUSTOMERS      = 20000          # increase if your laptop can handle it
WEEKS_BACK       = 52             # 1 year
YEAR_START_MONDAY = date(date.today().year, 1, 6) - timedelta(weeks=52)  # approx last year

REGIONS = [
    # name, base_ad_intensity (0..10), competitiveness (drives peer ports), arpu_tier
    ("metro_north", 6.0, 1.2, "high"),
    ("metro_south", 5.0, 1.0, "high"),
    ("urban_east",  4.5, 1.0, "mid"),
    ("urban_west",  4.0, 0.9, "mid"),
    ("suburb_east", 3.0, 0.7, "mid"),
    ("rural_north", 2.2, 0.5, "low"),
    ("rural_south", 1.8, 0.4, "low"),
]

PLAN_TIERS = ["basic", "standard", "premium"]

# --------------------------
# Helper: CPI (same as app/scoring.py)
# --------------------------
def score_cpi(contract_days_remaining: int,
              price_sensitivity_flag: bool,
              peer_port_count_30d: int,
              weekly_ad_intensity_index: float) -> int:
    days = int(contract_days_remaining)
    price = 1 if price_sensitivity_flag else 0
    peer_ports = int(peer_port_count_30d)
    ad_idx = float(weekly_ad_intensity_index)

    days_term = max(0, 100 - min(days, 100))
    price_term = 100 if price == 1 else 0
    peer_term = min(peer_ports * 10, 100)
    ad_term = int(round(min(ad_idx * 10, 100)))

    cpi = int(round(0.35*days_term + 0.25*price_term + 0.25*peer_term + 0.15*ad_term))
    return min(max(cpi, 0), 100)

# --------------------------
# 1) Customers master
# --------------------------
cust_ids = [f"C{str(i).zfill(6)}" for i in range(1, N_CUSTOMERS+1)]

# Region distribution (more weight to metro/urban)
region_names = [r[0] for r in REGIONS]
region_weights = np.array([0.20, 0.18, 0.16, 0.16, 0.14, 0.08, 0.08])
region_weights = region_weights / region_weights.sum()

customer_regions = np.random.choice(region_names, size=N_CUSTOMERS, p=region_weights)

# Plan tier distribution
tier_weights = np.array([0.45, 0.40, 0.15])  # basic, standard, premium
customer_tiers = np.random.choice(PLAN_TIERS, size=N_CUSTOMERS, p=tier_weights)

# Tenure months (skew older for premium)
tenure = []
for t in customer_tiers:
    if t == "premium":
        tenure.append(int(np.clip(np.random.normal(48, 12), 6, 120)))
    elif t == "standard":
        tenure.append(int(np.clip(np.random.normal(30, 10), 3, 120)))
    else:
        tenure.append(int(np.clip(np.random.normal(18, 9), 1, 120)))

# Price sensitivity flag baseline probability by tier
tier_price_p = {"basic": 0.40, "standard": 0.25, "premium": 0.12}
price_flags = [np.random.rand() < tier_price_p[t] for t in customer_tiers]

customers_df = pd.DataFrame({
    "customer_id": cust_ids,
    "region": customer_regions,
    "plan_tier": customer_tiers,
    "tenure_months": tenure,
    "price_sensitivity_flag": price_flags
})

customers_df.to_csv(os.path.join(OUT_DIR, "customers.csv"), index=False)

# --------------------------
# 2) Region weekly ad intensity (synthetic)
#    base + seasonality + noise  -> 0..10
# --------------------------
weeks = [YEAR_START_MONDAY + timedelta(weeks=k) for k in range(WEEKS_BACK)]
region_params = {r[0]: r for r in REGIONS}

region_week_rows = []
for rname, base, comp, _arpu in REGIONS:
    for k, wk in enumerate(weeks):
        # mild seasonality + AR(1)-like noise
        season = 1.0 + 0.3*math.sin(2*math.pi*(k/52))
        noise = np.random.normal(0, 0.5)
        val = max(0.0, min(10.0, base*season + noise))
        region_week_rows.append({"date": wk, "region": rname, "weekly_ad_intensity_index": round(val, 2)})

region_week_df = pd.DataFrame(region_week_rows)

# --------------------------
# 3) Household peer ports per customer per week
#    Poisson rate depends on region competitiveness
# --------------------------
region_comp = {r[0]: r[2] for r in REGIONS}  # competitiveness multiplier
peer_rows = []
for cid, rname in zip(cust_ids, customer_regions):
    lam = 0.2 * region_comp[rname]  # typical 0..~0.24
    # draw per-week ports with occasional spikes near contract end (added later)
    base_ports = np.random.poisson(lam=lam, size=WEEKS_BACK)
    peer_rows.append(base_ports)

peer_ports_arr = np.vstack(peer_rows)  # shape: (N_CUSTOMERS, WEEKS_BACK)

# --------------------------
# 4) Contract days remaining (≤ 30) — focus window near renewal
#    Pick a contract-end week; for 6 weeks before it, we fill 42..0 then cap to 30.
#    For other weeks, set to 30 (i.e., "not in window").
# --------------------------
end_weeks = np.random.randint(low=8, high=WEEKS_BACK-2, size=N_CUSTOMERS)  # renewal somewhere in the year
contr_days = np.full((N_CUSTOMERS, WEEKS_BACK), 30, dtype=int)  # default 30 (outside window)
for i in range(N_CUSTOMERS):
    end_wk = end_weeks[i]
    # last 6 weeks window
    for offset in range(6, -1, -1):  # 6..0 weeks
        wk = end_wk - (6 - offset)
        if 0 <= wk < WEEKS_BACK:
            days = offset * 7  # 42,35,28,...,0
            contr_days[i, wk] = min(days, 30)

# spike peer ports slightly inside window
for i in range(N_CUSTOMERS):
    w = end_weeks[i]
    w0, w1 = max(0, w-6), min(WEEKS_BACK-1, w)
    peer_ports_arr[i, w0:w1+1] += np.random.poisson(lam=0.3, size=(w1-w0+1))

# --------------------------
# 5) Build weekly customer rows + CPI
# --------------------------
rows = []
for idx, cid in enumerate(cust_ids):
    rname = customer_regions[idx]
    price_flag = bool(price_flags[idx])

    for w_idx, wk in enumerate(weeks):
        ad_idx = region_week_df.loc[
            (region_week_df["region"] == rname) & (region_week_df["date"] == wk),
            "weekly_ad_intensity_index"
        ].iloc[0]
        ports30 = int(peer_ports_arr[idx, w_idx])
        cdr = int(contr_days[idx, w_idx])

        cpi = score_cpi(
            contract_days_remaining=cdr,
            price_sensitivity_flag=price_flag,
            peer_port_count_30d=ports30,
            weekly_ad_intensity_index=ad_idx,
        )

        rows.append({
            "date": wk,
            "customer_id": cid,
            "region": rname,
            "contract_days_remaining": cdr,                 # ≤ 30 by construction
            "price_sensitivity_flag": price_flag,
            "peer_port_count_30d": ports30,
            "weekly_ad_intensity_index": ad_idx,
            "CPI": cpi
        })

signals_df = pd.DataFrame(rows).sort_values(["date","customer_id"]).reset_index(drop=True)

# Save
signals_df.to_csv(os.path.join(OUT_DIR, "competitive_signals_2025.csv"), index=False)

print(f"✅ Wrote {len(customers_df):,} customers to data/customers.csv")
print(f"✅ Wrote {len(signals_df):,} weekly records to data/competitive_signals_2025.csv")
