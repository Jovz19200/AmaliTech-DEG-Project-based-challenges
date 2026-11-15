"""Streamlit dashboard for Veridi Logistics — Last Mile Auditor.

Run: py -3.13 -m streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "audit_orders.csv"
SUMMARY = json.loads((ROOT / "data" / "processed" / "summary.json").read_text(encoding="utf-8"))

st.set_page_config(page_title="Last Mile Auditor — Veridi", layout="wide")
df = pd.read_csv(DATA)

st.title("Are we failing specific regions, or is this nationwide?")
st.caption("Veridi Logistics  ·  Olist Brazilian e-commerce")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Delivered orders", f"{SUMMARY['n_delivered']:,}")
c2.metric("Late share", f"{SUMMARY['pct_late']}%")
c3.metric("Super late (>5d)", f"{SUMMARY['pct_super_late']}%")
c4.metric("Review gap (on-time − late)", SUMMARY["review_gap"])

st.error(SUMMARY["recommendation"])

regions = ["All"] + sorted(df["region"].dropna().unique().tolist())
pick = st.selectbox("Region filter", regions)
view = df if pick == "All" else df[df["region"] == pick]

left, right = st.columns(2)
with left:
    state = (
        view.groupby("customer_state")
        .agg(n=("order_id", "size"), pct_late=("late", "mean"), avg_review=("review_score", "mean"))
        .reset_index()
    )
    state["pct_late"] *= 100
    fig = px.bar(state.sort_values("pct_late", ascending=False), x="customer_state", y="pct_late",
                 title="% late by state", labels={"pct_late": "% late"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = px.box(view, x="delivery_status", y="review_score",
                 title="Review score by delivery status")
    st.plotly_chart(fig, use_container_width=True)

sample = view.sample(min(len(view), 6000), random_state=7)
fig = px.scatter(sample, x="delay_days", y="review_score", color="region", opacity=0.4,
                 title="Delay vs review score")
st.plotly_chart(fig, use_container_width=True)
