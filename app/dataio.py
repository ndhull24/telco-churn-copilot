from functools import lru_cache
import pandas as pd
import os

SIGNALS_PATH = "data/customers.csv"

def _normalize(df):
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def _ensure_date(df):
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["date"] = df["date"].fillna(pd.Timestamp.today().normalize())
    else:
        df["date"] = pd.Timestamp.today().normalize()
    return df

def _ensure_types(df):
    if "price_sensitivity_flag" in df.columns:
        df["price_sensitivity_flag"] = (
            df["price_sensitivity_flag"].astype(str).str.lower().isin(["1","true","yes","y"])
        )
    else:
        df["price_sensitivity_flag"] = False
    if "region" not in df.columns: df["region"] = "unknown"
    if "customer_id" not in df.columns:
        df = df.rename(columns={"cust_id":"customer_id"}) if "cust_id" in df.columns else df.assign(customer_id="unknown")
    return df

def _compute_cpi_if_missing(df):
    if "cpi" not in df.columns:
        req = ["contract_days_remaining","price_sensitivity_flag","peer_port_count_30d","weekly_ad_intensity_index"]
        if all(c in df.columns for c in req):
            def score(r):
                days = int(r["contract_days_remaining"])
                price = 1 if bool(r["price_sensitivity_flag"]) else 0
                peer  = int(r["peer_port_count_30d"])
                ad    = float(r["weekly_ad_intensity_index"])
                days_term = max(0, 100 - min(days, 100))
                price_term = 100 if price == 1 else 0
                peer_term = min(peer * 10, 100)
                ad_term = int(round(min(ad * 10, 100)))
                return int(round(0.35*days_term + 0.25*price_term + 0.25*peer_term + 0.15*ad_term))
            df["cpi"] = df.apply(score, axis=1)
        else:
            df["cpi"] = 0
    df = df.rename(columns={"cpi":"CPI"})
    return df

@lru_cache(maxsize=1)
def load_signals() -> pd.DataFrame:
    if not os.path.exists(SIGNALS_PATH):
        raise FileNotFoundError(f"Signals file not found: {SIGNALS_PATH}")
    df = pd.read_csv(SIGNALS_PATH)
    df = _normalize(df)
    df = _ensure_date(df)
    df = _ensure_types(df)
    df = _compute_cpi_if_missing(df)
    df["region"] = df["region"].astype("category")
    return df

def latest_week():
    df = load_signals()
    return df["date"].max()
