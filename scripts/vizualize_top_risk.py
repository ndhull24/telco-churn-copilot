import os
import pandas as pd
import matplotlib.pyplot as plt

IN = "data/top_risk_export.csv"
OUTDIR = "data/plots"
os.makedirs(OUTDIR, exist_ok=True)

df = pd.read_csv(IN)

# ----- Plot 1: Top 20 by final score (bar chart) -----
top = df.nlargest(20, "final_score")[["customer_id", "final_score"]].copy()

plt.figure(figsize=(12, 6))
plt.bar(top["customer_id"], top["final_score"])
plt.title("Top 20 Customers by Final Risk Score")
plt.xlabel("Customer ID")
plt.ylabel("Final Risk Score (0–100)")  # <- y-axis label
plt.xticks(rotation=70, ha="right")
plt.tight_layout()

# annotate bars with values
for i, v in enumerate(top["final_score"]):
    plt.text(i, v + 1, f"{v:.0f}", ha="center", va="bottom", fontsize=8)

p1 = os.path.join(OUTDIR, "top20_final_score.png")
plt.savefig(p1, dpi=150)
plt.close()

# ----- Plot 2: Distribution of risk drivers (histograms) -----
# Final score histogram
plt.figure(figsize=(8, 5))
plt.hist(df["final_score"], bins=20)
plt.title("Distribution: Final Risk Score")
plt.xlabel("Final Risk Score (0–100)")
plt.ylabel("Customer Count")            # <- y-axis label
plt.tight_layout()
p2 = os.path.join(OUTDIR, "hist_final_score.png")
plt.savefig(p2, dpi=150)
plt.close()

# CPI histogram (optional, helps explain drivers)
if "CPI" in df.columns:
    plt.figure(figsize=(8, 5))
    plt.hist(df["CPI"], bins=20)
    plt.title("Distribution: Competitive Pressure Index (CPI)")
    plt.xlabel("CPI (0–100)")
    plt.ylabel("Customer Count")
    plt.tight_layout()
    p3 = os.path.join(OUTDIR, "hist_cpi.png")
    plt.savefig(p3, dpi=150)
    plt.close()
else:
    p3 = None

print("Saved:")
print(" -", p1)
print(" -", p2)
if p3: print(" -", p3)
