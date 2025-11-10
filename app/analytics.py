# app/analytics.py
import hashlib
from typing import Dict

# ---------- deterministic utilities ----------
def _seed_from_id(s: str) -> int:
    # stable 32-bit int from id for reproducible pseudo-randomness
    return int(hashlib.md5(s.encode()).hexdigest(), 16) & 0xFFFFFFFF

def _pseudo_uniform(seed: int, a: float = 0.0, b: float = 1.0) -> float:
    # very small LCG-style generator from seed → [0,1)
    x = (1103515245 * seed + 12345) & 0x7FFFFFFF
    return a + (x / 0x7FFFFFFF) * (b - a)

# ---------- scores ----------
def severity_0_100(customer_id: str, region: str) -> int:
    """
    Placeholder service Severity score (0–100).
    Intuition: different regions have different network strain ± jitter.
    Deterministic per (customer, region).
    """
    base = 50
    region_bias = (hash(region) % 11) - 5   # -5..+5
    seed = _seed_from_id(customer_id + "|" + region)
    jitter = int(_pseudo_uniform(seed, -15, 15))
    s = max(0, min(100, base + region_bias + jitter))
    return s

def crs_0_1(customer_id: str) -> float:
    """
    Placeholder Churn Risk Score (0..1).
    A monotonic mapping from a stable seed so we have consistent ranking.
    """
    seed = _seed_from_id(customer_id)
    # skew slightly to create a few high-risk tails
    u = _pseudo_uniform(seed, 0.0, 1.0)
    crs = min(0.95, round((u**1.5) * 0.9, 2))
    return crs

def final_risk(cpi: int, sev: int, crs: float) -> float:
    """
    Weighted blend per Day-3 plan:
      final = 0.5*CPI + 0.3*Severity + 0.2*(CRS*100)
    Returns 0..100
    """
    return round(0.5 * cpi + 0.3 * sev + 0.2 * (crs * 100), 2)

# ---------- action router ----------
def route_action(cpi: int, sev: int, crs: float) -> Dict:
    """
    Policy-safe routing (cheap first, no guarantees).
      - If CPI ≥ 80 and Severity < 60 → competitive playbook (data boost / referral)
      - If Severity ≥ 70 or CRS ≥ 0.8 → service playbook (plan review / priority callback / tech visit)
      - Otherwise → soft plan review
    """
    if cpi >= 80 and sev < 60:
        action = "data_boost"
        reason = "High competitive pressure; provide low-cost, high perceived value."
        cost = 3
    elif sev >= 70 or crs >= 0.8:
        action = "priority_callback" if sev < 80 else "tech_visit"
        reason = "Service factors likely; review line or schedule investigation."
        cost = 2 if action == "priority_callback" else 25
    else:
        action = "plan_review"
        reason = "Moderate risk; review options before committing credits."
        cost = 0

    msg = (
        "We can review your plan and check your line where needed. "
        "Would you like us to schedule a priority callback? "
        "Credits, if any, are a one-time credit, subject to account review; "
        "availability can vary by account and region."
    )
    return {"action": action, "reason": reason, "proposed_text": msg, "estimated_action_cost_usd": cost}
