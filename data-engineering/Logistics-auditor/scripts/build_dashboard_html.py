"""Self-contained Plotly dashboard. Open in a browser. No login."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = json.loads((ROOT / "data" / "processed" / "summary.json").read_text(encoding="utf-8"))
AUDIT = pd.read_csv(ROOT / "data" / "processed" / "audit_orders.csv")
OUT = ROOT / "dashboard" / "last_mile_dashboard.html"
DOCS = ROOT / "docs" / "index.html"
OUT.parent.mkdir(parents=True, exist_ok=True)
DOCS.parent.mkdir(parents=True, exist_ok=True)

state = pd.DataFrame(SUMMARY["state_table"])
status = pd.DataFrame(SUMMARY["status_table"])
sent = pd.DataFrame(SUMMARY["sentiment_table"])
cats = pd.DataFrame(SUMMARY["category_table"])
region = pd.DataFrame(SUMMARY["region_table"])

bar = px.bar(
    state.sort_values("pct_late", ascending=False).head(20),
    x="customer_state",
    y="pct_late",
    color="region",
    title="Late delivery rate by state (Late + Super Late)",
    labels={"pct_late": "% late", "customer_state": "State"},
    hover_data=["n", "avg_review", "avg_promised", "avg_actual"],
)
bar.update_layout(height=420, template="plotly_white")

promise = px.scatter(
    state,
    x="avg_promised",
    y="avg_actual",
    size="n",
    color="region",
    hover_name="customer_state",
    title="Candidate's choice: promised vs actual transit days by state",
    labels={"avg_promised": "Average promised days (purchase → ETA)", "avg_actual": "Average actual days"},
)
mx = max(state["avg_promised"].max(), state["avg_actual"].max())
promise.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx, line=dict(dash="dash", color="#888"))
promise.update_layout(height=420, template="plotly_white")

review = px.bar(
    status,
    x="delivery_status",
    y="avg_review",
    text=status["avg_review"].round(2),
    title="Average review score: On Time vs Late vs Super Late",
    labels={"avg_review": "Average review (1–5)", "delivery_status": "Status"},
)
review.update_traces(textposition="outside")
review.update_layout(height=380, template="plotly_white", yaxis_range=[0, 5.5])

delay_line = px.bar(
    sent,
    x="delay_bucket",
    y="avg_review",
    title="Review score falls as delay grows",
    labels={"avg_review": "Average review", "delay_bucket": "Delay bucket"},
)
delay_line.update_layout(height=380, template="plotly_white")

cat_bar = px.bar(
    cats.sort_values("pct_late", ascending=False).head(12),
    x="category_en",
    y="pct_late",
    title="Bonus: late rate by English product category (n ≥ 200)",
    labels={"pct_late": "% late", "category_en": "Category"},
)
cat_bar.update_layout(height=420, template="plotly_white", xaxis_tickangle=-30)

sample = AUDIT.sample(min(len(AUDIT), 8000), random_state=7)
scatter = px.scatter(
    sample,
    x="delay_days",
    y="review_score",
    color="region",
    opacity=0.35,
    title="Delay (days) vs review score — filter regions in the legend",
    labels={"delay_days": "Days late (negative = early)", "review_score": "Review score"},
)
scatter.update_layout(height=480, template="plotly_white")

insight = SUMMARY["recommendation"]
kpis = (
    f"<p><b>{SUMMARY['n_delivered']:,}</b> delivered orders &nbsp;·&nbsp; "
    f"<b>{SUMMARY['pct_late']}%</b> late &nbsp;·&nbsp; "
    f"<b>{SUMMARY['pct_super_late']}%</b> super late (&gt;5 days) &nbsp;·&nbsp; "
    f"review gap <b>{SUMMARY['review_gap']}</b> points "
    f"({SUMMARY['on_time_review']} on time vs {SUMMARY['late_review']} late)</p>"
)

html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>Last Mile Auditor — Veridi Logistics</title>
<style>
body {{ font-family: Segoe UI, system-ui, sans-serif; margin: 24px; color: #1a1a1a; }}
h1 {{ color: #1f4e79; margin-bottom: 0; }}
.box {{ background: #f3f7fb; border-left: 6px solid #c0392b; padding: 12px 16px; margin: 16px 0; }}
.muted {{ color: #555; }}
</style></head><body>
<h1>Are we failing specific regions, or is this nationwide?</h1>
<p class="muted">Veridi Logistics · Olist Brazilian e-commerce · AmaliTech Data Engineering challenge</p>
{kpis}
<div class="box"><h2>Key insight</h2><p>{insight}</p>
<p>Worst state: <b>{SUMMARY['worst_state']}</b> at {SUMMARY['worst_state_pct_late']}% late
({SUMMARY['worst_state_n']:,} orders). São Paulo hub: {SUMMARY['sp_pct_late']}% late.
Remote North/Northeast: {SUMMARY['remote_pct_late']}% late.</p></div>
{bar.to_html(full_html=False, include_plotlyjs="cdn")}
{scatter.to_html(full_html=False, include_plotlyjs=False)}
{review.to_html(full_html=False, include_plotlyjs=False)}
{delay_line.to_html(full_html=False, include_plotlyjs=False)}
{promise.to_html(full_html=False, include_plotlyjs=False)}
{cat_bar.to_html(full_html=False, include_plotlyjs=False)}
<p class="muted">Days_Difference = estimated − actual. Negative = late. Super Late = more than 5 days late.
Canceled and unavailable orders are excluded from delay rates. Reviews are deduplicated to one per order.</p>
</body></html>
"""
OUT.write_text(html, encoding="utf-8")
DOCS.write_text(html, encoding="utf-8")
print("wrote", OUT, "bytes", OUT.stat().st_size)
