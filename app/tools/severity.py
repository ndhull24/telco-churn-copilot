from typing import List, Dict

def mock_variable_severity() -> List[Dict]:
    """
    Returns a fixed ranking so UI/workflows have something to display.
    Swap this with real SHAP/permutation scores later.
    """
    return [
        {"variable": "avg_down_mbps", "severity": 78},
        {"variable": "last_bill_delta", "severity": 73},
        {"variable": "dropped_calls_pct", "severity": 66},
    ]

if __name__ == "__main__":
    for row in mock_variable_severity():
        print(f"{row['variable']}: {row['severity']}")
