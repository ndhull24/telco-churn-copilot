# app/guardrails.py
import re
from typing import Dict, List

# 1) Banned phrases (case-insensitive, whole or partial)
BANNED_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bguarantee(?:d|s)?\b", re.I),
    re.compile(r"\bpermanent price(?:s)?\b", re.I),
    re.compile(r"\bprice\s*match(?:ing)?\b", re.I),
    re.compile(r"\b(unlimited|100%)\s*(speed|throughput)\b", re.I),
    re.compile(r"\bwe will (always|never)\b", re.I),
    re.compile(r"\bno questions asked\b", re.I),
    re.compile(r"\bpii\b", re.I),  # stand-in for PII echoes
]

# 2) Required disclaimers (we’ll enforce presence of at least these two)
REQUIRED_SNIPPETS = [
    "availability can vary by account and region",
    "one-time credit, subject to account review",
]

def check_message(text: str) -> Dict:
    """Returns {pass: bool, violations: [...], missing_disclaimers: [...]}"""
    violations = []
    for pat in BANNED_PATTERNS:
        if pat.search(text or ""):
            violations.append(pat.pattern)

    missing = []
    low = (text or "").lower()
    for req in REQUIRED_SNIPPETS:
        if req not in low:
            missing.append(req)

    is_ok = (len(violations) == 0 and len(missing) == 0)
    return {"pass": is_ok, "violations": violations, "missing_disclaimers": missing}

def add_disclaimers(text: str) -> str:
    """Append any missing required disclaimers neatly."""
    low = text.lower()
    to_add = [d for d in REQUIRED_SNIPPETS if d not in low]
    if not to_add:
        return text
    suffix = " ".join([f"({d})." for d in to_add])
    if not text.endswith(("!", ".", "?")):
        text += "."
    return f"{text} {suffix}"
