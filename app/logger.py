import csv, os, datetime as dt
from typing import Dict

LOG_PATH = "data/action_log.csv"
HEADER = ["ts","customer_id","region","final_score","action","proposed_text","pass","violations","missing_disclaimers"]

os.makedirs("data", exist_ok=True)
if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADER)

def append_action(row: Dict):
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            dt.datetime.utcnow().isoformat(timespec="seconds"),
            row["customer_id"], row["region"], row["final_score"],
            row["action"], row["proposed_text"],
            row["compliance"]["pass"],
            "|".join(row["compliance"]["violations"]),
            "|".join(row["compliance"]["missing_disclaimers"]),
        ])
