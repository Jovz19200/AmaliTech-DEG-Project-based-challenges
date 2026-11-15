"""Build the Last Mile Auditor notebook. Run from the Logistics-auditor folder."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "last_mile_audit.ipynb"
OUT.parent.mkdir(parents=True, exist_ok=True)

nb = nbf.v4.new_notebook()
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}
cells = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text))


def code(text: str) -> None:
    cells.append(nbf.v4.new_code_cell(text))


md(
    """# Last Mile Auditor — Veridi Logistics
**Question:** Are we failing specific regions, or is this nationwide?  
**Data:** Olist Brazilian e-commerce (orders, reviews, customers, products). Raw CSVs are downloaded at runtime into `data/raw/` — do not commit them.

Covers User Stories 1–4, the English-category bonus, and Candidate's Choice (promised vs actual transit by state).
"""
)

code(
    """from pathlib import Path
import json, sys
sys.path.insert(0, str(Path.cwd() / 'scripts' if (Path.cwd() / 'scripts').exists() else Path.cwd().parent / 'scripts'))
from analyze import build
import pandas as pd
import plotly.express as px

audit, summary = build()
pd.Series(summary['drop_log'])"""
)

md(
    """## Story 1 — Schema builder

Join path: **Orders 1:1 latest Review**, **Orders many:1 Customers**, **Orders 1:1 first order item → product → English category**.

Reviews are 1-to-many. We keep the **latest review per `order_id`** so a second review cannot duplicate a shipment. After the joins, `orders_duplicated_after_join` in the drop log must be 0.
"""
)

code(
    """print('master grain check — duplicated orders after join:', summary['drop_log']['orders_duplicated_after_join'])
print('reviews dropped as extras:', summary['drop_log']['review_rows_dropped_as_duplicate'])
audit[['order_id','customer_state','review_score','Days_Difference','delivery_status','category_en']].head()"""
)

md(
    """## Story 2 — The real delay calculator

`Days_Difference = estimated delivery − actual delivery` (in days).

- **On Time:** `Days_Difference >= 0` (arrived on or before the promise)
- **Late:** `−5 ≤ Days_Difference < 0`
- **Super Late:** `Days_Difference < −5`

Canceled and unavailable orders are excluded from delay rates (they never arrived, so they are not “late” — they are a different failure).
"""
)

code(
    """print(audit['delivery_status'].value_counts())
print('late %', summary['pct_late'], 'super late %', summary['pct_super_late'])
print('mean Days_Difference (positive = early)', summary['avg_days_difference'])
pd.DataFrame(summary['status_table'])"""
)

md(
    """## Story 3 — Geographic heatmap (bar)

São Paulo is the commercial hub. Remote = North + Northeast. If remote states are disproportionately late, the CEO’s “nationwide” gut feeling is wrong — it is a regional last-mile problem.
"""
)

code(
    """state = pd.DataFrame(summary['state_table'])
fig = px.bar(state.sort_values('pct_late', ascending=False), x='customer_state', y='pct_late', color='region',
             title='% of delivered orders that missed the ETA',
             labels={'pct_late':'% late','customer_state':'State'}, hover_data=['n','avg_review'])
fig.show()
print('worst', summary['worst_state'], summary['worst_state_pct_late'])
print('SP hub', summary['sp_pct_late'], 'remote N/NE', summary['remote_pct_late'])
pd.DataFrame(summary['region_table'])"""
)

md(
    """## Story 4 — Sentiment correlation

If late deliveries cause bad reviews, on-time scores should beat late scores, and the score should fall as delay grows.
"""
)

code(
    """print('on time', summary['on_time_review'], 'late', summary['late_review'], 'gap', summary['review_gap'])
sent = pd.DataFrame(summary['sentiment_table'])
fig = px.bar(sent, x='delay_bucket', y='avg_review', title='Average review vs delay bucket')
fig.show()
sample = audit.sample(min(len(audit), 8000), random_state=7)
fig2 = px.scatter(sample, x='delay_days', y='review_score', color='region', opacity=0.35,
                  title='Days late vs review score')
fig2.show()"""
)

md(
    """## Bonus — English categories

`product_category_name` is Portuguese. We map it with `product_category_name_translation.csv` so furniture vs electronics is readable.
"""
)

code(
    """cat = pd.DataFrame(summary['category_table'])
fig = px.bar(cat.sort_values('pct_late', ascending=False).head(12), x='category_en', y='pct_late',
             title='Late rate by English category (n ≥ 200)')
fig.update_layout(xaxis_tickangle=-30)
fig.show()
cat.head(10)"""
)

md(
    """## Candidate's choice — promised vs actual transit

The CEO asked whether we **over-promise**. Plot average promised days (purchase → ETA) against average actual days (purchase → delivered) by state. Points **above the diagonal** take longer than we told the customer. That is an ETA policy fix, not a truck fix.
"""
)

code(
    """state = pd.DataFrame(summary['state_table'])
fig = px.scatter(state, x='avg_promised', y='avg_actual', size='n', color='region', hover_name='customer_state',
                 title='Promised vs actual transit days')
mx = max(state['avg_promised'].max(), state['avg_actual'].max())
fig.add_shape(type='line', x0=0, y0=0, x1=mx, y1=mx, line=dict(dash='dash', color='#888'))
fig.show()
print(summary['recommendation'])"""
)

nb['cells'] = cells
nbf.write(nb, OUT)
print('wrote', OUT)


if __name__ == "__main__":
    nbf.write(nb, OUT)
    print("wrote", OUT)
