"""Join Olist tables, compute delivery delay, and score regional performance.

Reads CSVs from data/raw/ (downloaded from the public Olist GitHub mirror).
Writes data/processed/audit_orders.csv and data/processed/summary.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

DATA_BASE = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"
NEEDED = [
    "olist_orders_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_order_items_dataset.csv",
    "product_category_name_translation.csv",
]

REGION = {
    "AC": "North", "AP": "North", "AM": "North", "PA": "North", "RO": "North", "RR": "North", "TO": "North",
    "AL": "Northeast", "BA": "Northeast", "CE": "Northeast", "MA": "Northeast", "PB": "Northeast",
    "PE": "Northeast", "PI": "Northeast", "RN": "Northeast", "SE": "Northeast",
    "DF": "Center-West", "GO": "Center-West", "MT": "Center-West", "MS": "Center-West",
    "ES": "Southeast", "MG": "Southeast", "RJ": "Southeast", "SP": "Southeast",
    "PR": "South", "RS": "South", "SC": "South",
}
REMOTE = {"North", "Northeast"}


def ensure_raw() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    import urllib.request

    for name in NEEDED:
        path = RAW / name
        if path.exists() and path.stat().st_size > 1000:
            continue
        urllib.request.urlretrieve(DATA_BASE + name, path)


def latest_review(reviews: pd.DataFrame) -> pd.DataFrame:
    """One review per order — keep the latest so 1-to-many does not duplicate orders."""
    work = reviews.copy()
    work["review_creation_date"] = pd.to_datetime(work["review_creation_date"], errors="coerce")
    work = work.sort_values(["order_id", "review_creation_date"])
    return work.drop_duplicates("order_id", keep="last")[
        ["order_id", "review_score", "review_creation_date"]
    ]


def primary_category(items: pd.DataFrame, products: pd.DataFrame, trans: pd.DataFrame) -> pd.DataFrame:
    """One category per order: first item, then English name."""
    first = items.sort_values(["order_id", "order_item_id"]).drop_duplicates("order_id", keep="first")
    first = first.merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
    first = first.merge(trans, on="product_category_name", how="left")
    first["category_en"] = (
        first["product_category_name_english"]
        .fillna(first["product_category_name"])
        .fillna("unknown")
        .str.replace("_", " ")
    )
    return first[["order_id", "category_en"]]


def classify(days_difference: pd.Series) -> pd.Series:
    # Days_Difference = estimated - actual. Negative means late.
    status = pd.Series("On Time", index=days_difference.index)
    status = status.mask(days_difference < 0, "Late")
    status = status.mask(days_difference < -5, "Super Late")
    return status


def build() -> tuple[pd.DataFrame, dict]:
    ensure_raw()
    orders = pd.read_csv(RAW / "olist_orders_dataset.csv")
    reviews = pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
    customers = pd.read_csv(RAW / "olist_customers_dataset.csv")
    products = pd.read_csv(RAW / "olist_products_dataset.csv")
    items = pd.read_csv(RAW / "olist_order_items_dataset.csv")
    trans = pd.read_csv(RAW / "product_category_name_translation.csv")

    drop_log = {
        "orders_in": int(len(orders)),
        "reviews_in": int(len(reviews)),
        "review_rows_dropped_as_duplicate": int(len(reviews) - reviews["order_id"].nunique()),
    }

    master = orders.merge(customers, on="customer_id", how="left", validate="m:1")
    master = master.merge(latest_review(reviews), on="order_id", how="left", validate="1:1")
    master = master.merge(primary_category(items, products, trans), on="order_id", how="left", validate="1:1")

    for col in [
        "order_purchase_timestamp",
        "order_estimated_delivery_date",
        "order_delivered_customer_date",
    ]:
        master[col] = pd.to_datetime(master[col], errors="coerce")

    delivered_mask = master["order_status"].eq("delivered") & master["order_delivered_customer_date"].notna()
    master["never_delivered"] = ~delivered_mask
    master["region"] = master["customer_state"].map(REGION).fillna("Unknown")
    master["remote"] = master["region"].isin(REMOTE)

    audit = master.loc[delivered_mask].copy()
    audit["Days_Difference"] = (
        audit["order_estimated_delivery_date"] - audit["order_delivered_customer_date"]
    ).dt.days
    audit["delay_days"] = -audit["Days_Difference"]
    audit["delivery_status"] = classify(audit["Days_Difference"])
    audit["late"] = audit["delivery_status"].isin(["Late", "Super Late"])
    audit["promised_days"] = (
        audit["order_estimated_delivery_date"] - audit["order_purchase_timestamp"]
    ).dt.days
    audit["actual_days"] = (
        audit["order_delivered_customer_date"] - audit["order_purchase_timestamp"]
    ).dt.days
    audit["overpromise_days"] = audit["actual_days"] - audit["promised_days"]

    drop_log["canceled_or_unavailable"] = int(
        master["order_status"].isin(["canceled", "unavailable"]).sum()
    )
    drop_log["other_not_delivered"] = int(master["never_delivered"].sum() - drop_log["canceled_or_unavailable"])
    drop_log["delivered_audited"] = int(len(audit))
    drop_log["master_rows"] = int(len(master))
    drop_log["orders_duplicated_after_join"] = int(len(master) - master["order_id"].nunique())

    state = (
        audit.groupby(["customer_state", "region", "remote"], dropna=False)
        .agg(
            n=("order_id", "size"),
            pct_late=("late", "mean"),
            pct_super_late=("delivery_status", lambda s: (s == "Super Late").mean()),
            avg_delay=("delay_days", "mean"),
            avg_review=("review_score", "mean"),
            avg_promised=("promised_days", "mean"),
            avg_actual=("actual_days", "mean"),
        )
        .reset_index()
    )
    state["pct_late"] = (state["pct_late"] * 100).round(1)
    state["pct_super_late"] = (state["pct_super_late"] * 100).round(1)
    state = state.sort_values("pct_late", ascending=False)

    region = (
        audit.groupby("region")
        .agg(n=("order_id", "size"), pct_late=("late", "mean"), avg_review=("review_score", "mean"))
        .reset_index()
    )
    region["pct_late"] = (region["pct_late"] * 100).round(1)

    by_status = (
        audit.groupby("delivery_status")
        .agg(n=("order_id", "size"), avg_review=("review_score", "mean"), avg_delay=("delay_days", "mean"))
        .reindex(["On Time", "Late", "Super Late"])
        .reset_index()
    )

    delay_bin = pd.cut(
        audit["delay_days"].clip(-20, 30),
        bins=[-20, -1, 0, 2, 5, 10, 20, 30],
        labels=["early 1d+", "on the day", "1-2d late", "3-5d late", "6-10d late", "11-20d late", "21d+ late"],
    )
    sentiment = (
        audit.assign(delay_bucket=delay_bin)
        .groupby("delay_bucket", observed=True)
        .agg(n=("order_id", "size"), avg_review=("review_score", "mean"))
        .reset_index()
    )

    cat = (
        audit.groupby("category_en")
        .agg(n=("order_id", "size"), pct_late=("late", "mean"), avg_review=("review_score", "mean"))
        .reset_index()
    )
    cat = cat[cat["n"] >= 200].copy()
    cat["pct_late"] = (cat["pct_late"] * 100).round(1)
    cat = cat.sort_values("pct_late", ascending=False)

    on_time_score = float(audit.loc[~audit["late"], "review_score"].mean())
    late_score = float(audit.loc[audit["late"], "review_score"].mean())
    remote_late = float(audit.loc[audit["remote"], "late"].mean() * 100)
    hub_late = float(audit.loc[audit["customer_state"].eq("SP"), "late"].mean() * 100)
    worst = state.iloc[0]
    best_big = state[state["n"] >= 500].sort_values("pct_late").iloc[0]
    furniture = cat[cat["category_en"].str.contains("furniture|bed bath|home", case=False, na=False)]
    electronics = cat[cat["category_en"].str.contains("electronic|computer|telephony|console", case=False, na=False)]

    summary = {
        "n_orders": int(len(orders)),
        "n_delivered": int(len(audit)),
        "n_late": int(audit["late"].sum()),
        "pct_late": round(float(audit["late"].mean() * 100), 1),
        "pct_super_late": round(float((audit["delivery_status"] == "Super Late").mean() * 100), 1),
        "avg_days_difference": round(float(audit["Days_Difference"].mean()), 2),
        "on_time_review": round(on_time_score, 2),
        "late_review": round(late_score, 2),
        "review_gap": round(on_time_score - late_score, 2),
        "remote_pct_late": round(remote_late, 1),
        "sp_pct_late": round(hub_late, 1),
        "worst_state": worst["customer_state"],
        "worst_state_pct_late": float(worst["pct_late"]),
        "worst_state_n": int(worst["n"]),
        "best_large_state": best_big["customer_state"],
        "best_large_state_pct_late": float(best_big["pct_late"]),
        "avg_promised_days": round(float(audit["promised_days"].mean()), 1),
        "avg_actual_days": round(float(audit["actual_days"].mean()), 1),
        "furniture_late": round(float(furniture["pct_late"].mean()), 1) if len(furniture) else None,
        "electronics_late": round(float(electronics["pct_late"].mean()), 1) if len(electronics) else None,
        "state_table": state.to_dict(orient="records"),
        "region_table": region.to_dict(orient="records"),
        "status_table": json.loads(by_status.to_json(orient="records")),
        "sentiment_table": json.loads(sentiment.to_json(orient="records")),
        "category_table": cat.head(15).to_dict(orient="records"),
        "drop_log": drop_log,
        "recommendation": (
            f"Late deliveries are regional, not nationwide: {worst['customer_state']} is at "
            f"{worst['pct_late']:.1f}% late vs São Paulo at {hub_late:.1f}%. "
            f"On-time orders score {on_time_score:.2f}/5; late orders score {late_score:.2f}/5 "
            f"(a {on_time_score - late_score:.2f} point drop). "
            f"North/Northeast run {remote_late:.1f}% late. Repair ETAs and last-mile capacity there first."
        ),
    }
    return audit, summary


def main() -> None:
    audit, summary = build()
    keep = [
        "order_id",
        "customer_state",
        "region",
        "remote",
        "review_score",
        "Days_Difference",
        "delay_days",
        "delivery_status",
        "late",
        "promised_days",
        "actual_days",
        "overpromise_days",
        "category_en",
        "order_status",
    ]
    out = PROCESSED / "audit_orders.csv"
    audit[keep].to_csv(out, index=False)
    (PROCESSED / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(summary["state_table"]).to_csv(PROCESSED / "state_stats.csv", index=False)
    print("delivered", summary["n_delivered"], "late%", summary["pct_late"])
    print("review on-time vs late", summary["on_time_review"], summary["late_review"])
    print("worst state", summary["worst_state"], summary["worst_state_pct_late"])
    print("join duplicates", summary["drop_log"]["orders_duplicated_after_join"])
    print("wrote", out)


if __name__ == "__main__":
    main()
